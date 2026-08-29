import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import aiosqlite

from skylink.models import (
    CommandRecord,
    CommandRequest,
    CommandState,
    GroundEvent,
    Mission,
    TelemetrySnapshot,
    utc_now,
)


class CommandConflictError(Exception):
    pass


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS flights (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    source TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    outcome TEXT NOT NULL DEFAULT 'active'
                );
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flight_id TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(flight_id) REFERENCES flights(id)
                );
                CREATE INDEX IF NOT EXISTS telemetry_flight_time
                ON telemetry(flight_id, captured_at);
                CREATE TABLE IF NOT EXISTS commands (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    request_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    state TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    acknowledgement TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    flight_id TEXT
                );
                CREATE TABLE IF NOT EXISTS missions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    flight_id TEXT,
                    captured_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                );
                """
            )
            await db.commit()

    async def start_flight(self, flight_id: UUID, name: str, source: str) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO flights(id, name, source, started_at) VALUES (?, ?, ?, ?)",
                (str(flight_id), name, source, utc_now().isoformat()),
            )
            await db.commit()

    async def end_flight(self, flight_id: UUID, outcome: str = "completed") -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE flights SET ended_at = ?, outcome = ? WHERE id = ?",
                (utc_now().isoformat(), outcome, str(flight_id)),
            )
            await db.commit()

    async def log_telemetry(self, flight_id: UUID, snapshot: TelemetrySnapshot) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO telemetry(flight_id, captured_at, payload) VALUES (?, ?, ?)",
                (str(flight_id), snapshot.timestamp.isoformat(), snapshot.model_dump_json()),
            )
            await db.commit()

    async def log_event(self, flight_id: UUID | None, event: GroundEvent) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO events(id, flight_id, captured_at, payload) VALUES (?, ?, ?, ?)",
                (
                    str(event.id),
                    str(flight_id) if flight_id else None,
                    event.timestamp.isoformat(),
                    event.model_dump_json(),
                ),
            )
            await db.commit()

    async def telemetry_for_flight(self, flight_id: UUID) -> list[TelemetrySnapshot]:
        async with aiosqlite.connect(self.path) as db:
            rows = await db.execute_fetchall(
                "SELECT payload FROM telemetry WHERE flight_id = ? ORDER BY captured_at",
                (str(flight_id),),
            )
        return [TelemetrySnapshot.model_validate_json(row[0]) for row in rows]

    async def list_flights(self) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            rows = await db.execute_fetchall(
                """SELECT f.*, COUNT(DISTINCT t.id) telemetry_count,
                COUNT(DISTINCT c.id) command_count FROM flights f
                LEFT JOIN telemetry t ON t.flight_id = f.id
                LEFT JOIN commands c ON c.flight_id = f.id
                GROUP BY f.id ORDER BY f.started_at DESC"""
            )
        return [dict(row) for row in rows]

    async def create_command(
        self, request: CommandRequest, flight_id: UUID | None
    ) -> tuple[CommandRecord, bool]:
        payload = request.model_dump_json()
        request_hash = _canonical_request(request)
        existing = await self.get_command(request.id)
        if existing:
            if _canonical_request(existing) != request_hash:
                raise CommandConflictError("command ID already exists with a different payload")
            return existing, False

        record = CommandRecord(**request.model_dump())
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """INSERT INTO commands(id, type, request_hash, payload, state, attempts,
                acknowledgement, error, created_at, updated_at, flight_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(record.id),
                    record.type,
                    request_hash,
                    payload,
                    record.state,
                    0,
                    None,
                    None,
                    record.createdAt.isoformat(),
                    record.updatedAt.isoformat(),
                    str(flight_id) if flight_id else None,
                ),
            )
            await db.commit()
        return record, True

    async def update_command(
        self,
        command_id: UUID,
        state: CommandState,
        attempts: int,
        acknowledgement: str | None = None,
        error: str | None = None,
    ) -> CommandRecord:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """UPDATE commands SET state = ?, attempts = ?, acknowledgement = ?, error = ?,
                updated_at = ? WHERE id = ?""",
                (state, attempts, acknowledgement, error, utc_now().isoformat(), str(command_id)),
            )
            await db.commit()
        record = await self.get_command(command_id)
        if record is None:
            raise KeyError(command_id)
        return record

    async def get_command(self, command_id: UUID) -> CommandRecord | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM commands WHERE id = ?", (str(command_id),))
            row = await cursor.fetchone()
        if row is None:
            return None
        request = CommandRequest.model_validate_json(row["payload"])
        return CommandRecord(
            **request.model_dump(),
            state=row["state"],
            attempts=row["attempts"],
            acknowledgement=row["acknowledgement"],
            error=row["error"],
            updatedAt=datetime.fromisoformat(row["updated_at"]),
        )

    async def save_mission(self, mission: Mission) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT INTO missions(id, name, payload, created_at) VALUES (?, ?, ?, ?)",
                (
                    str(mission.id),
                    mission.name,
                    mission.model_dump_json(),
                    mission.createdAt.isoformat(),
                ),
            )
            await db.commit()

    async def get_mission(self, mission_id: UUID) -> Mission | None:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT payload FROM missions WHERE id = ?", (str(mission_id),)
            )
            row = await cursor.fetchone()
        return Mission.model_validate_json(row[0]) if row else None


def _canonical_request(request: CommandRequest | CommandRecord) -> str:
    return json.dumps(
        {"id": str(request.id), "type": request.type, "parameters": request.parameters},
        sort_keys=True,
        separators=(",", ":"),
    )
