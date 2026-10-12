"""Semantic intake checks followed by UUID allocation and acceptance."""

from collections.abc import Callable
from uuid import UUID

from pydantic import JsonValue

from app.core.config import Settings
from app.core.ids import generate_case_id
from app.schemas.case import IncidentCase
from app.schemas.errors import CaseValidationError, ValidationIssue
from app.storage.case_store import AcceptedCase, CaseStore


def native_identifier(raw_alert: dict[str, JsonValue], pointer: str) -> JsonValue:
    """Read an explicitly configured JSON Pointer; never infer an ID field."""
    value: JsonValue = raw_alert
    for segment in pointer[1:].split("/"):
        key = segment.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if key not in value:
                return None
            value = value[key]
        elif isinstance(value, list) and key.isascii() and key.isdecimal():
            if (len(key) > 1 and key.startswith("0")) or int(key) >= len(value):
                return None
            value = value[int(key)]
        else:
            return None
    return value


class CaseService:
    def __init__(
        self,
        settings: Settings,
        store: CaseStore,
        id_factory: Callable[[], UUID] = generate_case_id,
    ) -> None:
        self.settings = settings
        self.store = store
        self.id_factory = id_factory

    def accept(self, case: IncidentCase) -> AcceptedCase:
        """All semantic checks complete before any generated case ID is allocated."""
        issues: list[ValidationIssue] = []
        seen: set[str] = set()

        def issue(rule: str, loc: list[str | int], msg: str) -> None:
            issues.append(
                ValidationIssue(
                    rule=rule, loc=["body", *loc], msg=msg, type="case_validation"
                )
            )

        for index, alert in enumerate(case.alerts):
            path: list[str | int] = ["alerts", index]
            if alert.alert_id in seen:
                issue("VR-11", [*path, "alert_id"], "Duplicate alert_id within case")
            seen.add(alert.alert_id)

            is_elastic = alert.source_system == "elastic"
            pointer = (
                self.settings.elastic_alert_id_pointer
                if is_elastic
                else self.settings.wazuh_alert_id_pointer
            )
            original_id = native_identifier(alert.raw_alert, pointer)
            if not isinstance(original_id, str) or original_id != alert.alert_id:
                issue(
                    "VR-10",
                    [*path, "alert_id"],
                    "alert_id must match the original string identifier at "
                    f"raw_alert JSON Pointer {pointer}; check the source profile",
                )

            if alert.source_version is not None:
                branch = tuple(
                    part.lstrip("0") or "0"
                    for part in alert.source_version.split(".")[:2]
                )
                supported = (
                    self.settings.elastic_versions
                    if is_elastic
                    else self.settings.wazuh_versions
                )
                if branch not in {tuple(map(str, version)) for version in supported}:
                    issue(
                        "VR-19",
                        [*path, "source_version"],
                        "Source version is not supported for this source_system",
                    )
            if alert.ecs_version is not None:
                major = alert.ecs_version.split(".")[0].lstrip("0") or "0"
                if major not in {str(version) for version in self.settings.ecs_majors}:
                    issue(
                        "VR-20",
                        [*path, "ecs_version"],
                        "ECS major version is not supported (initially 8 only)",
                    )

        for index, enrichment in enumerate(case.enrichments or []):
            for ref_index, reference in enumerate(enrichment.related_alert_ids or []):
                if reference not in seen:
                    issue(
                        "VR-23",
                        ["enrichments", index, "related_alert_ids", ref_index],
                        "Referenced alert_id does not exist in this case",
                    )

        if issues:
            raise CaseValidationError(issues)
        return self.store.create(case, self.id_factory)
