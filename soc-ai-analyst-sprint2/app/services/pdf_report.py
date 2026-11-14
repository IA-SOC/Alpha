"""Generate a shareable PDF from a validated investigation result."""

from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _text(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, (dict, list)):
        return escape(str(value))
    return escape(str(value))


def _paragraph(value: Any, style) -> Paragraph:
    return Paragraph(_text(value).replace("\n", "<br/>"), style)


def _table(rows: list[list[Any]], styles) -> Table:
    table = Table(rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b7c9d6")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, "#eef4f8"]),
            ]
        )
    )
    return table


def build_investigation_pdf(result: dict) -> bytes:
    """Return a PDF containing technical findings and analyst decisions."""
    report = result["report"]
    styles = getSampleStyleSheet()
    styles.add(
        styles["Title"].clone("ReportTitle", alignment=TA_CENTER, fontSize=18)
    )
    styles["Heading1"].spaceBefore = 12
    styles["Heading2"].spaceBefore = 8
    body = styles["BodyText"]
    body.leading = 13
    small = styles["BodyText"].clone("SmallBody", fontSize=8, leading=10)
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"Investigation report {result['case_id']}",
        pageCompression=0,
    )
    story = [
        Paragraph("SOC Investigation Report", styles["ReportTitle"]),
        Spacer(1, 5 * mm),
        _paragraph(f"Case ID: {result['case_id']}", body),
        _paragraph(f"Generated at: {report.get('generated_at', '—')}", body),
    ]

    story.append(Paragraph("Technical findings", styles["Heading1"]))
    findings = report.get("hypotheses", [])
    if findings:
        rows = [[
            _paragraph("Rank", small),
            _paragraph("Finding", small),
            _paragraph("Confidence", small),
            _paragraph("Evidence", small),
        ]]
        for finding in findings:
            evidence = [
                item.get("alert_id", item.get("evidence_id", "—"))
                for item in finding.get("evidence_for", [])
            ]
            rows.append(
                [
                    _paragraph(finding.get("rank"), small),
                    _paragraph(finding.get("statement"), small),
                    _paragraph(finding.get("confidence"), small),
                    _paragraph(", ".join(map(str, evidence)), small),
                ]
            )
        story.append(_table(rows, styles))
    else:
        story.append(_paragraph("No technical findings were produced.", body))

    story.append(Paragraph("Evidence", styles["Heading1"]))
    evidence_rows = [[
        _paragraph("Finding", small),
        _paragraph("Supporting alerts", small),
        _paragraph("Contradicting alerts", small),
        _paragraph("Unknowns", small),
    ]]
    for finding in findings:
        evidence_rows.append(
            [
                _paragraph(finding.get("rank"), small),
                _paragraph(
                    ", ".join(
                        item.get("alert_id", "—")
                        for item in finding.get("evidence_for", [])
                    ),
                    small,
                ),
                _paragraph(
                    ", ".join(
                        item.get("alert_id", "—")
                        for item in finding.get("evidence_against", [])
                    ),
                    small,
                ),
                _paragraph("; ".join(finding.get("unknowns", [])), small),
            ]
        )
    if len(evidence_rows) == 1:
        evidence_rows.append([_paragraph("—", small)] * 4)
    story.append(_table(evidence_rows, styles))

    story.append(Paragraph("MITRE ATT&CK mappings", styles["Heading1"]))
    mappings = report.get("attack_mapping", [])
    mapping_rows = [[
        _paragraph("Tactic", small),
        _paragraph("Technique", small),
        _paragraph("Status", small),
        _paragraph("Evidence", small),
    ]]
    for mapping in mappings:
        mapping_rows.append(
            [
                _paragraph(mapping.get("tactic"), small),
                _paragraph(
                    f"{mapping.get('technique_id', '—')} "
                    f"{mapping.get('technique_name', '—')}",
                    small,
                ),
                _paragraph(mapping.get("status"), small),
                _paragraph(
                    ", ".join(
                        item.get("alert_id", "—")
                        for item in mapping.get("evidence", [])
                    ),
                    small,
                ),
            ]
        )
    if len(mapping_rows) == 1:
        mapping_rows.append([_paragraph("—", small)] * 4)
    story.append(_table(mapping_rows, styles))

    story.append(Paragraph("Analyst decisions", styles["Heading1"]))
    review = report.get("review") or {}
    story.extend(
        [
            _paragraph(f"Status: {review.get('status')}", body),
            _paragraph(f"Analyst: {review.get('analyst')}", body),
            _paragraph(f"Notes: {review.get('notes')}", body),
        ]
    )
    decisions = review.get("findings", [])
    if decisions:
        decision_rows = [[
            _paragraph("Finding", small),
            _paragraph("Decision", small),
            _paragraph("Notes", small),
        ]]
        for decision in decisions:
            decision_rows.append(
                [
                    _paragraph(decision.get("finding_key"), small),
                    _paragraph(decision.get("status"), small),
                    _paragraph(decision.get("notes"), small),
                ]
            )
        story.append(_table(decision_rows, styles))

    document.build(story)
    return buffer.getvalue()
