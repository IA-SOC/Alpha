"""
Fase 1 de la skill soc-case-investigator: recibir y validar el caso.

Detecta el formato de origen (Elastic ECS, Elastic Security, Wazuh o el
formato interno simplificado del scaffold), conserva el registro original y
produce una alerta normalizada con los campos que usa core/logic.py
(id, timestamp, rule_name, tags, host, user, source_ip, dest_ip).

No completa valores por intuición: lo que falta se registra en
missing_fields y los timestamps sin zona horaria se marcan como
timezone_unknown en vez de asumirse UTC.
"""
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

MAX_ALERTS = 50

# Mismo orden de resolución de ID que scripts/validate_report.py de la skill,
# para que las referencias del reporte coincidan con las del validador.
ID_PATHS = ("alert_id", "id", "_id", "event.id", "kibana.alert.uuid")

# Grupos de reglas Wazuh -> señal que entiende el catálogo de core/logic.py.
TAG_SYNONYMS = {
    "authentication_failed": "failed_login",
    "invalid_login": "failed_login",
    "authentication_failures": "multiple_auth_failures",
}

# Texto que intenta dar instrucciones al agente. Se detecta solo para dejar
# constancia en limitaciones: nunca se ejecuta ni cambia el análisis.
INJECTION_PATTERN = re.compile(
    r"(ignore|ignora|olvida)\W+(all\W+)?(previous|prior|anteriores?)\W+(instructions|instrucciones)"
    r"|close (this|the) case|cierra (el|este) caso|system prompt",
    re.IGNORECASE,
)


