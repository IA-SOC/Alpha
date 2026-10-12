"""Associate supplied intelligence using declared links or typed field matches."""

from copy import deepcopy

from app.schemas.case import IncidentCase
from app.schemas.investigation import EventEvidence
from app.services.evidence import comparison_value

TYPE_KINDS = {
    "ip": {"ip"},
    "ipv4": {"ip"},
    "ipv6": {"ip"},
    "domain": {"domain"},
    "hostname": {"domain"},
    "url": {"url"},
    "sha256": {"sha256"},
    "sha1": {"sha1"},
    "md5": {"md5"},
    "hash": {"sha256", "sha1", "md5"},
    "email": {"email"},
}


def integrate_iocs(case: IncidentCase, events: list[EventEvidence]) -> list[dict]:
    items = []
    for index, supplied in enumerate(case.enrichments or []):
        original = supplied.model_dump(exclude_unset=True)
        kinds = TYPE_KINDS.get(supplied.observable.type.lower(), set())
        associations = []
        for event in events:
            matches = [
                attr.evidence.model_dump()
                for attr in event.attributes
                if attr.kind in kinds
                and comparison_value(attr.kind, supplied.observable.value) == attr.value
            ]
            declared = event.alert_id in (supplied.related_alert_ids or [])
            if matches or declared:
                methods = ["explicit_reference"] if declared else []
                if matches:
                    methods.append("observable_match")
                associations.append(
                    {
                        "alert_id": event.alert_id,
                        "methods": methods,
                        "fields": matches,
                        "reference_path": (
                            f"/enrichments/{index}/related_alert_ids/"
                            f"{supplied.related_alert_ids.index(event.alert_id)}"
                            if declared
                            else None
                        ),
                    }
                )
        # Do not flatten provider results or infer maliciousness from a score.
        # No provider field is required and no missing verdict is invented.
        item = {
            **deepcopy(original),
            "evidence_id": f"ioc-{index + 1:04d}",
            "source_path": f"/enrichments/{index}",
            "indicator": supplied.observable.value,
            "type": supplied.observable.type,
            "source": supplied.provider,
            "associations": associations,
            "associated_alert_ids": [a["alert_id"] for a in associations],
            "matched_alert_ids": [a["alert_id"] for a in associations if a["fields"]],
            "matched_fields": [
                {"alert_id": a["alert_id"], "field": f["path"]}
                for a in associations
                for f in a["fields"]
            ],
        }
        items.append(item)
    return items
