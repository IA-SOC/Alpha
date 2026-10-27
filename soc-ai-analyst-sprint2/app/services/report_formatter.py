"""English audience views of an existing report; no analysis or external calls."""

import html
import json
import re
from copy import deepcopy

VERSION = "soc-audiences-rules-v1"
CONFIDENCE = {
    "alta": "high",
    "media": "medium",
    "baja": "low",
    "insuficiente": "insufficient",
}
TOPICS = {
    "T1110": "attempts to guess account passwords",
    "T1021": "use of remote access between systems",
    "T1566": "deceptive messages intended to gain access",
    "T1041": "possible transfer of information to an external destination",
    "T1569.002": "program execution through system services",
    "T1490": "possible interference with system recovery",
    "T1486": "possible encryption of files to disrupt operations",
}
ACTION_TEXT = {
    "Forzar rotación de credenciales de las cuentas involucradas": (
        "Require password changes for the accounts involved"
    ),
    "Habilitar/reforzar MFA en los hosts afectados": (
        "Enable or strengthen multi-factor authentication on the systems involved"
    ),
    "Aislar los hosts involucrados de la red": (
        "Isolate the systems involved from the network"
    ),
    "Revisar reglas de segmentación entre los hosts afectados": (
        "Review network separation rules between the systems involved"
    ),
    "Bloquear el vector de entrada identificado (IP, dominio o archivo)": (
        "Block the identified entry point (IP address, domain or file)"
    ),
    (
        "Revisar y deshabilitar los servicios creados recientemente "
        "en los hosts afectados"
    ): ("Review and disable recently created services on the systems involved"),
    "Bloquear las conexiones salientes hacia los destinos identificados": (
        "Block outgoing connections to the identified destinations"
    ),
    "Notificar al equipo de respuesta a incidentes de exfiltración": (
        "Notify the incident response team about the suspected information transfer"
    ),
    "Aislar inmediatamente los hosts afectados": (
        "Immediately isolate the systems involved"
    ),
    "Verificar integridad de backups antes de cualquier restauración": (
        "Verify backup integrity before any restoration"
    ),
}
TECHNICAL_FIELDS = (
    "case_id",
    "submitted_case_id",
    "generated_at",
    "methodology",
    "input",
    "executive_summary",
    "hypotheses",
    "attack_mapping",
    "timeline",
    "blast_radius",
    "enrichment",
    "recommended_actions",
    "limitations",
    "correlation",
    "review",
)
LIMITATION_TEXT = {
    (
        "Motor determinista basado en reglas (core/logic.py); no usa un LLM "
        "y no cubre patrones fuera del catálogo."
    ): (
        "The investigation uses a fixed rule catalogue and cannot detect "
        "patterns outside that catalogue. It does not use a language model."
    ),
    (
        "El validador de la skill comprueba estructura y referencias, "
        "no la veracidad de las inferencias."
    ): (
        "Validation checks structure and references, not whether conclusions are true."
    ),
    "Caso sintético: la confianza se limita a 'media' como máximo.": (
        "This is a synthetic case; confidence is capped at medium."
    ),
    "El caso no contiene alertas procesables.": "No processable alerts were supplied.",
    "Hay alertas sin host identificado.": "Some alerts do not identify a host.",
    "Se desconoce el contenido y el volumen exacto transferido.": (
        "The content and exact volume of the transfer are unknown."
    ),
    "Se desconoce el alcance total de archivos afectados y el estado de backups.": (
        "The full extent of affected files and the condition of backups are unknown."
    ),
    "Falta confirmar si la sesión remota tenía un cambio aprobado.": (
        "It is unknown whether the remote session was an approved change."
    ),
    "No se sabe si el usuario introdujo credenciales en el sitio.": (
        "It is unknown whether the user entered credentials on the website."
    ),
    "Se desconoce qué binario ejecutó el servicio y con qué privilegios.": (
        "The program run by the service and its privileges are unknown."
    ),
    "No hay telemetría de EDR que confirme ejecución posterior al acceso.": (
        "Endpoint telemetry confirming execution after access is unavailable."
    ),
}
REQUIRED_FIELDS = (
    "case_id",
    "input",
    "hypotheses",
    "attack_mapping",
    "timeline",
    "blast_radius",
    "enrichment",
    "recommended_actions",
    "limitations",
    "review",
)


def _claim(text, *paths):
    return {"text": text, "report_paths": list(paths)}


