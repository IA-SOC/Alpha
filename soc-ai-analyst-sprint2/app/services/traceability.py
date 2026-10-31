"""Verify new evidence pointers against the original accepted payload."""

import re

from app.services.report_formatter import validate_audience_sections
from core.report_contract import validate_report


def _resolve_pointer(document: dict, pointer: str):
    """Resolve a strict RFC 6901 pointer while distinguishing absent from null."""
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return False, None
    parts = pointer[1:].split("/")
    if any(re.search(r"~(?:[^01]|$)", part) for part in parts):
        return False, None
    value = document
    for part in parts:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if part not in value:
                return False, None
            value = value[part]
        elif isinstance(value, list) and part.isascii() and part.isdecimal():
            if (len(part) > 1 and part.startswith("0")) or int(part) >= len(value):
                return False, None
            value = value[int(part)]
        else:
            return False, None
    return True, value


def verify_traceability(context: dict, report: dict) -> None:
    validate_report(report)
    validate_audience_sections(report)
    original = context["original_case"]
    alerts = original["alerts"]
    alert_indexes = {a["alert_id"]: i for i, a in enumerate(alerts)}
    known = set(alert_indexes)
    iocs = {i["evidence_id"]: i for i in context["ioc_evidence"]}

    def check_ref(alert_id):
        if not isinstance(alert_id, str) or alert_id not in known:
            raise ValueError("Unknown evidence alert")

    def check_field(field):
        check_ref(field["alert_id"])
        prefix = f"/alerts/{alert_indexes[field['alert_id']]}/raw_alert/"
        if (
            not isinstance(field.get("path"), str)
            or not field["path"].startswith(prefix)
        ):
            raise ValueError("Evidence pointer belongs to a different alert")
        exists, observed = _resolve_pointer(original, field["path"])
        if not exists or observed != field["value"]:
            raise ValueError("Evidence value differs from the original payload")

    def check_alert_ids(values):
        for alert_id in values:
            check_ref(alert_id)

    def check_evidence(items):
        for evidence in items:
            check_ref(evidence["alert_id"])
            for field in evidence.get("source_fields", []):
                check_field(field)
                if field["alert_id"] != evidence["alert_id"]:
                    raise ValueError("Finding evidence cites a different alert")

    correlation = report.get("correlation")
    if correlation is not None:
        if correlation != context["correlation"]:
            raise ValueError("Correlation differs from adapted case context")
        for rel in correlation["relationships"]:
            check_alert_ids(rel["alert_ids"])
            for evidence in rel["evidence"]:
                for field in evidence["fields"]:
                    check_field(field)
        for disposition in correlation["alerts"]:
            check_ref(disposition["alert_id"])
        for group in correlation["related_groups"]:
            check_alert_ids(group)
        check_alert_ids(correlation["noise_alert_ids"])

    for item in report["enrichment"]["items"]:
        expected = iocs.get(item["evidence_id"])
        if expected is None:
            raise ValueError("Unknown enrichment evidence reference")
        if item != expected:
            raise ValueError("Enrichment was changed after adaptation")
        exists, supplied = _resolve_pointer(original, item["source_path"])
        if not exists or not isinstance(supplied, dict):
            raise ValueError("Invalid enrichment source path")
        if item["source_path"] != expected["source_path"]:
            raise ValueError("Invalid enrichment source path")
        for key, value in supplied.items():
            if item[key] != value:
                raise ValueError("Provider evidence was not preserved")
        for association in item["associations"]:
            check_ref(association["alert_id"])
            if association["reference_path"] is not None:
                exists, reference = _resolve_pointer(
                    original, association["reference_path"]
                )
                if not exists or reference != association["alert_id"]:
                    raise ValueError("Invalid declared IoC reference")
            for field in association["fields"]:
                check_field(field)
                if field["alert_id"] != association["alert_id"]:
                    raise ValueError("IoC evidence cites a different alert")
        check_alert_ids(item["associated_alert_ids"])
        check_alert_ids(item["matched_alert_ids"])

    for entry in report["timeline"]:
        check_alert_ids(entry["alert_ids"])
        for field in entry["source_fields"]:
            check_field(field)
            if field["alert_id"] not in entry["alert_ids"]:
                raise ValueError("Timeline evidence cites another alert")
    for mapping in report["attack_mapping"]:
        check_evidence(mapping["evidence"])
    for hypothesis in report["hypotheses"]:
        for key in ("evidence_for", "evidence_against"):
            check_evidence(hypothesis[key])
        for evidence in hypothesis.get("ioc_evidence", []):
            item = iocs.get(evidence["evidence_id"])
            if item is None:
                raise ValueError("Unknown hypothesis IoC evidence reference")
            check_ref(evidence["alert_id"])
            if (
                evidence["alert_id"] not in item["associated_alert_ids"]
                or evidence["source_path"] != item["source_path"]
                or evidence["provider"] != item["provider"]
                or evidence["observable"] != item["observable"]
            ):
                raise ValueError("Broken hypothesis IoC evidence reference")

    blast = report["blast_radius"]
    for section in (
        "observed_assets",
        "confirmed_assets",
        "suspected_assets",
        "confirmed_identities",
        "suspected_identities",
    ):
        for entity in blast.get(section, []):
            check_alert_ids(entity["basis_alert_ids"])
    for action in report["recommended_actions"]:
        check_alert_ids(action["evidence_ids"])
