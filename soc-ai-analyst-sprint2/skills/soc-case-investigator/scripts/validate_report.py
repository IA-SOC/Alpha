#!/usr/bin/env python3
"""Validate report structure and resolve alert references.

This checks structure and referential traceability only. It cannot determine
whether a security inference is factually correct.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from core.report_contract import report_errors

REQUIRED = {
    "case_id", "input", "executive_summary", "attack_mapping", "hypotheses",
    "timeline", "blast_radius", "enrichment", "recommended_actions",
    "limitations", "review",
}
CONFIDENCE = {"alta", "media", "baja", "insuficiente"}
REPORT_FORMATS = {"elastic_ecs", "elastic_security", "wazuh", "mixed", "unknown"}


def load(path: str) -> Any:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def get_path(obj: Any, path: str) -> Any:
    for part in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(part)
    return obj


def alert_list(case: Any) -> list[dict]:
    """Handle simple arrays and common Elastic/Wazuh export envelopes."""
    if isinstance(case, list):
        return [x for x in case if isinstance(x, dict)]
    if not isinstance(case, dict):
        return []
    for key in ("alerts", "events", "hits"):
        value = case.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    # Elasticsearch search response: hits.hits[]._id + _source.
    nested_hits = get_path(case, "hits.hits")
    if isinstance(nested_hits, list):
        normalized = []
        for hit in nested_hits:
            if not isinstance(hit, dict):
                continue
            source = hit.get("_source")
            item = dict(source) if isinstance(source, dict) else {}
            if hit.get("_id") not in (None, ""):
                item["_id"] = hit["_id"]
            normalized.append(item)
        return normalized
    # A single alert record is also accepted.
    return [case]


def alert_id(alert: dict, index: int) -> str:
    for path in ("alert_id", "id", "_id", "event.id", "kibana.alert.uuid"):
        value = get_path(alert, path)
        if value not in (None, ""):
            return str(value)
    return f"alert-{index:03d}"


def as_list(value: Any, location: str, errors: list[str]) -> list:
    if not isinstance(value, list):
        errors.append(f"{location}: expected array")
        return []
    return value


def nonempty_text(obj: dict, key: str, location: str, errors: list[str]) -> None:
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        errors.append(f"{location}.{key}: required non-empty text")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="Input case JSON")
    parser.add_argument("--report", required=True, help="Output report JSON")
    args = parser.parse_args()
    errors: list[str] = []

    try:
        case = load(args.case)
        report = load(args.report)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read valid JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(report, dict):
        print("ERROR: report root must be a JSON object", file=sys.stderr)
        return 2

    schema_errors = report_errors(report)
    if schema_errors:
        print("REPORT VALIDATION FAILED")
        for error in schema_errors:
            print(f"- {error}")
        return 1

    missing = sorted(REQUIRED - report.keys())
    if missing:
        errors.append("missing report keys: " + ", ".join(missing))

    nonempty_text(report, "case_id", "report", errors)
    if "executive_summary" in report:
        nonempty_text(report, "executive_summary", "report", errors)

    alerts = alert_list(case)
    known = {alert_id(item, i + 1) for i, item in enumerate(alerts)}
    input_obj = report.get("input")
    if not isinstance(input_obj, dict):
        errors.append("input: expected object")
    else:
        source_format = input_obj.get("source_format")
        if source_format not in REPORT_FORMATS:
            errors.append(f"input.source_format must be one of {sorted(REPORT_FORMATS)}")
        supplied = input_obj.get("alert_count")
        processed = input_obj.get("processed_alert_count")
        if not isinstance(supplied, int) or isinstance(supplied, bool) or supplied < 0:
            errors.append("input.alert_count must be a non-negative integer")
        elif supplied != len(alerts):
            errors.append(f"input.alert_count={supplied}, but case contains {len(alerts)} alert(s)")
        if not isinstance(processed, int) or isinstance(processed, bool) or processed < 0:
            errors.append("input.processed_alert_count must be a non-negative integer")
        elif isinstance(supplied, int) and processed > supplied:
            errors.append("processed_alert_count exceeds alert_count")

    def check_ref(ref: Any, location: str) -> None:
        if not isinstance(ref, str) or not ref:
            errors.append(f"{location}: alert_id must be a non-empty string")
        elif ref not in known:
            errors.append(f"{location}: unknown alert_id {ref!r}")

    def check_evidence(items: Any, location: str) -> int:
        evidence = as_list(items, location, errors)
        for i, item in enumerate(evidence):
            where = f"{location}[{i}]"
            if not isinstance(item, dict):
                errors.append(f"{where}: expected object")
                continue
            check_ref(item.get("alert_id"), where)
            if item.get("role") not in {"supporting", "contradicting", "context"}:
                errors.append(f"{where}.role: invalid evidence role")
            nonempty_text(item, "observation", where, errors)
            nonempty_text(item, "relevance", where, errors)
        return len(evidence)

    attack_mapping = as_list(report.get("attack_mapping"), "attack_mapping", errors)
    for i, item in enumerate(attack_mapping):
        where = f"attack_mapping[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        nonempty_text(item, "technique_name", where, errors)
        if item.get("status") not in {"candidate", "supported", "not_supported", "unknown"}:
            errors.append(f"{where}.status: invalid mapping status")
        evidence_count = check_evidence(item.get("evidence"), f"{where}.evidence")
        if evidence_count == 0:
            errors.append(f"{where}.evidence: at least one evidence item is required")
        technique_id = item.get("technique_id")
        if technique_id is not None and not re.fullmatch(r"T[0-9]{4}(?:\.[0-9]{3})?", str(technique_id)):
            errors.append(f"{where}.technique_id: invalid ATT&CK ID format")

    hypotheses = as_list(report.get("hypotheses"), "hypotheses", errors)
    hypothesis_ranks = set()
    for i, item in enumerate(hypotheses):
        where = f"hypotheses[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        if not isinstance(item.get("rank"), int) or isinstance(item.get("rank"), bool) or item["rank"] < 1:
            errors.append(f"{where}.rank: expected positive integer")
        else:
            hypothesis_ranks.add(item["rank"])
        nonempty_text(item, "statement", where, errors)
        if item.get("confidence") not in CONFIDENCE:
            errors.append(f"{where}.confidence must be one of {sorted(CONFIDENCE)}")
        nonempty_text(item, "confidence_basis", where, errors)
        for name in ("evidence_for", "evidence_against"):
            check_evidence(item.get(name), f"{where}.{name}")
        if not item.get("evidence_for") and not item.get("evidence_against"):
            errors.append(f"{where}: at least one evidence reference is required")
        for name in ("unknowns", "alternatives"):
            if name in item and not isinstance(item[name], list):
                errors.append(f"{where}.{name}: expected array")

    timeline = as_list(report.get("timeline"), "timeline", errors)
    for i, item in enumerate(timeline):
        where = f"timeline[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        if "timestamp_original" not in item:
            errors.append(f"{where}.timestamp_original: required")
        nonempty_text(item, "description", where, errors)
        if item.get("certainty") not in {"observed", "inferred", "unknown"}:
            errors.append(f"{where}.certainty: invalid certainty")
        refs = as_list(item.get("alert_ids"), f"{where}.alert_ids", errors)
        if not refs:
            errors.append(f"{where}.alert_ids: at least one alert reference is required")
        for j, ref in enumerate(refs):
            check_ref(ref, f"{where}.alert_ids[{j}]")

    actions = as_list(report.get("recommended_actions"), "recommended_actions", errors)
    for i, item in enumerate(actions):
        where = f"recommended_actions[{i}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: expected object")
            continue
        if item.get("priority") not in {"urgent", "high", "medium", "low"}:
            errors.append(f"{where}.priority: invalid priority")
        nonempty_text(item, "action", where, errors)
        nonempty_text(item, "rationale", where, errors)
        refs = as_list(item.get("evidence_ids"), f"{where}.evidence_ids", errors)
        if not refs:
            errors.append(f"{where}.evidence_ids: at least one alert reference is required")
        for j, ref in enumerate(refs):
            check_ref(ref, f"{where}.evidence_ids[{j}]")
        if item.get("requires_human_approval") is not True:
            errors.append(f"{where}.requires_human_approval must be true")
        if item.get("approval_status") != "pending":
            errors.append(f"{where}.approval_status must be pending")
        ranks = as_list(item.get("hypothesis_ranks"), f"{where}.hypothesis_ranks", errors)
        if not ranks:
            errors.append(f"{where}.hypothesis_ranks: at least one hypothesis rank is required")
        for j, rank in enumerate(ranks):
            if type(rank) is not int or rank not in hypothesis_ranks:
                errors.append(f"{where}.hypothesis_ranks[{j}]: unknown hypothesis rank {rank!r}")

    blast = report.get("blast_radius")
    if not isinstance(blast, dict):
        errors.append("blast_radius: expected object")
    else:
        if "observed_entities" in blast:
            entities = as_list(
                blast["observed_entities"], "blast_radius.observed_entities", errors
            )
            for i, entity in enumerate(entities):
                where = f"blast_radius.observed_entities[{i}]"
                if not isinstance(entity, dict):
                    errors.append(f"{where}: expected object")
                    continue
                nonempty_text(entity, "entity", where, errors)
                nonempty_text(entity, "entity_type", where, errors)
                refs = as_list(
                    entity.get("basis_alert_ids"), f"{where}.basis_alert_ids", errors
                )
                if not refs:
                    errors.append(
                        f"{where}.basis_alert_ids: "
                        "at least one alert reference is required"
                    )
                for j, ref in enumerate(refs):
                    check_ref(ref, f"{where}.basis_alert_ids[{j}]")
        for field in ("observed_assets", "confirmed_assets", "suspected_assets"):
            entities = as_list(blast.get(field), f"blast_radius.{field}", errors)
            for i, entity in enumerate(entities):
                where = f"blast_radius.{field}[{i}]"
                if not isinstance(entity, dict):
                    errors.append(f"{where}: expected object")
                    continue
                nonempty_text(entity, "asset", where, errors)
                if field == "observed_assets":
                    nonempty_text(entity, "observed_activity", where, errors)
                refs = as_list(entity.get("basis_alert_ids"), f"{where}.basis_alert_ids", errors)
                if not refs:
                    errors.append(f"{where}.basis_alert_ids: at least one alert reference is required")
                for j, ref in enumerate(refs):
                    check_ref(ref, f"{where}.basis_alert_ids[{j}]")
        for field in ("confirmed_identities", "suspected_identities"):
            entities = as_list(blast.get(field), f"blast_radius.{field}", errors)
            for i, entity in enumerate(entities):
                where = f"blast_radius.{field}[{i}]"
                if not isinstance(entity, dict):
                    errors.append(f"{where}: expected object")
                    continue
                nonempty_text(entity, "identity", where, errors)
                refs = as_list(entity.get("basis_alert_ids"), f"{where}.basis_alert_ids", errors)
                if not refs:
                    errors.append(f"{where}.basis_alert_ids: at least one alert reference is required")
                for j, ref in enumerate(refs):
                    check_ref(ref, f"{where}.basis_alert_ids[{j}]")
        if not isinstance(blast.get("unknowns"), list):
            errors.append("blast_radius.unknowns: expected array")

    for field in ("limitations",):
        if not isinstance(report.get(field), list):
            errors.append(f"{field}: expected array")

    model_review = report.get("model_review")
    if model_review is not None:
        if not isinstance(model_review, dict):
            errors.append("model_review: expected object")
        elif model_review.get("status") == "ok":
            for i, item in enumerate(as_list(model_review.get("items"), "model_review.items", errors)):
                where = f"model_review.items[{i}]"
                if not isinstance(item, dict):
                    errors.append(f"{where}: expected object")
                    continue
                if item.get("rank") not in hypothesis_ranks:
                    errors.append(f"{where}.rank: unknown hypothesis rank")
                if item.get("assessment") not in {"supports", "weak", "contradicts"}:
                    errors.append(f"{where}.assessment: invalid assessment")
                refs = as_list(item.get("cited_alert_ids"), f"{where}.cited_alert_ids", errors)
                if not refs:
                    errors.append(f"{where}.cited_alert_ids: at least one alert reference is required")
                for j, ref in enumerate(refs):
                    check_ref(ref, f"{where}.cited_alert_ids[{j}]")

    follow_up = report.get("follow_up")
    if follow_up is not None:
        if not isinstance(follow_up, dict):
            errors.append("follow_up: expected object")
        else:
            instruction = follow_up.get("instruction")
            if not isinstance(instruction, dict):
                errors.append("follow_up.instruction: expected object")
            else:
                refs = as_list(instruction.get("alert_ids"), "follow_up.instruction.alert_ids", errors)
                for i, ref in enumerate(refs):
                    check_ref(ref, f"follow_up.instruction.alert_ids[{i}]")
            changes = as_list(follow_up.get("changes"), "follow_up.changes", errors)
            for i, change in enumerate(changes):
                if not isinstance(change, dict):
                    errors.append(f"follow_up.changes[{i}]: expected object")
                elif change.get("change") != "removed" and change.get("confidence_after") not in CONFIDENCE:
                    errors.append(f"follow_up.changes[{i}].confidence_after: invalid confidence")

    review = report.get("review")
    if not isinstance(review, dict):
        errors.append("review: expected object")
    elif review.get("status") not in {"pending", "validated", "corrected", "rejected"}:
        errors.append("review.status must be pending, validated, corrected, or rejected")

    if errors:
        print("REPORT VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"REPORT STRUCTURE OK — {len(alerts)} input alert(s); referenced IDs resolve.")
    print("NOTE: This validates structure and references, not the truth of the findings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
