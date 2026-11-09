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


@dataclass(frozen=True)
class StoredMessage:
    message_id: int
    case_id: UUID
    revision: int
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class StoredRevision:
    case_id: UUID
    revision: int
    run_id: str
    result: dict
    created_at: datetime


class CaseStore:
    """Store accepted evidence and enforce submitted-ID uniqueness atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _run_id_for_revision(result: dict) -> str:
        run_id = result.get("run_id")
        return run_id if isinstance(run_id, str) and run_id else "unknown"

    def initialize(self) -> None:
        """Run during application startup; importing the app creates no database."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as connection, connection:
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
            connection.execute(
                "CREATE TABLE IF NOT EXISTS investigation_revisions ("
                "case_id TEXT NOT NULL, "
                "revision INTEGER NOT NULL, "
                "run_id TEXT NOT NULL, "
                "result TEXT NOT NULL, "
                "created_at TEXT NOT NULL, "
                "PRIMARY KEY (case_id, revision), "
                "FOREIGN KEY (case_id) REFERENCES cases(case_id))"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS chat_messages ("
                "message_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "case_id TEXT NOT NULL, "
                "revision INTEGER NOT NULL, "
                "role TEXT NOT NULL, "
                "content TEXT NOT NULL, "
                "created_at TEXT NOT NULL, "
                "FOREIGN KEY (case_id) REFERENCES cases(case_id))"
            )
            legacy = connection.execute(
                "SELECT case_id, result FROM investigations"
            ).fetchall()
            for case_id, raw_result in legacy:
                result = json.loads(raw_result)
                connection.execute(
                    "INSERT OR IGNORE INTO investigation_revisions "
                    "(case_id, revision, run_id, result, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        case_id,
                        int(result.get("revision", 1)),
                        self._run_id_for_revision(result),
                        raw_result,
                        datetime.now(timezone.utc).isoformat(),
                    ),
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

    def save_investigation(self, case_id: UUID, result: dict) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            serialized = json.dumps(
                result, ensure_ascii=False, allow_nan=False
            )
            created_at = datetime.now(timezone.utc).isoformat()
            connection.execute(
                "INSERT INTO investigations (case_id, result) VALUES (?, ?) "
                "ON CONFLICT(case_id) DO UPDATE SET result = excluded.result",
                (str(case_id), serialized),
            )
            connection.execute(
                "INSERT INTO investigation_revisions "
                "(case_id, revision, run_id, result, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(case_id, revision) DO UPDATE SET "
                "run_id = excluded.run_id, result = excluded.result",
                (
                    str(case_id),
                    int(result.get("revision", 1)),
                    self._run_id_for_revision(result),
                    serialized,
                    created_at,
                ),
            )

    def save_instruction_revision(
        self,
        case_id: UUID,
        expected_revision: int,
        result: dict,
        chat_turn: tuple[str, str] | None = None,
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
            serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
            connection.execute(
                "INSERT INTO investigation_revisions "
                "(case_id, revision, run_id, result, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(case_id, revision) DO UPDATE SET "
                "run_id = excluded.run_id, result = excluded.result",
                (
                    str(case_id),
                    int(result["revision"]),
                    result["run_id"],
                    serialized,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            if chat_turn is not None:
                created_at = datetime.now(timezone.utc).isoformat()
                connection.executemany(
                    "INSERT INTO chat_messages "
                    "(case_id, revision, role, content, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        (
                            str(case_id),
                            int(result["revision"]),
                            "user",
                            chat_turn[0],
                            created_at,
                        ),
                        (
                            str(case_id),
                            int(result["revision"]),
                            "assistant",
                            chat_turn[1],
                            created_at,
                        ),
                    ],
                )

    def get_investigation(self, case_id: UUID) -> dict | None:
        with closing(sqlite3.connect(self.path)) as connection:
            row = connection.execute(
                "SELECT result FROM investigations WHERE case_id = ?", (str(case_id),)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save_chat_turn(
        self,
        case_id: UUID,
        revision: int,
        instruction: str,
        response: str,
    ) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executemany(
                "INSERT INTO chat_messages "
                "(case_id, revision, role, content, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (str(case_id), revision, "user", instruction, created_at),
                    (str(case_id), revision, "assistant", response, created_at),
                ],
            )

    def get_messages(self, case_id: UUID) -> list[StoredMessage]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT message_id, case_id, revision, role, content, created_at "
                "FROM chat_messages WHERE case_id = ? ORDER BY message_id",
                (str(case_id),),
            ).fetchall()
        return [
            StoredMessage(
                message_id=row[0],
                case_id=UUID(row[1]),
                revision=row[2],
                role=row[3],
                content=row[4],
                created_at=datetime.fromisoformat(row[5]),
            )
            for row in rows
        ]

    def get_revisions(self, case_id: UUID) -> list[StoredRevision]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute(
                "SELECT case_id, revision, run_id, result, created_at "
                "FROM investigation_revisions WHERE case_id = ? ORDER BY revision",
                (str(case_id),),
            ).fetchall()
        return [
            StoredRevision(
                case_id=UUID(row[0]),
                revision=row[1],
                run_id=row[2],
                result=json.loads(row[3]),
                created_at=datetime.fromisoformat(row[4]),
            )
            for row in rows
        ]

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
            serialized = json.dumps(result, ensure_ascii=False, allow_nan=False)
            connection.execute(
                "INSERT INTO investigation_revisions "
                "(case_id, revision, run_id, result, created_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(case_id, revision) DO UPDATE SET "
                "run_id = excluded.run_id, result = excluded.result",
                (
                    str(case_id),
                    int(result.get("revision", 1)),
                    result["run_id"],
                    serialized,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
