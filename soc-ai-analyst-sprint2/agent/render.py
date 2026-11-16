"""Reporte legible según skills/soc-case-investigator/templates/reporte.md."""
from typing import Any, Dict, List

from app.services.report_formatter import _safe, render_audience_markdown
from core.i18n import tr


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


def _probable_noise_markdown(report: Dict[str, Any]) -> str:
    matches = (report.get("correlation") or {}).get("probable_noise", [])
    if not matches:
        return ""
    lines = ["", "## Probable noise", ""]
    for match in matches:
        lines.append(
            f"- Alert {_safe(match['alert_id'])} matched process rule "
            f"{_safe(match['rule_id'])}. Evidence retained for review."
        )
    return "\n".join(lines) + "\n"


def render_markdown(report: Dict[str, Any]) -> str:
    if "audience_sections" in report:
        return (render_audience_markdown(report) + _probable_noise_markdown(report)
                + _model_review_markdown(report)
                + _follow_up_markdown(report))
    inp = report["input"]
    window = inp.get("time_window_utc") or {}
    blast = report["blast_radius"]
    lines = [
        tr("# Reporte de investigación SOC — borrador", "# SOC investigation report — draft"),
        "",
        tr("## Caso y alcance", "## Case and scope"),
        tr(f"- ID del caso: {report['case_id']}", f"- Case ID: {report['case_id']}"),
        tr(f"- Fuente/esquema y versión: {inp['source_format']} / {inp.get('schema_version') or 'no declarada'}", f"- Source/schema and version: {inp['source_format']} / {inp.get('schema_version') or 'not declared'}"),
        tr(f"- Alertas recibidas / procesadas: {inp['alert_count']} / {inp['processed_alert_count']}", f"- Alerts received / processed: {inp['alert_count']} / {inp['processed_alert_count']}"),
        tr(f"- Ventana temporal: {window.get('start', '?')} → {window.get('end', '?')}", f"- Time window: {window.get('start', '?')} → {window.get('end', '?')}"),
        tr(f"- Limitaciones de entrada: {'; '.join(inp.get('missing_fields') or []) or 'ninguna detectada'}", f"- Input limitations: {'; '.join(inp.get('missing_fields') or []) or 'none detected'}"),
        "",
        tr("## Resumen", "## Summary"),
        report["executive_summary"],
        "",
        tr("## Hipótesis ordenadas", "## Ranked hypotheses"),
    ]
    if not report["hypotheses"]:
        lines.append(tr("_Sin hipótesis sostenidas por los datos._", "_No hypotheses supported by the data._"))
    for h in report["hypotheses"]:
        lines += [
            tr(f"### {h['rank']}. {h['statement']} — confianza: {h['confidence']}", f"### {h['rank']}. {h['statement']} — confidence: {h['confidence']}"),
            tr(f"- Base de confianza: {h['confidence_basis']}", f"- Confidence basis: {h['confidence_basis']}"),
            tr(f"- Evidencia a favor: {_ids([e['alert_id'] for e in h['evidence_for']])}", f"- Supporting evidence: {_ids([e['alert_id'] for e in h['evidence_for']])}"),
            tr(f"- Evidencia en contra: {_ids([e['alert_id'] for e in h['evidence_against']])}", f"- Contradictory evidence: {_ids([e['alert_id'] for e in h['evidence_against']])}"),
            tr(f"- Alternativas plausibles: {'; '.join(h.get('alternatives') or []) or '—'}", f"- Plausible alternatives: {'; '.join(h.get('alternatives') or []) or '—'}"),
            tr(f"- Información que falta: {'; '.join(h['unknowns']) or '—'}", f"- Missing information: {'; '.join(h['unknowns']) or '—'}"),
            "",
        ]
        for evidence in h.get("ioc_evidence", []):
            lines.append(tr(f"- IoC: {evidence['evidence_id']} ({evidence['provider']}), alerta {evidence['alert_id']}, origen {evidence['source_path']}.", f"- IoC: {evidence['evidence_id']} ({evidence['provider']}), alert {evidence['alert_id']}, source {evidence['source_path']}."))
    if report.get("correlation"):
        lines += ["", tr("## Correlación de alertas", "## Alert correlation")]
        for rel in report["correlation"]["relationships"]:
            lines.append(f"- {rel['relationship_id']}: {_ids(rel['alert_ids'])} — "
                         f"{rel['classification']} ({rel['rule']}). {rel['explanation']}.")
    lines += [tr("## Mapeo MITRE ATT&CK", "## MITRE ATT&CK mapping"), tr("| Táctica | Técnica (ID y nombre) | Estado | Evidencia referenciada |", "| Tactic | Technique (ID and name) | Status | Referenced evidence |"), "|---|---|---|---|"]
    for m in report["attack_mapping"]:
        lines.append(f"| {m['tactic']} | {m['technique_id']} {m['technique_name']} | {m['status']} | "
                     f"{_ids([e['alert_id'] for e in m['evidence']])} |")
    lines += ["", tr("## Línea de tiempo", "## Timeline"), tr("| Hora original | Hora UTC / estado de zona | Evento observado o inferido | Alertas fuente |", "| Original time | UTC time / zone status | Observed or inferred event | Source alerts |"), "|---|---|---|---|"]
    undated = [t for t in report["timeline"] if not t["timestamp_utc"]]
    for t in report["timeline"]:
        if undated and t is undated[0]:
            lines += ["", tr("### Eventos sin hora UTC utilizable (fuera de la secuencia)", "### Events without usable UTC time (outside the sequence)"), tr("| Hora original | Estado de zona | Evento observado o inferido | Alertas fuente |", "| Original time | Zone status | Observed or inferred event | Source alerts |"), "|---|---|---|---|"]
        utc = t["timestamp_utc"] or tr("zona desconocida" if t["timezone_unknown"] else "sin timestamp", "unknown zone" if t["timezone_unknown"] else "no timestamp")
        lines.append(f"| {t['timestamp_original'] or '—'} | {utc} | {t['description']} ({t['certainty']}) | {_ids(t['alert_ids'])} |")
    lines += [
        "",
        "## Blast radius",
        tr("- Activos observados (no equivale a compromiso): ", "- Observed assets (not equivalent to compromise): ")
        + ("; ".join(f"{a['asset']} [{_ids(a['basis_alert_ids'])}]" for a in blast["observed_assets"]) or "—"),
        tr("- Activos con impacto confirmado: ", "- Assets with confirmed impact: ")
        + ("; ".join(a["asset"] for a in blast["confirmed_assets"]) or tr("ninguno", "none")),
        tr("- Sospechosos: ", "- Suspected: ") + ("; ".join(f"{a['asset']} [{_ids(a['basis_alert_ids'])}]" for a in blast["suspected_assets"]) or "—"),
        tr("- Identidades afectadas (sospechosas): ", "- Affected identities (suspected): ")
        + ("; ".join(f"{i['identity']} [{_ids(i['basis_alert_ids'])}]" for i in blast.get("suspected_identities", [])) or "—"),
        tr("- Desconocidos / brechas de telemetría: ", "- Unknowns / telemetry gaps: ") + "; ".join(blast["unknowns"]),
        "",
        tr("## IoC enriquecidos provistos", "## Provided enriched IoCs"),
        tr(f"Estado: {report['enrichment']['status']}. {report['enrichment'].get('note') or ''}", f"Status: {report['enrichment']['status']}. {report['enrichment'].get('note') or ''}"),
    ]
    for item in report["enrichment"]["items"]:
        lines.append(tr(f"- {item.get('indicator') or item.get('value')} ({item.get('type')}, veredicto {item.get('verdict', 'no interpretado')}, fuente {item.get('source')}) → alertas: {_ids(item['matched_alert_ids'])}", f"- {item.get('indicator') or item.get('value')} ({item.get('type')}, verdict {item.get('verdict', 'not interpreted')}, source {item.get('source')}) → alerts: {_ids(item['matched_alert_ids'])}"))
        if item.get("associations"):
            lines.append(tr("  Asociaciones: ", "  Associations: ") + "; ".join(
                f"{a['alert_id']} ({', '.join(a['methods'])})" for a in item["associations"]))
    lines += ["", tr("## Acciones recomendadas", "## Recommended actions")]
    for i, a in enumerate(report["recommended_actions"], start=1):
        lines.append(tr(f"{i}. [{a['priority']}] {a['action']} — {a['rationale']} Hipótesis: {_ids(a['hypothesis_ranks'])}. Evidencia: {_ids(a['evidence_ids'])}. Pendiente de aprobación del analista.", f"{i}. [{a['priority']}] {a['action']} — {a['rationale']} Hypotheses: {_ids(a['hypothesis_ranks'])}. Evidence: {_ids(a['evidence_ids'])}. Pending analyst approval."))
    if not report["recommended_actions"]:
        lines.append(tr("_Sin acciones propuestas._", "_No actions proposed._"))
    lines += ["", tr("## Limitaciones", "## Limitations")] + [f"- {l}" for l in report["limitations"]]
    review = report["review"]
    lines += [
        "",
        tr("## Revisión humana", "## Human review"),
        tr(f"- Estado: {review['status']}", f"- Status: {review['status']}"),
        tr(f"- Analista: {review.get('analyst') or '—'}", f"- Analyst: {review.get('analyst') or '—'}"),
        tr(f"- Correcciones/notas: {review.get('notes') or '—'}", f"- Corrections/notes: {review.get('notes') or '—'}"),
    ]
    return ("\n".join(lines) + "\n" + _probable_noise_markdown(report)
            + _follow_up_markdown(report))
