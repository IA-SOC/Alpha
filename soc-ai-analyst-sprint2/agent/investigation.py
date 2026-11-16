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
from core.i18n import tr

LEVELS = ["insuficiente", "baja", "media", "alta"]

ANALYST_LEGITIMATE_TAG = "analyst_legitimate"
# Etiquetas que describen actividad legítima conocida. Si aparecen en el mismo
# host que la evidencia de una hipótesis, cuentan como evidencia en contra.
# The analyst tag only affects hypotheses whose evidence included that alert; it is
# deliberately not a same-host benign tag, so one mark cannot lower unrelated hypotheses.
BENIGN_TAGS = {"backup", "scheduled_task", "maintenance", "change_approved"}

def ALTERNATIVES() -> Dict[str, List[str]]:
    """Return localized alternatives at call time, not at module import time."""
    return {
        "Credential Access": [tr("Usuario legítimo que olvidó su contraseña o script con credenciales vencidas.", "Legitimate user who forgot their password, or a script with expired credentials.")],
        "Lateral Movement": [tr("Tarea administrativa o de respaldo legítima entre servidores.", "Legitimate administrative or backup task between servers.")],
        "Initial Access": [tr("Correo legítimo de proveedor clasificado como sospechoso por la regla.", "Legitimate vendor email classified as suspicious by the rule.")],
        "Execution": [tr("Herramienta de administración remota (PsExec) usada por soporte de TI.", "Remote administration tool (PsExec) used by IT support.")],
        "Exfiltration": [tr("Replicación o respaldo externo autorizado.", "Authorized replication or external backup.")],
        "Impact": [tr("Cifrado o limpieza legítima por software de respaldo/DLP.", "Legitimate encryption or cleanup by backup/DLP software.")],
    }


def UNKNOWNS() -> Dict[str, List[str]]:
    """Return localized uncertainty statements at call time."""
    return {
        "Credential Access": [tr("No hay telemetría de EDR que confirme ejecución posterior al acceso.", "No EDR telemetry confirms execution after access.")],
        "Lateral Movement": [tr("Falta confirmar si la sesión remota tenía un cambio aprobado.", "It remains unconfirmed whether the remote session had an approved change.")],
        "Initial Access": [tr("No se sabe si el usuario introdujo credenciales en el sitio.", "It is unknown whether the user entered credentials on the site.")],
        "Execution": [tr("Se desconoce qué binario ejecutó el servicio y con qué privilegios.", "The binary run by the service and its privileges are unknown.")],
        "Exfiltration": [tr("Se desconoce el contenido y el volumen exacto transferido.", "The exact transferred content and volume are unknown.")],
        "Impact": [tr("Se desconoce el alcance total de archivos afectados y el estado de backups.", "The full scope of affected files and backup status are unknown.")],
    }

PRIORITY_BY_TACTIC = {
    "Impact": "urgent",
    "Exfiltration": "urgent",
    "Lateral Movement": "high",
    "Execution": "high",
    "Credential Access": "high",
    "Initial Access": "medium",
}
PRIORITIES = ["low", "medium", "high", "urgent"]

def CATALOG_VERSION() -> str:
    return tr("catálogo local core/logic.RULES (sin versión ATT&CK fijada)", "local catalog core/logic.RULES (ATT&CK version not pinned)")


def WAZUH_VERSION() -> str:
    return tr("rule.mitre nativo de Wazuh (sin versión ATT&CK fijada)", "native Wazuh rule.mitre (ATT&CK version not pinned)")


def _evidence(alert: Dict[str, Any], role: str, relevance: str,
              mapping_source: str | None = None) -> Dict[str, Any]:
    evidence = {
        "alert_id": alert["id"],
        "role": role,
        "fields": [f for f in ("rule_name", "tags", "host", "user") if alert.get(f)],
        "observation": tr(
            f"{alert['rule_name'] or 'sin regla'} en {alert.get('host') or 'host desconocido'}"
            + (f" (usuario {alert['user']})" if alert.get("user") else ""),
            f"{alert['rule_name'] or 'no rule'} on {alert.get('host') or 'unknown host'}"
            + (f" (user {alert['user']})" if alert.get("user") else ""),
        ),
        "relevance": relevance,
        "source_fields": deepcopy(alert["source_fields"]),
    }
    if mapping_source:
        evidence["mapping_source"] = mapping_source
    return evidence


