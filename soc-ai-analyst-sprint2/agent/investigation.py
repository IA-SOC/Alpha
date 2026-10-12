"""
Fases 2-5 de la skill soc-case-investigator, en funciones puras.

Toman lo que devuelven los MCP servers (mapeo MITRE, timeline, cadena de
ataque) y lo llevan al contrato de salida de la skill
(skills/soc-case-investigator/references/report-schema.json, v1.1):

- confianza ordinal (alta/media/baja/insuficiente), nunca porcentajes;
- evidencia a favor y en contra, con IDs de alerta y campos concretos;
- activos observados separados de sospechosos/confirmados;
- IoC tomados solo del enriquecimiento adjunto al caso.
"""
from copy import deepcopy
from typing import Any, Dict, List

from core.logic import ACTIONS_BY_TACTIC, TACTIC_ORDER

LEVELS = ["insuficiente", "baja", "media", "alta"]

# Etiquetas que describen actividad legítima conocida. Si aparecen en el mismo
# host que la evidencia de una hipótesis, cuentan como evidencia en contra.
BENIGN_TAGS = {"backup", "scheduled_task", "maintenance", "change_approved"}

ALTERNATIVES = {
    "Credential Access": ["Usuario legítimo que olvidó su contraseña o script con credenciales vencidas."],
    "Lateral Movement": ["Tarea administrativa o de respaldo legítima entre servidores."],
    "Initial Access": ["Correo legítimo de proveedor clasificado como sospechoso por la regla."],
    "Exfiltration": ["Replicación o respaldo externo autorizado."],
    "Impact": ["Cifrado o limpieza legítima por software de respaldo/DLP."],
}

UNKNOWNS = {
    "Credential Access": ["No hay telemetría de EDR que confirme ejecución posterior al acceso."],
    "Lateral Movement": ["Falta confirmar si la sesión remota tenía un cambio aprobado."],
    "Initial Access": ["No se sabe si el usuario introdujo credenciales en el sitio."],
    "Exfiltration": ["Se desconoce el contenido y el volumen exacto transferido."],
    "Impact": ["Se desconoce el alcance total de archivos afectados y el estado de backups."],
}

PRIORITY_BY_TACTIC = {
    "Impact": "urgent",
    "Exfiltration": "urgent",
    "Lateral Movement": "high",
    "Credential Access": "high",
    "Initial Access": "medium",
}
PRIORITIES = ["low", "medium", "high", "urgent"]

CATALOG_VERSION = "catálogo local core/logic.RULES (sin versión ATT&CK fijada)"


def _evidence(alert: Dict[str, Any], role: str, relevance: str) -> Dict[str, Any]:
    return {
        "alert_id": alert["id"],
        "role": role,
        "fields": [f for f in ("rule_name", "tags", "host", "user") if alert.get(f)],
        "observation": f"{alert['rule_name'] or 'sin regla'} en {alert.get('host') or 'host desconocido'}"
                       + (f" (usuario {alert['user']})" if alert.get("user") else ""),
        "relevance": relevance,
    }


def ordinal_confidence(support: List[Dict[str, Any]], against: List[Dict[str, Any]],
                       synthetic: bool) -> Dict[str, str]:
    """Rúbrica de references/protocolo.md aplicada de forma determinista."""
    distinct_rules = {a["rule_name"] for a in support}
    if len(support) >= 3 and len(distinct_rules) >= 2:
        level, basis = 3, f"{len(support)} alertas con {len(distinct_rules)} reglas distintas coinciden"
    elif len(support) >= 2:
        level, basis = 2, f"{len(support)} alertas coherentes, sin corroboración de otra fuente"
    elif support:
        level, basis = 1, "una única alerta sostiene la hipótesis"
    else:
        level, basis = 0, "no hay alertas que sostengan la hipótesis"

    reasons = []
    if against:
        level -= 1
        reasons.append(f"{len(against)} alerta(s) sugieren actividad legítima")
    if any(a["timestamp_problem"] for a in support):
        level -= 1
        reasons.append("hay timestamps sin zona horaria o inválidos")
    if synthetic and level > 2:
        level = 2
        reasons.append("el caso es sintético")
    level = max(level, 0)

    text = basis + (". Se ajusta a la baja: " + "; ".join(reasons) if reasons else "") + "."
    return {"confidence": LEVELS[level], "confidence_basis": text[0].upper() + text[1:]}


