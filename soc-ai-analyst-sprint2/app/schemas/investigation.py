"""Internal/output models. These do not change the v1.0 intake contract."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class FieldEvidence(BaseModel):
    alert_id: str
    path: str  # JSON Pointer into the original submitted case
    value: JsonValue


class Attribute(BaseModel):
    kind: str
    family: str
    value: str  # comparison value; original value is retained in evidence
    evidence: FieldEvidence


class EventEvidence(BaseModel):
    alert_id: str
    source_system: str
    attributes: list[Attribute]
    timestamp_utc: str | None
    timestamp_evidence: FieldEvidence | None
    warnings: list[str]


class RelationshipEvidence(BaseModel):
    kind: str
    assessment: Literal["shared", "distinct", "temporal", "missing"]
    observation: str
    fields: list[FieldEvidence]


class AlertRelationship(BaseModel):
    relationship_id: str
    alert_ids: list[str]
    classification: Literal["related", "uncertain", "unrelated"]
    rule: str
    explanation: str
    time_delta_seconds: float | None
    evidence: list[RelationshipEvidence]


class AlertDisposition(BaseModel):
    alert_id: str
    classification: Literal["related", "uncertain", "unrelated"]
    relationship_ids: list[str]
    explanation: str


class CorrelationResult(BaseModel):
    algorithm: str = "entity-time-v1"
    window_seconds: int
    relationships: list[AlertRelationship]
    alerts: list[AlertDisposition]
    related_groups: list[list[str]]
    noise_alert_ids: list[str]
    limitations: list[str]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["validated", "corrected", "rejected"]
    analyst: str = Field(min_length=1, pattern=r"\S")
    notes: str = Field(min_length=1, pattern=r"\S")
