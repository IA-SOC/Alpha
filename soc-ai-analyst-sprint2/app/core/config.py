"""Small startup configuration; no external services are required."""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

ProcessField = Literal[
    "process.executable", "process.hash.sha256", "data.win.eventdata.image"
]


class BenignProcessRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    match: dict[ProcessField, str] = Field(min_length=1)

    @field_validator("match")
    @classmethod
    def validate_match(cls, fields: dict[ProcessField, str]) -> dict[ProcessField, str]:
        for field, value in fields.items():
            if not value.strip():
                raise ValueError("Process match values must not be blank")
            if field == "process.hash.sha256" and not re.fullmatch(
                r"[0-9a-fA-F]{64}", value
            ):
                raise ValueError("Process SHA-256 must contain 64 hexadecimal digits")
        return fields


@dataclass(frozen=True)
class Settings:
    max_alerts_per_case: int = 50
    case_database_path: Path = Path("data/cases.sqlite3")
    elastic_alert_id_pointer: str = "/event/id"
    wazuh_alert_id_pointer: str = "/id"
    elastic_versions: tuple[tuple[int, int], ...] = ((8, 19), (9, 4))
    wazuh_versions: tuple[tuple[int, int], ...] = ((4, 14),)
    ecs_majors: tuple[int, ...] = (8,)
    benign_process_rules: tuple[BenignProcessRule, ...] = ()

    def __post_init__(self) -> None:
        if self.max_alerts_per_case < 1:
            raise ValueError("MAX_ALERTS_PER_CASE must be a positive integer")
        rule_ids = {rule.id for rule in self.benign_process_rules}
        if len(rule_ids) != len(self.benign_process_rules):
            raise ValueError("BENIGN_PROCESS_RULES must use unique rule IDs")
        for pointer in (
            self.elastic_alert_id_pointer,
            self.wazuh_alert_id_pointer,
        ):
            if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
                raise ValueError("Native ID paths must be valid JSON Pointers")

    @classmethod
    def from_environment(cls) -> "Settings":
        process_rules = TypeAdapter(tuple[BenignProcessRule, ...]).validate_json(
            os.getenv("BENIGN_PROCESS_RULES", "[]")
        )
        return cls(
            max_alerts_per_case=int(os.getenv("MAX_ALERTS_PER_CASE", "50")),
            case_database_path=Path(
                os.getenv("CASE_DATABASE_PATH", "data/cases.sqlite3")
            ),
            elastic_alert_id_pointer=os.getenv("ELASTIC_ALERT_ID_POINTER", "/event/id"),
            wazuh_alert_id_pointer=os.getenv("WAZUH_ALERT_ID_POINTER", "/id"),
            benign_process_rules=process_rules,
        )


# Read once before models/OpenAPI are built. Restart to change the input profile.
settings = Settings.from_environment()