def build_attack_analysis(alerts: List[Dict[str, Any]], mappings: List[Dict[str, Any]],
                          synthetic: bool) -> Dict[str, List[Dict[str, Any]]]:
    """Mapeo MITRE del MCP server -> attack_mapping + hypotheses (fase 2)."""
    by_id = {a["id"]: a for a in alerts}
    attack_mapping, hypotheses = [], []

    for mapping in mappings:
        support = [by_id[i] for i in mapping["supporting_alert_ids"] if i in by_id]
        hosts = {a.get("host") for a in support}
        against = [
            a for a in alerts
            if a["id"] not in mapping["supporting_alert_ids"]
            and a.get("host") in hosts and BENIGN_TAGS & set(a["tags"])
        ]
        tactic = mapping["tactic"]

        attack_mapping.append({
            "tactic": tactic,
            "technique_id": mapping["technique_id"],
            "technique_name": mapping["technique_name"],
            "status": "candidate",
            "evidence": [_evidence(a, "supporting", f"Señal que coincide con el patrón de {mapping['technique_name']}.")
                         for a in support],
            "source_version": CATALOG_VERSION,
        })

        confidence = ordinal_confidence(support, against, synthetic)
        hypotheses.append({
            "statement": f"Actividad compatible con {mapping['technique_name']} "
                         f"({mapping['technique_id']}, táctica {tactic}) en {', '.join(sorted(h for h in hosts if h))}.",
            "tactic": tactic,
            **confidence,
            "evidence_for": [_evidence(a, "supporting", "Alerta que coincide con el patrón de la técnica.") for a in support],
            "evidence_against": [_evidence(a, "contradicting", "Actividad legítima conocida en el mismo host y ventana.")
                                 for a in against],
            "alternatives": ALTERNATIVES.get(tactic, []),
            "unknowns": UNKNOWNS.get(tactic, []),
        })

    hypotheses.sort(key=lambda h: (
        -LEVELS.index(h["confidence"]),
        TACTIC_ORDER.index(h["tactic"]) if h["tactic"] in TACTIC_ORDER else 99,
    ))
    for rank, hypothesis in enumerate(hypotheses, start=1):
        hypothesis["rank"] = rank
    return {"attack_mapping": attack_mapping, "hypotheses": hypotheses}


