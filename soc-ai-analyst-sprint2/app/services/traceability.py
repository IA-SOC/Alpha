"""Verify new evidence pointers against the original accepted payload."""

from app.services.case_service import native_identifier


def verify_traceability(context: dict, report: dict) -> None:
    original = context["original_case"]
    known = {a["alert_id"] for a in original["alerts"]}
    iocs = {i["evidence_id"]: i for i in context["ioc_evidence"]}

    def check_field(field):
        if field["alert_id"] not in known:
            raise ValueError("Unknown evidence alert")
        index = next(
            i
            for i, a in enumerate(original["alerts"])
            if a["alert_id"] == field["alert_id"]
        )
        if not field["path"].startswith(f"/alerts/{index}/raw_alert/"):
            raise ValueError("Evidence pointer belongs to a different alert")
        if native_identifier(original, field["path"]) != field["value"]:
            raise ValueError("Evidence value differs from the original payload")

    for rel in report["correlation"]["relationships"]:
        if not set(rel["alert_ids"]) <= known:
            raise ValueError("Unknown correlation alert")
        for evidence in rel["evidence"]:
            for field in evidence["fields"]:
                check_field(field)
    for item in report["enrichment"]["items"]:
        expected = iocs[item["evidence_id"]]
        if item != expected:
            raise ValueError("Enrichment was changed after adaptation")
        supplied = native_identifier(original, item["source_path"])
        for key, value in supplied.items():
            if item[key] != value:
                raise ValueError("Provider evidence was not preserved")
        for association in item["associations"]:
            if association["alert_id"] not in known:
                raise ValueError("Unknown IoC alert")
            if association["reference_path"] is not None:
                if (
                    native_identifier(original, association["reference_path"])
                    != association["alert_id"]
                ):
                    raise ValueError("Invalid declared IoC reference")
            for field in association["fields"]:
                check_field(field)
    for entry in report["timeline"]:
        for field in entry["source_fields"]:
            check_field(field)
            if field["alert_id"] not in entry["alert_ids"]:
                raise ValueError("Timeline evidence cites another alert")
    for mapping in report["attack_mapping"]:
        for evidence in mapping["evidence"]:
            for field in evidence["source_fields"]:
                check_field(field)
    for hypothesis in report["hypotheses"]:
        for key in ("evidence_for", "evidence_against"):
            for evidence in hypothesis[key]:
                for field in evidence["source_fields"]:
                    check_field(field)
        for evidence in hypothesis.get("ioc_evidence", []):
            item = iocs[evidence["evidence_id"]]
            if (
                evidence["alert_id"] not in item["associated_alert_ids"]
                or evidence["source_path"] != item["source_path"]
                or evidence["provider"] != item["provider"]
                or evidence["observable"] != item["observable"]
            ):
                raise ValueError("Broken hypothesis IoC evidence reference")
