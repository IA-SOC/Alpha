"""
Lógica de negocio del agente, en funciones puras sobre dicts/listas (JSON-friendly).

Se separa de los MCP servers a propósito: cada servidor es solo un wrapper
delgado de protocolo alrededor de estas funciones. Así la lógica se puede
testear sin levantar ningún servidor MCP, y el protocolo se puede cambiar
sin tocar la lógica.

Es la misma lógica que en soc-agent/agent/*.py, adaptada a dicts en vez de
dataclasses para que viaje directo como argumentos/resultados de tools MCP.
"""
from collections import defaultdict
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Catálogo de reglas MITRE ATT&CK (ampliar con la guía real del cliente)
# ---------------------------------------------------------------------------
RULES = [
    {
        "match_any": ["brute_force", "failed_login", "multiple_auth_failures"],
        "technique_id": "T1110",
        "technique_name": "Brute Force",
        "tactic": "Credential Access",
    },
    {
        "match_any": ["lateral_movement", "smb_admin_share", "remote_exec"],
        "technique_id": "T1021",
        "technique_name": "Remote Services",
        "tactic": "Lateral Movement",
    },
    {
        "match_any": ["phishing", "suspicious_attachment", "credential_harvest"],
        "technique_id": "T1566",
        "technique_name": "Phishing",
        "tactic": "Initial Access",
    },
    {
        "match_any": ["data_exfiltration", "large_outbound_transfer", "dns_tunneling"],
        "technique_id": "T1041",
        "technique_name": "Exfiltration Over C2 Channel",
        "tactic": "Exfiltration",
    },
    {
        "match_any": ["file_encryption", "shadow_copy_deleted", "ransom_note"],
        "technique_id": "T1486",
        "technique_name": "Data Encrypted for Impact",
        "tactic": "Impact",
    },
]

TACTIC_TO_STAGE = {
    "Initial Access": "initial_access",
    "Credential Access": "initial_access",
    "Lateral Movement": "progression",
    "Persistence": "progression",
    "Exfiltration": "impact",
    "Impact": "impact",
}

ACTIONS_BY_TACTIC = {
    "Credential Access": [
        "Forzar rotación de credenciales de las cuentas involucradas",
        "Habilitar/reforzar MFA en los hosts afectados",
    ],
    "Lateral Movement": [
        "Aislar los hosts involucrados de la red",
        "Revisar reglas de segmentación entre los hosts afectados",
    ],
    "Initial Access": [
        "Bloquear el vector de entrada identificado (IP, dominio o archivo)",
    ],
    "Exfiltration": [
        "Bloquear las conexiones salientes hacia los destinos identificados",
        "Notificar al equipo de respuesta a incidentes de exfiltración",
    ],
    "Impact": [
        "Aislar inmediatamente los hosts afectados",
        "Verificar integridad de backups antes de cualquier restauración",
    ],
}

TACTIC_ORDER = ["Initial Access", "Credential Access", "Lateral Movement",
                "Persistence", "Exfiltration", "Impact"]


def _alert_signals(alert: Dict[str, Any]) -> List[str]:
    signals = [alert.get("rule_name", "").lower()]
    signals += [t.lower() for t in alert.get("tags", [])]
    return signals


