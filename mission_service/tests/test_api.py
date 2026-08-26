import time
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from skylink.api import create_app
from skylink.config import Settings
from skylink.service import MissionService
from skylink.vehicle import DemoVehicle


def make_client(database_path: Path) -> tuple[TestClient, DemoVehicle]:
    config = Settings(database_path=database_path, telemetry_hz=20)
    vehicle = DemoVehicle(telemetry_hz=20)
    return TestClient(create_app(config, MissionService(config, vehicle))), vehicle


def test_health_and_telemetry(tmp_path) -> None:
    client, _ = make_client(tmp_path / "test.db")
    with client:
        assert client.get("/api/health").json()["simulationOnly"] is True
        with client.websocket_connect("/ws/telemetry") as socket:
            frame = socket.receive_json()
            assert frame["schemaVersion"] == 1
            assert frame["source"] == "demo"


def test_duplicate_command_executes_once(tmp_path) -> None:
    client, vehicle = make_client(tmp_path / "test.db")
    command_id = uuid4()
    payload = {"id": str(command_id), "type": "arm", "parameters": {}}
    with client:
        assert client.post("/api/commands", json=payload).json()["created"] is True
        assert client.post("/api/commands", json=payload).json()["created"] is False
        deadline = time.time() + 2
        while time.time() < deadline:
            command = client.get(f"/api/commands/{command_id}").json()
            if command["state"] == "acknowledged":
                break
            time.sleep(0.02)
        assert command["state"] == "acknowledged"
        assert vehicle.command_executions[str(command_id)] == 1


def test_command_id_conflict_returns_409(tmp_path) -> None:
    client, _ = make_client(tmp_path / "test.db")
    command_id = uuid4()
    with client:
        client.post("/api/commands", json={"id": str(command_id), "type": "arm"})
        response = client.post("/api/commands", json={"id": str(command_id), "type": "land"})
        assert response.status_code == 409