def ordinal_confidence(support: List[Dict[str, Any]], against: List[Dict[str, Any]],
                       synthetic: bool) -> Dict[str, str]:
    """Rúbrica de references/protocolo.md aplicada de forma determinista."""
    distinct_rules = {a["rule_name"] for a in support}
    if len(support) >= 3 and len(distinct_rules) >= 2:
        level, basis = 3, tr(f"{len(support)} alertas con {len(distinct_rules)} reglas distintas coinciden", f"{len(support)} alerts with {len(distinct_rules)} distinct rules match")
    elif len(support) >= 2:
        level, basis = 2, tr(f"{len(support)} alertas coherentes, sin corroboración de otra fuente", f"{len(support)} consistent alerts, without corroboration from another source")
    elif support:
        level, basis = 1, tr("una única alerta sostiene la hipótesis", "a single alert supports the hypothesis")
    else:
        level, basis = 0, tr("no hay alertas que sostengan la hipótesis", "no alerts support the hypothesis")

    reasons = []
    if against:
        level -= 1
        reasons.append(tr(f"{len(against)} alerta(s) sugieren actividad legítima", f"{len(against)} alert(s) suggest legitimate activity"))
    if any(a["timestamp_problem"] for a in support):
        level -= 1
        reasons.append(tr("hay timestamps sin zona horaria o inválidos", "timestamps have no time zone or are invalid"))
    if synthetic and level > 2:
        level = 2
        reasons.append(tr("el caso es sintético", "the case is synthetic"))
    level = max(level, 0)

    text = basis + (tr(". Se ajusta a la baja: ", ". Downward adjustment: ") + "; ".join(reasons) if reasons else "") + "."
    return {"confidence": LEVELS[level], "confidence_basis": text[0].upper() + text[1:]}


def build_attack_analysis(alerts: List[Dict[str, Any]], mappings: List[Dict[str, Any]],
                          synthetic: bool) -> Dict[str, List[Dict[str, Any]]]:
    """Mapeo MITRE del MCP server -> attack_mapping + hypotheses (fase 2)."""
    by_id = {a["id"]: a for a in alerts}
    attack_mapping, hypotheses = [], []

    for mapping in mappings:
        alert_sources = mapping.get("alert_mapping_sources", {})
        mapped_support = [by_id[i] for i in mapping["supporting_alert_ids"] if i in by_id]
        analyst_legitimate = [a for a in mapped_support if ANALYST_LEGITIMATE_TAG in a["tags"]]
        support = [a for a in mapped_support if a not in analyst_legitimate]
        hosts = {a.get("host") for a in mapped_support}
        against = [
            a for a in alerts
            if a["id"] not in mapping["supporting_alert_ids"]
            and a.get("host") in hosts and BENIGN_TAGS & set(a["tags"])
        ]
        against += analyst_legitimate
        tactic = mapping["tactic"]

        attack_mapping.append({
            "tactic": tactic,
            "technique_id": mapping["technique_id"],
            "technique_name": mapping["technique_name"],
            # The rule still matched every mapped alert; analyst marks only change the status.
            "status": "not_supported" if analyst_legitimate and not support else "candidate",
            "evidence": [_evidence(a, "supporting", tr(f"Señal que coincide con el patrón de {mapping['technique_name']}.", f"Signal matching the {mapping['technique_name']} pattern."),
                                   alert_sources.get(a["id"]))
                         for a in mapped_support],
            "mapping_source": mapping.get("mapping_source", "local_catalog"),
            "alert_mapping_sources": alert_sources,
            "ambiguous": mapping.get("ambiguous", False),
            "source_version": WAZUH_VERSION() if mapping.get("mapping_source") == "wazuh_rule_mitre"
                              else CATALOG_VERSION() if mapping.get("mapping_source") == "local_catalog"
                              else f"{WAZUH_VERSION()}; {CATALOG_VERSION()}",
        })

        confidence = ordinal_confidence(support, against, synthetic)
        hypotheses.append({
            "statement": tr(
                f"Actividad compatible con {mapping['technique_name']} "
                f"({mapping['technique_id']}, táctica {tactic}) en {', '.join(sorted(h for h in hosts if h))}.",
                f"Activity consistent with {mapping['technique_name']} "
                f"({mapping['technique_id']}, tactic {tactic}) on {', '.join(sorted(h for h in hosts if h))}.",
            ),
            "tactic": tactic,
            **confidence,
            "evidence_for": [_evidence(a, "supporting", tr("Alerta que coincide con el patrón de la técnica.", "Alert matching the technique pattern."),
                                         alert_sources.get(a["id"])) for a in support],
            "evidence_against": [_evidence(a, "contradicting", tr("Actividad legítima conocida en el mismo host y ventana.", "Known legitimate activity on the same host and time window."))
                                 for a in against],
            "alternatives": ALTERNATIVES().get(tactic, []),
            "unknowns": UNKNOWNS().get(tactic, []),
        })
        for evidence in hypotheses[-1]["evidence_against"]:
            if evidence["alert_id"] in {alert["id"] for alert in analyst_legitimate}:
                evidence["relevance"] = tr("Marcada como legitima por el analista (seguimiento).", "Marked as legitimate by the analyst (follow-up).")

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
            "description": event["description"] or tr("Evento sin descripción de regla", "Event without a rule description"),
            "stage": event["stage"],
            "alert_ids": [alert["id"]],
            "certainty": "observed",
            "source_fields": deepcopy(alert["source_fields"]),
        })
    return timeline


