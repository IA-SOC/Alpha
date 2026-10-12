"""Small startup configuration; no external services are required."""

import os
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    max_alerts_per_case: int = 50
    case_database_path: Path = Path("data/cases.sqlite3")
    elastic_alert_id_pointer: str = "/event/id"
    wazuh_alert_id_pointer: str = "/id"
    elastic_versions: tuple[tuple[int, int], ...] = ((8, 19), (9, 4))
    wazuh_versions: tuple[tuple[int, int], ...] = ((4, 14),)
    ecs_majors: tuple[int, ...] = (8,)

    def __post_init__(self) -> None:
        if self.max_alerts_per_case < 1:
            raise ValueError("MAX_ALERTS_PER_CASE must be a positive integer")
        for pointer in (
            self.elastic_alert_id_pointer,
            self.wazuh_alert_id_pointer,
        ):
            if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
                raise ValueError("Native ID paths must be valid JSON Pointers")

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            max_alerts_per_case=int(os.getenv("MAX_ALERTS_PER_CASE", "50")),
            case_database_path=Path(
                os.getenv("CASE_DATABASE_PATH", "data/cases.sqlite3")
            ),
            elastic_alert_id_pointer=os.getenv("ELASTIC_ALERT_ID_POINTER", "/event/id"),
            wazuh_alert_id_pointer=os.getenv("WAZUH_ALERT_ID_POINTER", "/id"),
        )


# Read once before models/OpenAPI are built. Restart to change the input profile.
settings = Settings.from_environment()
