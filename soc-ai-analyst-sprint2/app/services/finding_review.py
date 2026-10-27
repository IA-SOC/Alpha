
from collections import Counter


def finding_keys(report: dict) -> list[str]:
    seen = Counter()
    keys = []

    def add(key):
        seen[key] += 1
        keys.append(key if seen[key] == 1 else f"{key}#{seen[key]}")

    for hypothesis in sorted(report["hypotheses"], key=lambda h: h["rank"]):
        add(f"hypothesis:{hypothesis['statement']}")
    for technique in report["attack_mapping"]:
        label = " ".join(
            filter(
                None, [technique.get("technique_id"), technique.get("technique_name")]
            )
        )
        if technique.get("tactic"):
            label += f", {technique['tactic']}"
        add(f"technique:{label}")
    return keys


def validate_finding_decisions(report, decision):
    if not decision.run_id:
        raise ValueError("Per-finding decisions require run_id")
    supplied = [item.finding_key for item in decision.findings]
    if len(supplied) != len(set(supplied)):
        raise ValueError("Duplicate finding decision")
    if set(supplied) != set(finding_keys(report)):
        raise ValueError("Decisions must cover exactly the current findings")
