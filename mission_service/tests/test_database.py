from datetime import UTC, datetime
from uuid import uuid4

import aiosqlite
import pytest
from skylink.database import CommandConflictError, Database
from skylink.models import CommandRequest, GroundEvent


@pytest.mark.asyncio
async def test_command_idempotency(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.connect()
    command_id = uuid4()
    request = CommandRequest(id=command_id, type="arm", createdAt=datetime.now(UTC))

    first, first_created = await database.create_command(request, None)
    second, second_created = await database.create_command(request, None)

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert second.createdAt == request.createdAt


@pytest.mark.asyncio
async def test_command_id_conflict(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.connect()
    command_id = uuid4()
    await database.create_command(CommandRequest(id=command_id, type="arm"), None)

    with pytest.raises(CommandConflictError):
        await database.create_command(CommandRequest(id=command_id, type="land"), None)


@pytest.mark.asyncio
async def test_events_are_recorded_with_the_flight(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.connect()
    flight_id = uuid4()
    await database.start_flight(flight_id, "Link test", "demo")
    event = GroundEvent(message="Vehicle link lost", severity="warning", kind="connection")

    await database.log_event(flight_id, event)

    async with aiosqlite.connect(database.path) as db:
        row = await (await db.execute("SELECT flight_id, payload FROM events")).fetchone()
    assert row is not None
    assert row[0] == str(flight_id)
    assert "Vehicle link lost" in row[1]
