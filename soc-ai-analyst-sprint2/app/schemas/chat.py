
from pydantic import BaseModel, ConfigDict, Field


class AnalystMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    analyst_id: str = Field(min_length=1, max_length=200, pattern=r"\S")
    message: str = Field(min_length=1, max_length=4000, pattern=r"\S")
    evidence_refs: list[str] = Field(default_factory=list, max_length=50)


class AssistantAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    answer: str = Field(min_length=1, max_length=6000, pattern=r"\S")
    evidence_refs: list[str] = Field(max_length=50)