def map_alerts_to_mitre(alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Alertas -> lista de técnicas MITRE ATT&CK candidatas, con evidencia."""
    evidence_by_technique: Dict[str, List[str]] = defaultdict(list)
    rule_by_technique = {}

    for alert in alerts:
        signals = _alert_signals(alert)
        for rule in RULES:
            if any(pattern in signal for pattern in rule["match_any"] for signal in signals):
                evidence_by_technique[rule["technique_id"]].append(alert["id"])
                rule_by_technique[rule["technique_id"]] = rule

    mappings = []
    for technique_id, alert_ids in evidence_by_technique.items():
        rule = rule_by_technique[technique_id]
        confidence = min(0.5 + 0.15 * len(alert_ids), 0.95)
        mappings.append({
            "technique_id": technique_id,
            "technique_name": rule["technique_name"],
            "tactic": rule["tactic"],
            "supporting_alert_ids": alert_ids,
            "confidence": round(confidence, 2),
        })

    return sorted(mappings, key=lambda m: m["confidence"], reverse=True)


def build_timeline(alerts: List[Dict[str, Any]], mappings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Alertas + mapeo MITRE -> línea de tiempo ordenada, con etapa por evento."""
    alert_to_tactic = {}
    for mapping in mappings:
        for alert_id in mapping["supporting_alert_ids"]:
            alert_to_tactic.setdefault(alert_id, mapping["tactic"])

    events = []
    for alert in sorted(alerts, key=lambda a: a["timestamp"]):
        tactic = alert_to_tactic.get(alert["id"])
        stage = TACTIC_TO_STAGE.get(tactic, "progression")
        description = alert.get("rule_name", "")
        if alert.get("host"):
            description += f" en host {alert['host']}"
        if alert.get("user"):
            description += f" (usuario: {alert['user']})"

        events.append({
            "alert_id": alert["id"],
            "timestamp": alert["timestamp"],
            "description": description,
            "stage": stage,
        })

    return events


def generate_hypothesis(mappings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Técnicas MITRE -> hipótesis de ataque rankeada con confianza agregada."""
    if not mappings:
        return {
            "summary": "No se detectaron patrones que coincidan con técnicas MITRE ATT&CK conocidas.",
            "mitre_techniques": [],
            "confidence": 0.0,
            "evidence_alert_ids": [],
        }

    ordered = sorted(
        mappings,
        key=lambda m: TACTIC_ORDER.index(m["tactic"]) if m["tactic"] in TACTIC_ORDER else 99,
    )
    steps = [f"{m['technique_name']} ({m['technique_id']}, táctica: {m['tactic']})" for m in ordered]
    summary = "Secuencia de ataque sugerida: " + " → ".join(steps) + "."

    all_evidence = sorted({aid for m in mappings for aid in m["supporting_alert_ids"]})
    confidence = round(sum(m["confidence"] for m in mappings) / len(mappings), 2)

    return {
        "summary": summary,
        "mitre_techniques": ordered,
        "confidence": confidence,
        "evidence_alert_ids": all_evidence,
    }


def _blast_radius(alerts_by_id: Dict[str, Dict[str, Any]], evidence_alert_ids: List[str]) -> List[str]:
    hosts, users = set(), set()
    for alert_id in evidence_alert_ids:
        alert = alerts_by_id.get(alert_id)
        if not alert:
            continue
        if alert.get("host"):
            hosts.add(alert["host"])
        if alert.get("user"):
            users.add(alert["user"])
    return sorted(hosts) + sorted(f"usuario:{u}" for u in users)


def _recommended_actions(hypothesis: Dict[str, Any]) -> List[str]:
    actions = []
    for technique in hypothesis["mitre_techniques"]:
        for action in ACTIONS_BY_TACTIC.get(technique["tactic"], []):
            if action not in actions:
                actions.append(action)
    return actions


def generate_report(case: Dict[str, Any], timeline: List[Dict[str, Any]],
                     hypothesis: Dict[str, Any]) -> Dict[str, Any]:
    """Ensambla el reporte final de incidente."""
    alerts_by_id = {a["id"]: a for a in case["alerts"]}

    case_summary = (
        f"Caso {case['case_id']}: {len(case['alerts'])} alertas correlacionadas analizadas. "
        f"Confianza de la hipótesis principal: {hypothesis['confidence']:.0%}."
    )

    return {
        "case_id": case["case_id"],
        "case_summary": case_summary,
        "timeline": timeline,
        "hypothesis": hypothesis,
        "blast_radius": _blast_radius(alerts_by_id, hypothesis["evidence_alert_ids"]),
        "recommended_actions": _recommended_actions(hypothesis),
    }
