"""Local SQLite persistence for the specification's durable uniqueness rule."""

import json
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from app.schemas.case import CaseStatus, IncidentCase
from app.schemas.errors import CaseValidationError, ValidationIssue


@dataclass(frozen=True)
class AcceptedCase:
    case_id: UUID
    submitted_case: IncidentCase


@dataclass(frozen=True)
class StoredCase:
    case_id: UUID
    submitted_case_id: str
    status: CaseStatus
    created_at: datetime
    investigation: dict | None


class CaseStore:
    """Store accepted evidence and enforce submitted-ID uniqueness atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def initialize(self) -> None:
        """Run during application startup; importing the app creates no database."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS analysis_jobs ("
                "case_id TEXT PRIMARY KEY, status TEXT NOT NULL, "
                "error TEXT, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS chat_messages ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, "
                "message TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS chat_messages_case_id "
                "ON chat_messages (case_id, id)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS cases ("
                "submitted_case_id TEXT PRIMARY KEY, "
                "case_id TEXT NOT NULL UNIQUE, "
                "payload TEXT NOT NULL, "
                "status TEXT NOT NULL DEFAULT 'open', "
                "created_at TEXT NOT NULL)"
            )
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(cases)").fetchall()
            }
            if "status" not in columns:
                connection.execute(
                    "ALTER TABLE cases ADD COLUMN status TEXT NOT NULL DEFAULT 'open'"
                )
            if "created_at" not in columns:
                connection.execute("ALTER TABLE cases ADD COLUMN created_at TEXT")
                connection.execute(
                    "UPDATE cases SET created_at = ? WHERE created_at IS NULL",
                    (datetime.now(timezone.utc).isoformat(),),
                )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS investigations ("
                "case_id TEXT PRIMARY KEY, result TEXT NOT NULL)"
            )

    def create(
        self, case: IncidentCase, id_factory: Callable[[], UUID]
    ) -> AcceptedCase:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            # Serialize creators before checking uniqueness and allocating an ID.
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT 1 FROM cases WHERE submitted_case_id = ?", (case.case_id,)
            ).fetchone()
            if existing:
                raise CaseValidationError(
                    [
                        ValidationIssue(
                            rule="VR-04",
                            loc=["body", "case_id"],
                            msg="This submitted case_id has already been accepted",
                            type="case_id_conflict",
                        )
                    ],
                    status_code=409,
                )
            record = AcceptedCase(id_factory(), case.model_copy(deep=True))
            connection.execute(
                "INSERT INTO cases "
                "(submitted_case_id, case_id, payload, status, created_at) "
                "VALUES (?, ?, ?, 'open', ?)",
                (
                    case.case_id,
                    str(record.case_id),
                    case.model_dump_json(exclude_unset=True),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            connection.execute(
                "INSERT INTO analysis_jobs (case_id, status) VALUES (?, 'queued')",
                (str(record.case_id),),
            )
        return record

    def list_cases(self) -> list[StoredCase]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT c.case_id, c.submitted_case_id, c.status, c.created_at, "
                "i.result FROM cases AS c "
                "LEFT JOIN investigations AS i ON i.case_id = c.case_id "
                "ORDER BY c.created_at DESC, c.case_id DESC"
            ).fetchall()
        return [
            StoredCase(
                case_id=UUID(row[0]),
                submitted_case_id=row[1],
                status=row[2],
                created_at=datetime.fromisoformat(row[3]),
                investigation=json.loads(row[4]) if row[4] else None,
            )
            for row in rows
        ]

    def update_status(self, case_id: UUID, status: CaseStatus) -> bool:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            result = connection.execute(
                "UPDATE cases SET status = ? WHERE case_id = ?",
                (status, str(case_id)),
            )
        return result.rowcount == 1

    def get(self, submitted_case_id: str) -> AcceptedCase | None:
        """Look up the submitted identifier for existing internal callers."""
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT case_id, payload FROM cases WHERE submitted_case_id = ?",
                (submitted_case_id,),
            ).fetchone()
        if row is None:
            return None
        return AcceptedCase(UUID(row[0]), IncidentCase.model_validate_json(row[1]))

    def get_by_id(self, case_id: UUID) -> AcceptedCase | None:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT payload FROM cases WHERE case_id = ?", (str(case_id),)
            ).fetchone()
        return (
            AcceptedCase(case_id, IncidentCase.model_validate_json(row[0]))
            if row
            else None
        )

    def save_investigation(
        self, case_id: UUID, result: dict, *, complete_analysis: bool = False
    ) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "INSERT INTO investigations (case_id, result) VALUES (?, ?) "
                "ON CONFLICT(case_id) DO UPDATE SET result = excluded.result",
                (str(case_id), json.dumps(result, ensure_ascii=False, allow_nan=False)),
            )
            if complete_analysis:
                self._write_analysis_status(connection, case_id, "completed", None)

    def save_instruction_revision(
        self, case_id: UUID, expected_revision: int, result: dict
    ) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT result FROM investigations WHERE case_id = ?", (str(case_id),)
            ).fetchone()
            current = json.loads(row[0]) if row else None
            actual_revision = int(current.get("revision", 1)) if current else None
            if current is None:
                raise LookupError("No completed investigation found")
            if actual_revision != expected_revision:
                raise LookupError("The investigation revision has changed; reload")
            connection.execute(
                "UPDATE investigations SET result = ? WHERE case_id = ?",
                (
                    json.dumps(result, ensure_ascii=False, allow_nan=False),
                    str(case_id),
                ),
            )

    def get_investigation(self, case_id: UUID) -> dict | None:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT result FROM investigations WHERE case_id = ?", (str(case_id),)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_review(self, case_id: UUID, run_id: str, result: dict) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT result FROM investigations WHERE case_id = ?", (str(case_id),)
            ).fetchone()
            current = json.loads(row[0]) if row else None
            if current is None or current["run_id"] != run_id:
                raise LookupError("The investigation run has changed; reload")
            if current["report"]["review"]["status"] != "pending":
                raise LookupError("The investigation is not awaiting review")
            connection.execute(
                "UPDATE investigations SET result = ? WHERE case_id = ?",
                (json.dumps(result, ensure_ascii=False, allow_nan=False), str(case_id)),
            )

    def analysis_status(self, case_id: UUID) -> dict | None:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT status, error, updated_at FROM analysis_jobs WHERE case_id = ?",
                (str(case_id),),
            ).fetchone()
        return dict(zip(("status", "error", "updated_at"), row)) if row else None

    @staticmethod
    def _write_analysis_status(
        connection: sqlite3.Connection, case_id: UUID, status: str, error: str | None
    ) -> None:
        connection.execute(
            "INSERT INTO analysis_jobs (case_id, status, error) VALUES (?, ?, ?) "
            "ON CONFLICT(case_id) DO UPDATE SET status=excluded.status, "
            "error=excluded.error, updated_at=CURRENT_TIMESTAMP",
            (str(case_id), status, error),
        )

    def set_analysis_status(
        self, case_id: UUID, status: str, error: str | None = None
    ) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            self._write_analysis_status(connection, case_id, status, error)

    def recover_jobs(self) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "UPDATE analysis_jobs SET status='queued', error=NULL "
                "WHERE status='running'"
            )

    def next_job(self) -> UUID | None:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT case_id FROM analysis_jobs WHERE status='queued' "
                "ORDER BY updated_at, rowid LIMIT 1"
            ).fetchone()
        return UUID(row[0]) if row else None

    def messages(self, case_id: UUID) -> list[dict]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT message FROM chat_messages WHERE case_id=? ORDER BY id",
                (str(case_id),),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def append_exchange(self, case_id: UUID, user: dict, assistant: dict) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executemany(
                "INSERT INTO chat_messages (case_id, message) VALUES (?, ?)",
                [
                    (str(case_id), json.dumps(item, ensure_ascii=False))
                    for item in (user, assistant)
                ],
            )
