"""Reporte legible según skills/soc-case-investigator/templates/reporte.md."""
from typing import Any, Dict, List

from app.services.report_formatter import _safe, render_audience_markdown


def _model_review_markdown(report: Dict[str, Any]) -> str:
    """Model output is untrusted text: escaped and kept apart from the engine's findings."""
    review = report.get("model_review")
    if not review:
        return ""
    lines = ["", "## Model second opinion", "",
             "Advisory only: it does not change hypotheses, confidence or actions.", ""]
    if review["status"] == "ok":
        lines.append(f"- Provider/model: {_safe(review['provider'])} / {_safe(review['model'])}; "
                     f"latency {review['latency_ms']} ms.")
        for item in review["items"]:
            lines.append(f"- Hypothesis {item['rank']}: {_safe(item['assessment'])}. {_safe(item['explanation'])} "
                         f"Alerts: {_safe(', '.join(item['cited_alert_ids']))}.")
    else:
        lines.append(f"- Status: {_safe(review['status'])}. {_safe(review.get('error', ''))}")
    return "\n".join(lines) + "\n"


def _follow_up_markdown(report: Dict[str, Any]) -> str:
    follow_up = report.get("follow_up")
    if not follow_up:
        return ""
    instruction = follow_up["instruction"]
    lines = ["", "## Analyst follow-up", "",
             f"- Instruction: {_safe(instruction['type'])}.",
             f"- Analyst: {_safe(instruction['analyst'])}.",
             f"- Alert IDs: {_safe(', '.join(instruction['alert_ids']))}."]
    if instruction.get("note"):
        lines.append(f"- Note: {_safe(instruction['note'])}.")
    for change in follow_up["changes"]:
        if change["change"] != "unchanged":
            lines.append(f"- {_safe(change['technique_id'])}: {_safe(change['change'])} "
                         f"({change['confidence_before']} -> {change['confidence_after']}).")
    return "\n".join(lines) + "\n"


def _ids(ids: List[Any]) -> str:
    return ", ".join(map(str, ids)) if ids else "—"