def build_blast_radius(alerts: List[Dict[str, Any]], hypotheses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fase 3: activos observados vs. sospechosos. Nada se marca como confirmado."""
    observed: Dict[str, Dict[str, Any]] = {}
    observed_entities: Dict[tuple[str, str], Dict[str, Any]] = {}

    def add_entity(kind: str, value: Any, alert_id: str) -> None:
        if not isinstance(value, str) or not value:
            return
        entry = observed_entities.setdefault(
            (kind, value),
            {"entity": value, "entity_type": kind, "basis_alert_ids": []},
        )
        if alert_id not in entry["basis_alert_ids"]:
            entry["basis_alert_ids"].append(alert_id)

    for alert in alerts:
        host = alert.get("host")
        if host:
            entry = observed.setdefault(
                host, {"asset": host, "basis_alert_ids": [], "rules": []}
            )
            if alert["id"] not in entry["basis_alert_ids"]:
                entry["basis_alert_ids"].append(alert["id"])
            if alert["rule_name"] and alert["rule_name"] not in entry["rules"]:
                entry["rules"].append(alert["rule_name"])
            add_entity("host", host, alert["id"])
        add_entity("user", alert.get("user"), alert["id"])
        add_entity("source_ip", alert.get("source_ip"), alert["id"])
        add_entity("destination_ip", alert.get("dest_ip"), alert["id"])
    observed_assets = [
        {"asset": e["asset"], "basis_alert_ids": e["basis_alert_ids"],
         "observed_activity": "; ".join(e["rules"]) or tr("actividad sin regla nombrada", "activity without a named rule")}
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
        tr("Ningún activo se marca como confirmado: requiere validación del analista o telemetría adicional (EDR).", "No asset is marked confirmed: analyst validation or additional EDR telemetry is required."),
    ]
    for host, ids in ambiguous.items():
        if host not in suspected:
            unknowns.append(tr(f"Actividad ambigua en {host} (alertas {', '.join(ids)}): hipótesis de confianza baja o insuficiente.", f"Ambiguous activity on {host} (alerts {', '.join(ids)}): low or insufficient-confidence hypothesis."))
    if any(not a.get("host") for a in alerts):
        unknowns.append(tr("Hay alertas sin host identificado.", "Some alerts have no identified host."))

    return {
        "observed_assets": observed_assets,
        "observed_entities": list(observed_entities.values()),
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
            "note": tr("IoC suministrados por el caso. Enlaces declarados y coincidencias observadas se registran por separado. Sin consultas externas.", "IoCs supplied by the case. Declared links and observed matches are recorded separately. No external queries."),
        }
    provided = case.get("enrichment")
    if not isinstance(provided, list) or not provided:
        return {"status": "no_disponible", "items": [],
                "note": tr("El caso no trae enriquecimiento de IoC; no se hicieron consultas externas.", "The case has no IoC enrichment; no external queries were made.")}

    items = []
    for ioc in provided:
        value = ioc.get("indicator") or ioc.get("value")
        matches = [
            {"alert_id": a["id"], "field": path}
            for a in alerts for path, text in a["string_values"] if value and text == value
        ]
        items.append({**ioc, "matched_alert_ids": sorted({m["alert_id"] for m in matches}),
                      "matched_fields": matches})
    unmatched = [str(i.get("indicator") or i.get("value") or tr("sin valor", "no value"))
                 for i in items if not i["matched_alert_ids"]]
    note = tr("Enriquecimiento tomado del caso tal como vino; no se hicieron consultas externas.", "Enrichment was taken from the case as provided; no external queries were made.")
    if unmatched:
        note += tr(f" Sin coincidencia exacta en alertas: {', '.join(unmatched)}.", f" No exact match in alerts: {', '.join(unmatched)}.")
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
                # Procedencia solo de las alertas del grupo, no de otros grupos.
                sources = {i: s for i, s in mapping.get("alert_mapping_sources", {}).items()
                           if i in ids}
                kinds = set(sources.values())
                subset.append({
                    **mapping,
                    "supporting_alert_ids": ids,
                    "alert_mapping_sources": sources,
                    "mapping_source": (next(iter(kinds)) if len(kinds) == 1
                                       else "mixed" if kinds
                                       else mapping.get("mapping_source", "local_catalog")),
                })
        analysis = build_attack_analysis(selected, subset, synthetic)
        for values in analysis.values():
            for item in values:
                item["correlation_group_alert_ids"] = group
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
                        "relevance": tr("Enriquecimiento aportado para un observable asociado a esta evidencia. No confirma compromiso ni aumenta la confianza automáticamente.", "Enrichment provided for an observable associated with this evidence. It does not confirm compromise or increase confidence automatically."),
                    })
    return output


def build_actions(hypotheses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    by_action = {}
    confidence_by_rank = {hypothesis["rank"]: hypothesis["confidence"] for hypothesis in hypotheses}
    for hypothesis in hypotheses:
        if hypothesis["confidence"] == "insuficiente":
            continue
        priority = PRIORITY_BY_TACTIC.get(hypothesis["tactic"], "medium")
        if hypothesis["confidence"] == "baja":
            priority = PRIORITIES[max(PRIORITIES.index(priority) - 1, 0)]
        evidence_ids = [e["alert_id"] for e in hypothesis["evidence_for"]]
        for action in ACTIONS_BY_TACTIC.get(hypothesis["tactic"], []):
            existing = by_action.get(action)
            if existing:
                if hypothesis["rank"] not in existing["hypothesis_ranks"]:
                    existing["hypothesis_ranks"].append(hypothesis["rank"])
                    existing["hypothesis_ranks"].sort()
                for evidence_id in evidence_ids:
                    if evidence_id not in existing["evidence_ids"]:
                        existing["evidence_ids"].append(evidence_id)
                ranks = ", ".join(map(str, existing["hypothesis_ranks"]))
                confidences = ", ".join(confidence_by_rank[rank] for rank in existing["hypothesis_ranks"])
                existing["rationale"] = tr(f"Derivada de las hipótesis {ranks} (confianza {confidences}).", f"Derived from hypotheses {ranks} (confidence {confidences}).")
                continue
            entry = {
                "priority": priority,
                "action": action,
                "rationale": tr(f"Derivada de la hipótesis {hypothesis['rank']} (confianza {hypothesis['confidence']}).", f"Derived from hypothesis {hypothesis['rank']} (confidence {hypothesis['confidence']})."),
                "evidence_ids": list(evidence_ids),  # own copy: merges must not leak into sibling actions
                "requires_human_approval": True,
                "hypothesis_ranks": [hypothesis["rank"]],
                "approval_status": "pending",
            }
            by_action[action] = entry
            actions.append(entry)
    actions.sort(key=lambda a: -PRIORITIES.index(a["priority"]))
    return actions


def build_limitations(case: Dict[str, Any], input_summary: Dict[str, Any]) -> List[str]:
    limitations = [
        tr("Motor determinista basado en reglas (core/logic.py); no usa un LLM y no cubre patrones fuera del catálogo.", "Deterministic rule-based engine (core/logic.py); it does not use an LLM and does not cover patterns outside the catalog."),
        tr(f"Los IDs ATT&CK provienen del {CATALOG_VERSION()}; se reportan como candidatos.", f"ATT&CK IDs come from {CATALOG_VERSION()}; they are reported as candidates."),
        tr("El validador de la skill comprueba estructura y referencias, no la veracidad de las inferencias.", "The skill validator checks structure and references, not the truth of inferences."),
    ]
    if case.get("synthetic"):
        limitations.append(tr("Caso sintético: la confianza se limita a 'media' como máximo.", "Synthetic case: confidence is capped at 'media'."))
    limitations += input_summary["warnings"]
    if input_summary["untrusted_instruction_fields"]:
        limitations.append(
            tr(
                "Se detectó texto con forma de instrucción en "
                + ", ".join(input_summary["untrusted_instruction_fields"])
                + "; se trató como dato no confiable y no se siguió.",
                "Instruction-like text was detected in "
                + ", ".join(input_summary["untrusted_instruction_fields"])
                + "; it was treated as untrusted data and not followed.",
            )
        )
    return limitations


def executive_summary(case: Dict[str, Any], chain: Dict[str, Any], hypotheses: List[Dict[str, Any]],
                      processed: int) -> str:
    if not hypotheses:
        return tr(
            f"Caso {case.get('case_id')}: {processed} alertas procesadas. Ninguna coincide con el catálogo de técnicas; no se sostiene una hipótesis de ataque con estos datos.",
            f"Case {case.get('case_id')}: {processed} alerts processed. None match the technique catalog; these data do not support an attack hypothesis.",
        )
    top = hypotheses[0]
    return tr(
        f"Caso {case.get('case_id')}: {processed} alertas procesadas. {chain['summary']} Hipótesis principal: {top['statement']} Confianza {top['confidence']}. Ningún compromiso se da por confirmado hasta la revisión del analista.",
        f"Case {case.get('case_id')}: {processed} alerts processed. {chain['summary']} Primary hypothesis: {top['statement']} Confidence {top['confidence']}. No compromise is considered confirmed until analyst review.",
    )