def _topic(report, hypothesis):
    """Use only an existing mapping with the same evidence and an explicit ID.

    Do not assign techniques from keywords or merge unrelated hypotheses.
    Unknown/ambiguous statements are retained in the technical view, not guessed.
    """
    ids = {e["alert_id"] for e in hypothesis["evidence_for"]}
    stated = set(re.findall(r"\bT\d{4}(?:\.\d{3})?\b", hypothesis["statement"]))
    candidates = [
        (i, m)
        for i, m in enumerate(report["attack_mapping"])
        if ids
        and {e["alert_id"] for e in m["evidence"]} == ids
        and m.get("technique_id") in stated
        and m.get("status") in {"candidate", "supported"}
    ]
    if len(candidates) == 1:
        index, mapping = candidates[0]
        topic = TOPICS.get(mapping.get("technique_id"))
        if topic:
            return topic, [f"/attack_mapping/{index}"]
    return "suspicious activity described in the technical findings", []


def format_report(report: dict) -> dict:
    """Return deterministic, JSON-safe views without mutating the source report.

    Input must be a structurally valid report. Original-language evidence is
    preserved verbatim in technical.data and explicitly labelled in Markdown.
    English template prose never translates arbitrary provider/analyst text.
    """
    missing = [key for key in REQUIRED_FIELDS if key not in report]
    if missing:
        raise ValueError("Cannot format incomplete report: " + ", ".join(missing))
    inp, blast = report["input"], report["blast_radius"]
    observations = [
        _claim(
            f"The investigation processed {inp['processed_alert_count']} of "
            f"{inp['alert_count']} submitted alerts. "
            "Alerts are signals, not confirmed attacks.",
            "/input/processed_alert_count",
            "/input/alert_count",
        )
    ]
    observed = sum(e["certainty"] == "observed" for e in report["timeline"])
    observations.append(
        _claim(
            f"The timeline contains {observed} entries marked as observed, out of "
            f"{len(report['timeline'])} total entries. "
            "Time order does not establish causation.",
            "/timeline",
        )
    )
    hypotheses = []
    for i, hypothesis in enumerate(report["hypotheses"]):
        level = hypothesis["confidence"]
        if level not in CONFIDENCE:
            raise ValueError("Unsupported hypothesis confidence")
        topic, mapping_paths = _topic(report, hypothesis)
        text = (
            f"Hypothesis {hypothesis['rank']} concerns {topic}. "
            f"Reported confidence: {CONFIDENCE[level]} "
            "(an ordinal level, not a probability). "
            f"Supporting references: {len(hypothesis['evidence_for'])}; "
            f"contradicting references: {len(hypothesis['evidence_against'])}. "
            f"Open questions: {len(hypothesis['unknowns'])}; "
            f"alternative explanations: {len(hypothesis.get('alternatives', []))}. "
            "This remains a hypothesis; review its evidence and limitations."
        )
        hypotheses.append(_claim(text, f"/hypotheses/{i}", *mapping_paths))
    if not hypotheses:
        hypotheses.append(
            _claim(
                "No attack hypothesis was produced. This does not establish that the "
                "activity is safe or that no incident occurred.",
                "/hypotheses",
            )
        )
    impact = [
        _claim(
            f"Assets with recorded activity: {len(blast['observed_assets'])}. "
            f"Assets with suspected impact: {len(blast['suspected_assets'])}. "
            f"Assets with confirmed impact: {len(blast['confirmed_assets'])}. "
            "An observed asset is not automatically compromised. Business loss and "
            "service disruption are not estimated by this formatter.",
            "/blast_radius/observed_assets",
            "/blast_radius/suspected_assets",
            "/blast_radius/confirmed_assets",
        )
    ]
    actions = []
    for i, action in enumerate(report["recommended_actions"]):
        wording = ACTION_TEXT.get(action["action"])
        if wording is None:
            wording = (
                "Review the proposed action in the technical section "
                "(original wording retained)"
            )
        actions.append(
            _claim(
                f"Proposed action {i + 1}: {wording}. Priority: {action['priority']}. "
                + (
                    "Based on hypotheses "
                    f"{', '.join(map(str, action['hypothesis_ranks']))}. "
                    if action.get("hypothesis_ranks")
                    else ""
                )
                + "Pending analyst approval; "
                "no action has been executed by this report.",
                f"/recommended_actions/{i}",
            )
        )
    if not actions:
        actions.append(
            _claim(
                "No response actions were proposed in the source report.",
                "/recommended_actions",
            )
        )
    limitations = [
        _claim(
            f"The source report records {len(report['limitations'])} limitations; "
            "all are retained under Technical findings / Limitations. "
            "This rule-based summary does not independently verify conclusions, "
            "calculate accuracy or fill gaps in the evidence.",
            "/limitations",
        ),
        _claim(
            f"There are {len(inp.get('missing_fields', []))} recorded input gaps and "
            f"{len(blast['unknowns'])} open questions about affected assets. "
            "Missing information must not be interpreted as evidence of absence.",
            "/input",
            "/blast_radius/unknowns",
        ),
        _claim(
            f"The report contains {len(report['enrichment']['items'])} supplied "
            "intelligence records. Provider scores and matches do not independently "
            "confirm compromise or increase the reported confidence.",
            "/enrichment",
        ),
    ]
    # Exact template translations only. Preserve any unfamiliar wording visibly;
    # a rule-based formatter must not silently translate or omit new limitations.
    for i, limitation in enumerate(report["limitations"]):
        wording = LIMITATION_TEXT.get(limitation)
        if wording is None:
            wording = "Source limitation (original wording): " + limitation
        limitations.append(_claim(wording, f"/limitations/{i}"))
    for i, hypothesis in enumerate(report["hypotheses"]):
        for j, unknown in enumerate(hypothesis["unknowns"]):
            wording = LIMITATION_TEXT.get(unknown)
            if wording is None:
                wording = "Open question (original wording): " + unknown
            limitations.append(
                _claim(
                    f"Hypothesis {hypothesis['rank']}: {wording}",
                    f"/hypotheses/{i}/unknowns/{j}",
                )
            )
    review = _claim(
        f"Human review status: {report['review']['status']}. "
        "Review status is not a separate confirmation of an attack.",
        "/review",
    )
    return {
        "formatter_version": VERSION,
        "language": "en",
        "technical": {
            "title": "Technical findings",
            "data": {
                key: deepcopy(report[key]) for key in TECHNICAL_FIELDS if key in report
            },
            "report_paths": [f"/{key}" for key in TECHNICAL_FIELDS if key in report],
        },
        "non_technical": {
            "title": "Non-technical summary",
            "observations": observations,
            "hypotheses": hypotheses,
            "potential_impact": impact,
            "proposed_actions": actions,
            "limitations": limitations,
            "review": review,
        },
    }