def get_path(obj: Any, path: str) -> Any:
    """Lee 'a.b.c' como objeto anidado o, si no existe, como clave plana."""
    if isinstance(obj, dict) and path in obj:
        return obj[path]
    for part in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def _first(alert: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        value = get_path(alert, path)
        if value not in (None, "", []):
            return value
    return None


def _as_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def detect_format(alert: Dict[str, Any]) -> str:
    if isinstance(alert.get("agent"), dict) and isinstance(alert.get("rule"), dict) and "level" in alert["rule"]:
        return "wazuh"
    if get_path(alert, "kibana.alert.uuid") or get_path(alert, "kibana.alert.rule.name"):
        return "elastic_security"
    if "@timestamp" in alert or isinstance(alert.get("event"), dict):
        return "elastic_ecs"
    return "unknown"


def parse_timestamp(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Devuelve (timestamp_utc, problema). problema ∈ {None, missing, invalid, timezone_unknown}."""
    if not raw:
        return None, "missing"
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (ValueError, OverflowError):
        return None, "invalid"
    if parsed.tzinfo is None:
        return None, "timezone_unknown"
    try:
        return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"), None
    except (ValueError, OverflowError):
        return None, "invalid"


def _strings(obj: Any) -> List[Tuple[str, str]]:
    """Aplana un registro a pares (ruta, valor) de texto, para IoC e inyección."""
    out: List[Tuple[str, str]] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for child in value:
                walk(child, path)
        elif isinstance(value, str):
            out.append((path, value))

    walk(obj, "")
    return out


def normalize_alert(alert: Dict[str, Any], index: int) -> Dict[str, Any]:
    source_format = detect_format(alert)

    native_id = _first(alert, *ID_PATHS)
    alert_id = str(native_id) if native_id is not None else f"alert-{index:03d}"

    timestamp_original = _first(alert, "timestamp", "@timestamp")
    # Native/custom fields are untyped at intake. Keep them in raw, but only
    # expose strings to the legacy agent's timeline/asset algorithms.
    if not isinstance(timestamp_original, str):
        timestamp_original = None
    timestamp_utc, ts_problem = parse_timestamp(timestamp_original)

    tags = _as_list(alert.get("tags")) + _as_list(get_path(alert, "rule.groups"))
    tags += _as_list(get_path(alert, "event.category"))
    tags += [TAG_SYNONYMS[t] for t in tags if t in TAG_SYNONYMS]

    rule_name = _first(alert, "rule_name", "kibana.alert.rule.name", "rule.name", "rule.description", "event.action")
    host = alert["host"] if isinstance(alert.get("host"), str) else _first(alert, "host.name", "host.hostname", "agent.name")
    # En Wazuh, srcuser es quien actúa (sudo); dstuser es la cuenta objetivo (login SSH).
    user = alert["user"] if isinstance(alert.get("user"), str) else _first(alert, "user.name", "data.srcuser", "data.dstuser")
    host = host if isinstance(host, str) else None
    user = user if isinstance(user, str) else None

    normalized = {
        "id": alert_id,
        "id_is_native": native_id is not None,
        "source_format": source_format,
        # core/logic.py ordena la timeline por este campo; si no hay UTC se usa el original.
        "timestamp": timestamp_utc or (str(timestamp_original) if timestamp_original else ""),
        "timestamp_original": timestamp_original,
        "timestamp_utc": timestamp_utc,
        "timestamp_problem": ts_problem,
        "rule_name": str(rule_name) if rule_name else "",
        "tags": tags,
        "host": host,
        "user": user,
        "source_ip": _first(alert, "source_ip", "source.ip", "data.srcip"),
        "dest_ip": _first(alert, "dest_ip", "destination.ip", "data.dstip"),
        "raw": alert,
    }

    missing = [name for name, value in (
        ("id", native_id), ("timestamp", timestamp_original),
        ("rule_name", rule_name), ("host", host),
    ) if value in (None, "")]
    normalized["missing_fields"] = missing
    normalized["string_values"] = _strings(alert)
    return normalized


def normalize_case(case: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Caso crudo -> (alertas normalizadas, resumen de entrada para el reporte)."""
    raw_alerts = case.get("alerts") if isinstance(case.get("alerts"), list) else []
    alerts = [normalize_alert(a, i + 1) for i, a in enumerate(raw_alerts) if isinstance(a, dict)]

    context = case.get("investigation_context", {})
    if context.get("adapter_version") == "backend-v1":
        originals = context["original_case"]["alerts"]
        for normalized, event, original in zip(alerts, context["events"], originals, strict=True):
            normalized["id"] = original["alert_id"]
            normalized["id_is_native"] = True
            normalized["raw"] = original["raw_alert"]
            normalized["string_values"] = _strings(original["raw_alert"])
            normalized["source_format"] = (
                "wazuh" if original["source_system"] == "wazuh" else
                "elastic_security" if normalized["source_format"] == "elastic_security" else "elastic_ecs"
            )
            original_time = (event.get("timestamp_evidence") or {}).get("value")
            normalized["timestamp_original"] = original_time if isinstance(original_time, str) else None
            normalized["timestamp_utc"] = event["timestamp_utc"]
            normalized["timestamp"] = event["timestamp_utc"] or ""
            if event["timestamp_utc"]:
                normalized["timestamp_problem"] = None
            else:
                _, problem = parse_timestamp(normalized["timestamp_original"])
                normalized["timestamp_problem"] = problem or "invalid"

    formats = {a["source_format"] for a in alerts}
    source_format = formats.pop() if len(formats) == 1 else ("mixed" if formats else "unknown")

    utc_times = sorted(a["timestamp_utc"] for a in alerts if a["timestamp_utc"])
    missing_fields = [f"{a['id']}: {field}" for a in alerts for field in a["missing_fields"]]

    warnings: List[str] = []
    if context.get("adapter_version") == "backend-v1":
        warnings.extend(f"{e['alert_id']}: {w}" for e in context["events"] for w in e["warnings"])
    if not alerts:
        warnings.append("El caso no contiene alertas procesables.")
    if len(alerts) > MAX_ALERTS:
        warnings.append(
            f"El caso tiene {len(alerts)} alertas (> {MAX_ALERTS}); se procesan todas, "
            "pero queda fuera del requisito de rendimiento del prototipo."
        )
    seen, duplicates = set(), set()
    for a in alerts:
        (duplicates if a["id"] in seen else seen).add(a["id"])
    if duplicates:
        warnings.append(f"IDs de alerta duplicados: {sorted(duplicates)}")
    for a in alerts:
        if a["timestamp_problem"] == "timezone_unknown":
            warnings.append(f"{a['id']}: timestamp sin zona horaria ({a['timestamp_original']}); no se asume UTC.")
        elif a["timestamp_problem"] == "invalid":
            warnings.append(f"{a['id']}: timestamp inválido ({a['timestamp_original']}).")
        if not a["id_is_native"]:
            warnings.append(f"{a['id']}: sin ID nativo; se asignó una referencia local.")
    if source_format == "unknown" and alerts:
        warnings.append("Formato interno simplificado del scaffold (no es ECS ni Wazuh nativo).")

    injections = [
        f"{a['id']}.{path}" for a in alerts for path, value in a["string_values"] if INJECTION_PATTERN.search(value)
    ]

    summary = {
        "source_format": source_format,
        "schema_version": case.get("schema_version"),
        "alert_count": len(raw_alerts),
        "processed_alert_count": len(alerts),
        "time_window_utc": {"start": utc_times[0], "end": utc_times[-1]} if utc_times else None,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "untrusted_instruction_fields": injections,
    }
    return alerts, summary
