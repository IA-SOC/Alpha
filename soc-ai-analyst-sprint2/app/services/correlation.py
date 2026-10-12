"""Conservative pairwise correlation, independent of ATT&CK classification."""

from datetime import datetime
from itertools import combinations

from app.schemas.investigation import (
    AlertDisposition,
    AlertRelationship,
    CorrelationResult,
    EventEvidence,
    RelationshipEvidence,
)

CORRELATION_FAMILIES = {"network", "user", "host", "process", "session", "artifact"}


def correlate(
    events: list[EventEvidence], window_seconds: int = 300
) -> CorrelationResult:
    if window_seconds <= 0:
        raise ValueError("Correlation window must be positive")
    relationships = []
    for pair_index, (left, right) in enumerate(combinations(events, 2), 1):
        evidence, shared_families, comparable_families = [], set(), set()
        left_attrs = [a for a in left.attributes if a.family in CORRELATION_FAMILIES]
        right_attrs = [a for a in right.attributes if a.family in CORRELATION_FAMILIES]
        common_kinds = {a.kind for a in left_attrs} & {a.kind for a in right_attrs}
        for kind in sorted(common_kinds):
            la = [a for a in left_attrs if a.kind == kind]
            ra = [a for a in right_attrs if a.kind == kind]
            family = la[0].family
            comparable_families.add(family)
            shared = {a.value for a in la} & {a.value for a in ra}
            if shared:
                shared_families.add(family)
                fields = [a.evidence for a in la + ra if a.value in shared]
                observation = f"Shared {kind}: {', '.join(sorted(shared))}"
            else:
                fields = [a.evidence for a in la + ra]
                observation = f"No shared value among the available {kind} fields"
            evidence.append(
                RelationshipEvidence(
                    kind=kind,
                    assessment="shared" if shared else "distinct",
                    observation=observation,
                    fields=fields,
                )
            )
        delta = None
        if left.timestamp_utc and right.timestamp_utc:
            delta = abs(
                (
                    datetime.fromisoformat(left.timestamp_utc)
                    - datetime.fromisoformat(right.timestamp_utc)
                ).total_seconds()
            )
        time_fields = [
            e.timestamp_evidence
            for e in (left, right)
            if e.timestamp_evidence is not None
        ]
        evidence.append(
            RelationshipEvidence(
                kind="time",
                assessment="temporal" if delta is not None else "missing",
                observation=(
                    f"Events are {delta:g} seconds apart; window {window_seconds}s"
                    if delta is not None
                    else "Comparable timezone-aware event times are unavailable. "
                    + "; ".join(left.warnings + right.warnings)
                ),
                fields=time_fields,
            )
        )
        # Two independent entity families and reliable close event times are
        # required. IP alone (NAT, proxies), user alone, hashes and time alone
        # do not prove that the same activity is being observed.
        if len(shared_families) >= 2 and delta is not None and delta <= window_seconds:
            classification, rule = "related", "R1"
            explanation = "At least two entity families match within the time window"
        elif shared_families:
            classification, rule = "uncertain", "R2"
            explanation = (
                "Shared attributes exist, but independent corroboration or reliable "
                "temporal proximity is insufficient"
            )
        elif len(comparable_families) >= 2:
            classification, rule = "unrelated", "R3"
            explanation = (
                "No shared values across at least two comparable entity families; "
                "unrelated under this rule profile, not proof of benign activity"
            )
        else:
            classification, rule = "uncertain", "R4"
            explanation = (
                "Insufficient comparable entity evidence; absence is not disproof"
            )
            evidence.append(
                RelationshipEvidence(
                    kind="coverage",
                    assessment="missing",
                    fields=[],
                    observation="Fewer than two entity families are comparable",
                )
            )
        relationships.append(
            AlertRelationship(
                relationship_id=f"rel-{pair_index:04d}",
                alert_ids=[left.alert_id, right.alert_id],
                classification=classification,
                rule=rule,
                explanation=explanation,
                time_delta_seconds=delta,
                evidence=evidence,
            )
        )

    dispositions = []
    adjacency = {event.alert_id: set() for event in events}
    for rel in relationships:
        if rel.classification == "related":
            a, b = rel.alert_ids
            adjacency[a].add(b)
            adjacency[b].add(a)
    for event in events:
        linked = [r for r in relationships if event.alert_id in r.alert_ids]
        kinds = {r.classification for r in linked}
        if "related" in kinds:
            classification, reason = "related", "At least one related pair exists"
        elif not linked or "uncertain" in kinds:
            classification, reason = (
                "uncertain",
                "No related pair; evidence remains uncertain",
            )
        else:
            classification, reason = (
                "unrelated",
                "Every other alert is unrelated under this profile",
            )
        dispositions.append(
            AlertDisposition(
                alert_id=event.alert_id,
                classification=classification,
                relationship_ids=[r.relationship_id for r in linked],
                explanation=reason,
            )
        )
    groups, visited = [], set()
    for alert_id in adjacency:
        if alert_id in visited or not adjacency[alert_id]:
            continue
        stack, component = [alert_id], []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - visited, reverse=True))
        groups.append(sorted(component))
    return CorrelationResult(
        window_seconds=window_seconds,
        relationships=relationships,
        alerts=dispositions,
        related_groups=groups,
        noise_alert_ids=[
            a.alert_id for a in dispositions if a.classification == "unrelated"
        ],
        limitations=[
            "Related means shared observed entities, "
            "not a confirmed attack or causation.",
            "Noise is relative to this case and rule profile; "
            "alerts are never discarded.",
            "Groups are connected components, not proof that every pair is related.",
            "Unknown custom fields are retained but require "
            "verified mappings to correlate.",
            "Names are compared exactly; tenant/domain scoping "
            "requires customer validation.",
        ],
    )
