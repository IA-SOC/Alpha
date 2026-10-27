"""Deterministic, bounded analyst follow-up for an existing report."""
from copy import deepcopy
from datetime import datetime, timezone
import re
from uuid import uuid4

from agent.normalize import normalize_case

TECHNIQUE = re.compile(r"T\d{4}(?:\.\d{3})?")


def validate_instruction(instruction, alerts):
    """Validate and normalize the only supported analyst follow-up instruction."""
    if not isinstance(instruction, dict):
        raise ValueError("La instruccion del analista debe ser un objeto.")
    if instruction.get("type") != "mark_legitimate":
        raise ValueError("El tipo de instruccion debe ser 'mark_legitimate'.")
    alert_ids = instruction.get("alert_ids")
    if not isinstance(alert_ids, list) or not alert_ids:
        raise ValueError("alert_ids debe ser una lista no vacia.")
    if len(alert_ids) > 50:
        raise ValueError("alert_ids no puede contener mas de 50 alertas.")
    if not all(isinstance(alert_id, str) for alert_id in alert_ids):
        raise ValueError("Cada alert_id debe ser una cadena de texto.")
    if len(set(alert_ids)) != len(alert_ids):
        raise ValueError("alert_ids no puede contener IDs repetidos.")
    known = {alert["id"] for alert in alerts}
    unknown = [alert_id for alert_id in alert_ids if alert_id not in known]
    if unknown:
        raise ValueError(f"alert_ids contiene un ID inexistente: {unknown[0]!r}.")
    analyst = instruction.get("analyst")
    if not isinstance(analyst, str) or not analyst.strip():
        raise ValueError("analyst debe ser una cadena no vacia.")
    note = instruction.get("note")
    if note is not None and not isinstance(note, str):
        raise ValueError("note debe ser una cadena de texto opcional.")
    if note is not None and len(note) > 500:
        raise ValueError("note no puede superar 500 caracteres.")
    return {"type": "mark_legitimate", "alert_ids": list(alert_ids),
            "analyst": analyst.strip(), "note": note}


def _hypothesis_key(hypothesis):
    technique = TECHNIQUE.search(hypothesis.get("statement", ""))
    return (technique.group(0) if technique else None,
            tuple(sorted(hypothesis.get("correlation_group_alert_ids") or [])))


def _hypotheses_by_key(report):
    return {_hypothesis_key(hypothesis): hypothesis for hypothesis in report.get("hypotheses", [])}


def _ids(hypothesis, field):
    return {item["alert_id"] for item in hypothesis.get(field, [])}


def build_follow_up(previous_report, revised_report, instruction):
    """Describe report differences by technique and correlation group."""
    before, after = _hypotheses_by_key(previous_report), _hypotheses_by_key(revised_report)
    changes = []
    for key in sorted(before.keys() | after.keys(), key=lambda value: str(value)):
        old, new = before.get(key), after.get(key)
        if old is None:
            change = "added"
        elif new is None:
            change = "removed"
        # A rank shift caused by another hypothesis is reported but is not a change.
        elif (old["confidence"], _ids(old, "evidence_for"),
              _ids(old, "evidence_against")) == (new["confidence"],
                                                 _ids(new, "evidence_for"),
                                                 _ids(new, "evidence_against")):
            change = "unchanged"
        else:
            change = "changed"
        changes.append({
            "technique_id": key[0],
            "rank_before": old.get("rank") if old else None,
            "rank_after": new.get("rank") if new else None,
            "confidence_before": old.get("confidence") if old else None,
            "confidence_after": new.get("confidence") if new else None,
            "evidence_for_removed": sorted(_ids(old, "evidence_for") - _ids(new, "evidence_for"))
            if old and new else [],
            "evidence_against_added": sorted(_ids(new, "evidence_against") - _ids(old, "evidence_against"))
            if old and new else [],
            "change": change,
        })
    return {"instruction": deepcopy(instruction),
            "requested_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "previous_generated_at": previous_report.get("generated_at"), "changes": changes}


async def run_follow_up(case, previous_report, instruction, thread_id, app=None):
    """Run the graph in a fresh checkpoint without changing caller-owned inputs."""
    case_copy, report_copy = deepcopy(case), deepcopy(previous_report)
    alerts, _ = normalize_case(case_copy)
    instruction_copy = validate_instruction(deepcopy(instruction), alerts)
    if app is None:
        from agent.graph import build_graph
        app = build_graph()
    config = {"configurable": {"thread_id": f"{thread_id}:follow-up:{uuid4()}"}}
    await app.ainvoke({"case": case_copy, "audit_log": [],
                       "analyst_instruction": instruction_copy,
                       "previous_report": report_copy}, config)
    return app.get_state(config).values
