"""Read supported native fields without mutating payloads or guessing decoders."""

from datetime import datetime, timezone
from ipaddress import ip_address
from typing import Any

from app.schemas.case import IncidentCase
from app.schemas.investigation import Attribute, EventEvidence, FieldEvidence

# Separate kinds avoid matching a username with a user ID or an agent-local ID
# with a globally scoped host ID. Families prevent counting two IPs as two signals.
FIELDS = {
    "ip": (
        "network",
        (
            "source.ip",
            "destination.ip",
            "source_ip",
            "dest_ip",
            "data.srcip",
            "data.dstip",
            "host.ip",
            "agent.ip",
        ),
    ),
    "user_name": ("user", ("user.name", "data.srcuser", "data.dstuser", "user")),
    "user_id": ("user", ("user.id",)),
    "host_name": ("host", ("host.name", "host.hostname", "agent.name", "host")),
    "host_id": ("host", ("host.id",)),
    "wazuh_agent_id": ("host", ("agent.id",)),
    "process_id": ("process", ("process.entity_id",)),
    "session_id": ("session", ("session.id",)),
    "sha256": ("artifact", ("file.hash.sha256", "process.hash.sha256")),
    "sha1": ("artifact", ("file.hash.sha1", "process.hash.sha1")),
    "md5": ("artifact", ("file.hash.md5", "process.hash.md5")),
    "domain": (
        "observable",
        ("dns.question.name", "url.domain", "source.domain", "destination.domain"),
    ),
    "url": ("observable", ("url.full", "url.original")),
    "email": ("observable", ("email.from.address", "email.to.address")),
}


def escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def read_field(raw: dict, path: str, prefix: str) -> list[tuple[str, Any]]:
    """Return flat and nested representations, including _source, with pointers."""
    found = []
    if path in raw:
        found.append((prefix + "/" + escape(path), raw[path]))
    if "." in path:
        value, pointer = raw, prefix
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                break
            value, pointer = value[part], pointer + "/" + escape(part)
        else:
            found.append((pointer, value))
    if isinstance(raw.get("_source"), dict):
        # Only the standard single export envelope is unwrapped.
        source = {k: v for k, v in raw["_source"].items() if k != "_source"}
        found.extend(read_field(source, path, prefix + "/_source"))
    return found


def comparison_value(kind: str, value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    if kind == "ip":
        try:
            return str(ip_address(value))
        except ValueError:
            return None
    if kind in {"sha256", "sha1", "md5"}:
        size = {"sha256": 64, "sha1": 40, "md5": 32}[kind]
        if len(value) != size or any(c not in "0123456789abcdefABCDEF" for c in value):
            return None
        return value.lower()
    if kind == "domain":
        return value.lower().removesuffix(".")
    return value


def extract_events(case: IncidentCase) -> list[EventEvidence]:
    events = []
    for index, alert in enumerate(case.alerts):
        prefix = f"/alerts/{index}/raw_alert"
        attrs, warnings = [], []
        for kind, (family, paths) in FIELDS.items():
            for path in paths:
                for pointer, value in read_field(alert.raw_alert, path, prefix):
                    values = [(pointer, value)]
                    if isinstance(value, list):
                        values = [(f"{pointer}/{i}", x) for i, x in enumerate(value)]
                    for ptr, item in values:
                        normalized = comparison_value(kind, item)
                        if normalized is not None:
                            attrs.append(
                                Attribute(
                                    kind=kind,
                                    family=family,
                                    value=normalized,
                                    evidence=FieldEvidence(
                                        alert_id=alert.alert_id, path=ptr, value=item
                                    ),
                                )
                            )
        timestamps = []
        for path in ("@timestamp", "timestamp"):
            timestamps.extend(read_field(alert.raw_alert, path, prefix))
        utc_values = set()
        timestamp_evidence = None
        for pointer, value in timestamps:
            if timestamp_evidence is None:
                timestamp_evidence = FieldEvidence(
                    alert_id=alert.alert_id,
                    path=pointer,
                    value=value,
                )
            try:
                if not isinstance(value, str):
                    raise ValueError("not a string")
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError("timezone missing")
                utc_values.add(parsed.astimezone(timezone.utc).isoformat())
            except (ValueError, OverflowError):
                warnings.append(f"Unusable event timestamp at {pointer}")
        timestamp = None
        if len(utc_values) == 1 and not warnings:
            timestamp = next(iter(utc_values))
        elif len(utc_values) > 1:
            warnings.append("Conflicting event timestamps; temporal proximity unknown")
        elif not timestamps:
            warnings.append("Event timestamp absent; submitted_at is not substituted")
        events.append(
            EventEvidence(
                alert_id=alert.alert_id,
                source_system=alert.source_system,
                attributes=attrs,
                timestamp_utc=timestamp,
                timestamp_evidence=timestamp_evidence,
                warnings=warnings,
            )
        )
    return events
