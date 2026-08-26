from datetime import UTC, datetime
from uuid import uuid4

import pytest
from skylink.database import CommandConflictError, Database
from skylink.models import CommandRequest


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


@pytest.mark.asyncio
async def test_command_id_conflict(tmp_path) -> None:
    database = Database(tmp_path / "test.db")
    await database.connect()
    command_id = uuid4()
    await database.create_command(CommandRequest(id=command_id, type="arm"), None)

    with pytest.raises(CommandConflictError):
        await database.create_command(CommandRequest(id=command_id, type="land"), None)
