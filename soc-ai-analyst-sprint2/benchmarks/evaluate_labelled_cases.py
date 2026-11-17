"""Compare structured MITRE claims in saved SOC reports against labelled cases."""

import argparse
import json
from pathlib import Path


def read_object(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def read_list(value, name):
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    return value


def read_id(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def evaluate_case(labels, report):
    """Score technique IDs and their case-specific alert citations."""
    expected = {}
    for technique, evidence in read_object(labels, "Case labels").items():
        read_id(technique, "Labelled technique_id")
        expected[technique] = {
            read_id(alert_id, "Labelled alert_id")
            for alert_id in read_list(evidence, "Expected alert IDs")
        }
        if not expected[technique]:
            raise ValueError(f"Expected evidence is empty for {technique}")

    observed = {}
    for mapping in read_list(report.get("attack_mapping"), "attack_mapping"):
        mapping = read_object(mapping, "Mapping")
        status = mapping.get("status")
        if status in ("not_supported", "unknown"):
            continue
        if status not in ("candidate", "supported"):
            raise ValueError("Invalid mapping status")
        technique = read_id(mapping.get("technique_id"), "Reported technique_id")
        references = observed.setdefault(technique, set())
        for item in read_list(mapping.get("evidence"), "Mapping evidence"):
            alert_id = read_object(item, "Evidence").get("alert_id")
            references.add(read_id(alert_id, "Reported alert_id"))

    unsupported = []
    for technique, cited in sorted(observed.items()):
        if technique not in expected:
            unsupported.append({"technique_id": technique, "reason": "unlabelled"})
        elif cited - expected[technique]:
            unsupported.append({
                "technique_id": technique,
                "reason": "citation_not_labelled_for_technique",
                "alert_ids": sorted(cited - expected[technique]),
            })

    missing_evidence = []
    for technique, required in sorted(expected.items()):
        missing = required - observed.get(technique, set())
        if missing:
            missing_evidence.append({
                "technique_id": technique,
                "alert_ids": sorted(missing),
            })

    return {
        "agreement": expected.keys() == observed.keys(),
        "matching_techniques": sorted(expected.keys() & observed.keys()),
        "missing_techniques": sorted(expected.keys() - observed.keys()),
        "unsupported_claims": unsupported,
        "missing_evidence": missing_evidence,
    }


def evaluate(labels, reports):
    labels = read_object(labels, "Labels")
    seen = set()
    cases = []
    for result in reports:
        result = read_object(result, "Investigation result")
        report = read_object(result.get("report", result), "Report")
        case_id = read_id(report.get("case_id"), "Report case_id")
        if case_id in seen:
            raise ValueError(f"Duplicate report for case {case_id}")
        if case_id not in labels:
            raise ValueError(f"No labels for case {case_id}")
        seen.add(case_id)
        cases.append({"case_id": case_id, **evaluate_case(labels[case_id], report)})

    if not cases:
        raise ValueError("At least one case is required")
    missing_reports = sorted(labels.keys() - seen)
    if missing_reports:
        raise ValueError(f"Missing reports for cases: {', '.join(missing_reports)}")

    agreements = sum(case["agreement"] for case in cases)
    return {
        "case_count": len(cases),
        "cases_with_technique_agreement": agreements,
        "technique_agreement_rate": agreements / len(cases),
        "unsupported_claim_count": sum(len(case["unsupported_claims"]) for case in cases),
        "missing_evidence_count": sum(
            len(item["alert_ids"]) for case in cases for item in case["missing_evidence"]
        ),
        "cases": cases,
    }


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", type=Path)
    parser.add_argument("reports", nargs="+", type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(load_json(args.labels), map(load_json, args.reports))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