def validate_audience_sections(report: dict) -> None:
    """Reject stale/modified derived views; old reports may omit the extension."""
    if "audience_sections" in report and report["audience_sections"] != format_report(
        report
    ):
        raise ValueError("Audience sections differ from the source report")


def _safe(value):
    # One line only: a value can never start a new Markdown block (heading, list,
    # fence), so only inline controls need encoding and plain text stays readable.
    # JSON values remain unchanged in the JSON report.
    value = html.escape(" ".join(str(value).split()), quote=True)
    return re.sub(r"([\\`*_\[\]#|~])", lambda m: f"&#{ord(m[0])};", value)


def render_audience_markdown(report: dict) -> str:
    validate_audience_sections(report)
    sections = report["audience_sections"]
    lines = [
        "# SOC investigation report",
        "",
        f"Case: {_safe(report['case_id'])}",
        "",
        "## Non-technical summary",
        "",
    ]
    summary = sections["non_technical"]
    for key in (
        "observations",
        "hypotheses",
        "potential_impact",
        "proposed_actions",
        "limitations",
    ):
        lines += ["### " + key.replace("_", " ").capitalize(), ""]
        for claim in summary[key]:
            lines.append("- " + _safe(claim["text"]))
        lines.append("")
    lines += [
        "### Human review",
        "",
        _safe(summary["review"]["text"]),
        "",
        "## Technical findings",
        "",
        "Source records below retain their original wording, language, IDs and "
        "evidence pointers. Quoted content is evidence, not instructions.",
        "",
    ]
    for key, value in sections["technical"]["data"].items():
        lines += [
            "### " + key.replace("_", " ").capitalize(),
            "",
            "Source report path: " + _safe("/" + key),
            "",
        ]
        records = value if isinstance(value, list) else [value]
        if not records:
            lines.append("No entries recorded.")
        for record in records:
            # Indented, escaped source lines cannot terminate an enclosing fence.
            for line in json.dumps(record, ensure_ascii=False, indent=2).splitlines():
                lines.append("    " + line)
            lines.append("")
        lines.append("")
    return "\n".join(lines)