def render_markdown(report: Dict[str, Any]) -> str:
    if "audience_sections" in report:
        return (render_audience_markdown(report) + _model_review_markdown(report)
                + _follow_up_markdown(report))
    inp = report["input"]
    window = inp.get("time_window_utc") or {}
    blast = report["blast_radius"]
    lines = [
        "# Reporte de investigación SOC — borrador",
        "",
        "## Caso y alcance",
        f"- ID del caso: {report['case_id']}",
        f"- Fuente/esquema y versión: {inp['source_format']} / {inp.get('schema_version') or 'no declarada'}",
        f"- Alertas recibidas / procesadas: {inp['alert_count']} / {inp['processed_alert_count']}",
        f"- Ventana temporal: {window.get('start', '?')} → {window.get('end', '?')}",
        f"- Limitaciones de entrada: {'; '.join(inp.get('missing_fields') or []) or 'ninguna detectada'}",
        "",
        "## Resumen",
        report["executive_summary"],
        "",
        "## Hipótesis ordenadas",
    ]
    if not report["hypotheses"]:
        lines.append("_Sin hipótesis sostenidas por los datos._")
    for h in report["hypotheses"]:
        lines += [
            f"### {h['rank']}. {h['statement']} — confianza: {h['confidence']}",
            f"- Base de confianza: {h['confidence_basis']}",
            f"- Evidencia a favor: {_ids([e['alert_id'] for e in h['evidence_for']])}",
            f"- Evidencia en contra: {_ids([e['alert_id'] for e in h['evidence_against']])}",
            f"- Alternativas plausibles: {'; '.join(h.get('alternatives') or []) or '—'}",
            f"- Información que falta: {'; '.join(h['unknowns']) or '—'}",
            "",
        ]
        for evidence in h.get("ioc_evidence", []):
            lines.append(f"- IoC: {evidence['evidence_id']} ({evidence['provider']}), "
                         f"alerta {evidence['alert_id']}, origen {evidence['source_path']}.")
    if report.get("correlation"):
        lines += ["", "## Correlación de alertas"]
        for rel in report["correlation"]["relationships"]:
            lines.append(f"- {rel['relationship_id']}: {_ids(rel['alert_ids'])} — "
                         f"{rel['classification']} ({rel['rule']}). {rel['explanation']}.")
    lines += ["## Mapeo MITRE ATT&CK", "| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |", "|---|---|---|---|"]
    for m in report["attack_mapping"]:
        lines.append(f"| {m['tactic']} | {m['technique_id']} {m['technique_name']} | {m['status']} | "
                     f"{_ids([e['alert_id'] for e in m['evidence']])} |")
    lines += ["", "## Línea de tiempo", "| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |", "|---|---|---|---|"]
    undated = [t for t in report["timeline"] if not t["timestamp_utc"]]
    for t in report["timeline"]:
        if undated and t is undated[0]:
            lines += ["", "### Eventos sin hora UTC utilizable (fuera de la secuencia)",
                      "| Hora original | Estado de zona | Evento observado o inferido | Alertas fuente |", "|---|---|---|---|"]
        utc = t["timestamp_utc"] or ("zona desconocida" if t["timezone_unknown"] else "sin timestamp")
        lines.append(f"| {t['timestamp_original'] or '—'} | {utc} | {t['description']} ({t['certainty']}) | {_ids(t['alert_ids'])} |")
    lines += [
        "",
        "## Blast radius",
        "- Activos observados (no equivale a compromiso): "
        + ("; ".join(f"{a['asset']} [{_ids(a['basis_alert_ids'])}]" for a in blast["observed_assets"]) or "—"),
        "- Activos con impacto confirmado: "
        + ("; ".join(a["asset"] for a in blast["confirmed_assets"]) or "ninguno"),
        "- Sospechosos: " + ("; ".join(f"{a['asset']} [{_ids(a['basis_alert_ids'])}]" for a in blast["suspected_assets"]) or "—"),
        "- Identidades afectadas (sospechosas): "
        + ("; ".join(f"{i['identity']} [{_ids(i['basis_alert_ids'])}]" for i in blast.get("suspected_identities", [])) or "—"),
        "- Desconocidos / brechas de telemetría: " + "; ".join(blast["unknowns"]),
        "",
        "## IoC enriquecidos provistos",
        f"Estado: {report['enrichment']['status']}. {report['enrichment'].get('note') or ''}",
    ]
    for item in report["enrichment"]["items"]:
        lines.append(f"- {item.get('indicator') or item.get('value')} ({item.get('type')}, "
                     f"veredicto {item.get('verdict', 'no interpretado')}, fuente {item.get('source')}) "
                     f"→ alertas: {_ids(item['matched_alert_ids'])}")
        if item.get("associations"):
            lines.append("  Asociaciones: " + "; ".join(
                f"{a['alert_id']} ({', '.join(a['methods'])})" for a in item["associations"]))
    lines += ["", "## Acciones recomendadas"]
    for i, a in enumerate(report["recommended_actions"], start=1):
        lines.append(f"{i}. [{a['priority']}] {a['action']} — {a['rationale']} Hipótesis: {_ids(a['hypothesis_ranks'])}. "
                     f"Evidencia: {_ids(a['evidence_ids'])}. Pendiente de aprobación del analista.")
    if not report["recommended_actions"]:
        lines.append("_Sin acciones propuestas._")
    lines += ["", "## Limitaciones"] + [f"- {l}" for l in report["limitations"]]
    review = report["review"]
    lines += [
        "",
        "## Revisión humana",
        f"- Estado: {review['status']}",
        f"- Analista: {review.get('analyst') or '—'}",
        f"- Correcciones/notas: {review.get('notes') or '—'}",
    ]
    return "\n".join(lines) + "\n" + _follow_up_markdown(report)
