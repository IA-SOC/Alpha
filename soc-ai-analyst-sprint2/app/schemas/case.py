"""Pydantic input models implementing the existing v1.0 structural contract."""

from typing import Annotated, Any, Literal

from pydantic import (
    UUID4,
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
)
from pydantic.json_schema import SkipJsonSchema
from rfc3339_validator import validate_rfc3339

from app.core.config import settings

NonBlankString = Annotated[str, Field(min_length=1, pattern=r"\S")]
SourceVersion = Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+(\.[0-9]+)?$")]
EcsVersion = Annotated[str, Field(pattern=r"^[0-9]+\.(x|[0-9]+(\.[0-9]+)?)$")]


def valid_timestamp(value: str) -> str:
    """Keep the original string, but require an RFC 3339 timezone/date-time."""
    if not validate_rfc3339(value.upper()):
        raise ValueError("VR-05: expected an RFC 3339 date-time with timezone")
    return value


def distinct_strings(values: list[str]) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError("Array entries must be distinct")
    return values


Timestamp = Annotated[
    str,
    Field(json_schema_extra={"format": "date-time"}),
    AfterValidator(valid_timestamp),
]
DistinctLabels = Annotated[
    list[NonBlankString],
    Field(min_length=1, json_schema_extra={"uniqueItems": True}),
    AfterValidator(distinct_strings),
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, value: Any) -> Any:
        # Optional means absent, not null. Nested raw JSON null values are valid.
        if value is None:
            raise ValueError("Omit an unavailable optional field; null is not allowed")
        return value


class Alert(ContractModel):
    alert_id: NonBlankString
    source_system: Literal["elastic", "wazuh"]
    raw_alert: Annotated[
        dict[str, JsonValue],
        Field(min_length=1, json_schema_extra={"additionalProperties": True}),
    ]
    source_version: SourceVersion | SkipJsonSchema[None] = None
    ecs_version: EcsVersion | SkipJsonSchema[None] = None


class Correlation(ContractModel):
    fields: DistinctLabels


class Observable(ContractModel):
    type: NonBlankString
    value: NonBlankString


class Enrichment(ContractModel):
    provider: NonBlankString
    observable: Observable
    related_alert_ids: DistinctLabels | SkipJsonSchema[None] = None
    raw_result: (
        Annotated[
            dict[str, JsonValue],
            Field(json_schema_extra={"additionalProperties": True}),
        ]
        | SkipJsonSchema[None]
    ) = None


class IncidentCase(ContractModel):
    schema_version: Literal["1.0"]
    case_id: NonBlankString
    submitted_at: Timestamp
    alerts: Annotated[
        list[Alert], Field(min_length=1, max_length=settings.max_alerts_per_case)
    ]
    title: str | SkipJsonSchema[None] = None
    description: str | SkipJsonSchema[None] = None
    correlation: Correlation | SkipJsonSchema[None] = None
    enrichments: list[Enrichment] | SkipJsonSchema[None] = None


class AcceptedCaseResponse(BaseModel):
    case_id: UUID4
    submitted_case_id: str
    status: Literal["accepted"] = "accepted"