def build_timeline(alerts: List[Dict[str, Any]], mcp_timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Timeline del MCP server -> formato de la skill, conservando el timestamp original."""
    by_id = {a["id"]: a for a in alerts}
    timeline = []
    for event in mcp_timeline:
        alert = by_id[event["alert_id"]]
        timeline.append({
            "timestamp_original": alert["timestamp_original"],
            "timestamp_utc": alert["timestamp_utc"],
            "timezone_unknown": alert["timestamp_problem"] == "timezone_unknown",
            "description": event["description"] or "Evento sin descripción de regla",
            "stage": event["stage"],
            "alert_ids": [alert["id"]],
            "certainty": "observed",
        })
    return timeline


def build_blast_radius(alerts: List[Dict[str, Any]], hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fase 3: activos observados vs. sospechosos. Nada se marca como confirmado."""
    observed: Dict[str, Dict[str, Any]] = {}
    for alert in alerts:
        host = alert.get("host")
        if not host:
            continue
        entry = observed.setdefault(host, {"asset": host, "basis_alert_ids": [], "rules": []})
        entry["basis_alert_ids"].append(alert["id"])
        if alert["rule_name"] and alert["rule_name"] not in entry["rules"]:
            entry["rules"].append(alert["rule_name"])
    observed_assets = [
        {"asset": e["asset"], "basis_alert_ids": e["basis_alert_ids"],
         "observed_activity": "; ".join(e["rules"]) or "actividad sin regla nombrada"}
        for e in observed.values()
    ]

    suspected: Dict[str, List[str]] = {}
    identities: Dict[str, List[str]] = {}
    ambiguous: Dict[str, List[str]] = {}
    for hypothesis in hypotheses:
        strong = hypothesis["confidence"] in ("media", "alta")
        for ev in hypothesis["evidence_for"]:
            alert = next(a for a in alerts if a["id"] == ev["alert_id"])
            if alert.get("host"):
                target = suspected if strong else ambiguous
                ids = target.setdefault(alert["host"], [])
                if alert["id"] not in ids:
                    ids.append(alert["id"])
            if strong and alert.get("user"):
                ids = identities.setdefault(alert["user"], [])
                if alert["id"] not in ids:
                    ids.append(alert["id"])

    unknowns = [
        "Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).",
    ]
    for host, ids in ambiguous.items():
        if host not in suspected:
            unknowns.append(f"Actividad ambigua en {host} (alertas {', '.join(ids)}): hipótesis de confianza baja o insuficiente.")
    if any(not a.get("host") for a in alerts):
        unknowns.append("Hay alertas sin host identificado.")

    return {
        "observed_assets": observed_assets,
        "confirmed_assets": [],
        "suspected_assets": [{"asset": h, "basis_alert_ids": ids} for h, ids in suspected.items()],
        "confirmed_identities": [],
        "suspected_identities": [{"identity": u, "basis_alert_ids": ids} for u, ids in identities.items()],
        "unknowns": unknowns,
    }


def consume_enrichment(case: Dict[str, Any], alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fase 4: solo el enriquecimiento adjunto; cruce por valor exacto. Sin lookups."""
    context = case.get("investigation_context", {})
    if context.get("adapter_version") == "backend-v1":
        items = deepcopy(context["ioc_evidence"])
        return {
            "status": "provided" if items else "no_disponible", "items": items,
            "note": "IoC suministrados por el caso. Enlaces declarados y coincidencias "
                    "observadas se registran por separado. Sin consultas externas.",
        }
    provided = case.get("enrichment")
    if not isinstance(provided, list) or not provided:
        return {"status": "no_disponible", "items": [],
                "note": "El caso no trae enriquecimiento de IoC; no se hicieron consultas externas."}

    items = []
    for ioc in provided:
        value = ioc.get("indicator") or ioc.get("value")
        matches = [
            {"alert_id": a["id"], "field": path}
            for a in alerts for path, text in a["string_values"] if value and text == value
        ]
        items.append({**ioc, "matched_alert_ids": sorted({m["alert_id"] for m in matches}),
                      "matched_fields": matches})
    unmatched = [str(i.get("indicator") or i.get("value") or "sin valor")
                 for i in items if not i["matched_alert_ids"]]
    note = "Enriquecimiento tomado del caso tal como vino; no se hicieron consultas externas."
    if unmatched:
        note += f" Sin coincidencia exacta en alertas: {', '.join(unmatched)}."
    return {"status": "provided", "items": items, "note": note}


def correlated_attack_analysis(alerts, mappings, synthetic, context):
    """Reuse the original analysis within related components and singleton alerts.

    An unrelated or uncertain alert is still investigated, but it cannot raise
    another component's confidence merely by sharing an ATT&CK technique.
    """
    groups = list(context["correlation"]["related_groups"])
    grouped = {aid for group in groups for aid in group}
    groups += [[a["id"]] for a in alerts if a["id"] not in grouped]
    combined = {"attack_mapping": [], "hypotheses": []}
    for group in groups:
        selected = [a for a in alerts if a["id"] in group]
        subset = []
        for mapping in mappings:
            ids = [aid for aid in mapping["supporting_alert_ids"] if aid in group]
            if ids:
                subset.append({**mapping, "supporting_alert_ids": ids})
        analysis = build_attack_analysis(selected, subset, synthetic)
        for values in analysis.values():
            for item in values:
                item["correlation_group_alert_ids"] = group
                for key in ("evidence", "evidence_for", "evidence_against"):
                    for ev in item.get(key, []):
                        ev["source_fields"] = deepcopy(context["signal_evidence"][ev["alert_id"]])
        for key in combined:
            combined[key].extend(analysis[key])
    combined["hypotheses"].sort(key=lambda h: -LEVELS.index(h["confidence"]))
    for rank, hypothesis in enumerate(combined["hypotheses"], 1):
        hypothesis["rank"] = rank
    return combined


def attach_ioc_references(hypotheses, enrichment):
    """Evidence supports the observable association, never an invented verdict."""
    output = deepcopy(hypotheses)
    for hypothesis in output:
        alert_ids = {e["alert_id"] for e in hypothesis["evidence_for"]}
        hypothesis["ioc_evidence"] = []
        for item in enrichment["items"]:
            for association in item.get("associations", []):
                if association["alert_id"] in alert_ids:
                    hypothesis["ioc_evidence"].append({
                        "evidence_id": item["evidence_id"],
                        "source_path": item["source_path"],
                        "alert_id": association["alert_id"],
                        "provider": item["provider"],
                        "observable": deepcopy(item["observable"]),
                        "association_methods": association["methods"],
                        "role": "context",
                        "relevance": "Enriquecimiento aportado para un observable asociado "
                                     "a esta evidencia. No confirma compromiso ni aumenta "
                                     "la confianza automáticamente.",
                    })
    return output


def build_actions(hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    seen = set()
    for hypothesis in hypotheses:
        if hypothesis["confidence"] == "insuficiente":
            continue
        priority = PRIORITY_BY_TACTIC.get(hypothesis["tactic"], "medium")
        if hypothesis["confidence"] == "baja":
            priority = PRIORITIES[max(PRIORITIES.index(priority) - 1, 0)]
        evidence_ids = [e["alert_id"] for e in hypothesis["evidence_for"]]
        for action in ACTIONS_BY_TACTIC.get(hypothesis["tactic"], []):
            if action in seen:
                continue
            seen.add(action)
            actions.append({
                "priority": priority,
                "action": action,
                "rationale": f"Derivada de la hipótesis {hypothesis['rank']} (confianza {hypothesis['confidence']}).",
                "evidence_ids": evidence_ids,
                "requires_human_approval": True,
            })
    actions.sort(key=lambda a: -PRIORITIES.index(a["priority"]))
    return actions


def build_limitations(case: Dict[str, Any], input_summary: Dict[str, Any]) -> List[str]:
    limitations = [
        "Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.",
        f"Los IDs ATT&CK provienen del {CATALOG_VERSION}; se reportan como candidatos.",
        "El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.",
    ]
    if case.get("synthetic"):
        limitations.append("Caso sintético: la confianza se limita a 'media' como máximo.")
    limitations += input_summary["warnings"]
    if input_summary["untrusted_instruction_fields"]:
        limitations.append(
            "Se detectó texto con forma de instrucción en "
            + ", ".join(input_summary["untrusted_instruction_fields"])
            + "; se trató como dato no confiable y no se siguió."
        )
    return limitations


def executive_summary(case: Dict[str, Any], chain: Dict[str, Any], hypotheses: List[Dict[str, Any]],
                      processed: int) -> str:
    if not hypotheses:
        return (f"Caso {case.get('case_id')}: {processed} alertas procesadas. Ninguna coincide con el "
                "catálogo de técnicas; no se sostiene una hipótesis de ataque con estos datos.")
    top = hypotheses[0]
    return (f"Caso {case.get('case_id')}: {processed} alertas procesadas. {chain['summary']} "
            f"Hipótesis principal: {top['statement']} Confianza {top['confidence']}. "
            "Ningún compromiso se da por confirmado hasta la revisión del analista.")
