from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from skylink.config import Settings, settings
from skylink.database import CommandConflictError
from skylink.models import CommandRequest, LinkProfile, Mission, MissionCreate, ReplayControl
from skylink.service import MissionService


def create_app(config: Settings | None = None, service: MissionService | None = None) -> FastAPI:
    config = config or settings
    mission_service = service or MissionService(config)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await mission_service.start()
        try:
            yield
        finally:
            await mission_service.stop()

    app = FastAPI(title="SkyLink Mission Service", version="0.1.0", lifespan=lifespan)
    app.state.service = mission_service
    app.state.link_profile = LinkProfile()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        return {"status": "ok", "mode": config.mode, "simulationOnly": True, "schemaVersion": 1}

    @app.websocket("/ws/telemetry")
    async def telemetry_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            if mission_service.latest:
                await websocket.send_json(mission_service.latest.model_dump(mode="json"))
            async for snapshot in mission_service.telemetry_bus.subscribe():
                await websocket.send_json(snapshot.model_dump(mode="json"))
        except WebSocketDisconnect:
            return

    @app.websocket("/ws/events")
    async def event_socket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            async for event in mission_service.event_bus.subscribe():
                await websocket.send_json(event.model_dump(mode="json"))
        except WebSocketDisconnect:
            return

    @app.post("/api/commands", status_code=status.HTTP_202_ACCEPTED)
    async def issue_command(request: CommandRequest):
        try:
            record, created = await mission_service.issue_command(request)
        except CommandConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=423, detail=str(exc)) from exc
        return {"created": created, "command": record}

    @app.get("/api/commands/{command_id}")
    async def get_command(command_id: UUID):
        record = await mission_service.database.get_command(command_id)
        if record is None:
            raise HTTPException(status_code=404, detail="command not found")
        return record

    @app.post("/api/missions", status_code=status.HTTP_201_CREATED)
    async def create_mission(request: MissionCreate) -> Mission:
        mission = Mission(**request.model_dump())
        await mission_service.save_mission(mission)
        return mission

    @app.get("/api/missions/{mission_id}")
    async def get_mission(mission_id: UUID) -> Mission:
        mission = await mission_service.database.get_mission(mission_id)
        if mission is None:
            raise HTTPException(status_code=404, detail="mission not found")
        return mission

    @app.post("/api/missions/{mission_id}/upload")
    async def upload_mission(mission_id: UUID) -> dict[str, str]:
        try:
            return {"acknowledgement": await mission_service.upload_mission(mission_id)}
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="mission not found") from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=423, detail=str(exc)) from exc

    @app.get("/api/flights")
    async def list_flights():
        return await mission_service.database.list_flights()

    @app.get("/api/flights/{flight_id}")
    async def get_flight(flight_id: UUID):
        frames = await mission_service.database.telemetry_for_flight(flight_id)
        if not frames:
            raise HTTPException(status_code=404, detail="flight not found")
        return {"id": flight_id, "telemetry": frames}

    @app.post("/api/flights/{flight_id}/replay")
    async def start_replay(flight_id: UUID):
        try:
            await mission_service.replay.start(flight_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"status": "playing", "flightId": flight_id}

    @app.put("/api/replay")
    async def control_replay(control: ReplayControl):
        await mission_service.replay.control(control)
        return {
            "active": mission_service.replay.active,
            "paused": mission_service.replay.paused,
            "speed": mission_service.replay.speed,
        }

    @app.get("/api/link-profile")
    async def get_link_profile():
        return {
            "profile": app.state.link_profile,
            "stats": mission_service.link_proxy.stats()
            if mission_service.link_proxy
            else {
                "vehicle_to_app": {
                    "received": 0,
                    "forwarded": 0,
                    "dropped": 0,
                    "delayed": 0,
                    "duplicated": 0,
                },
                "app_to_vehicle": {
                    "received": 0,
                    "forwarded": 0,
                    "dropped": 0,
                    "delayed": 0,
                    "duplicated": 0,
                },
            },
        }

    @app.put("/api/link-profile")
    async def set_link_profile(profile: LinkProfile) -> LinkProfile:
        app.state.link_profile = profile
        if mission_service.link_proxy:
            mission_service.link_proxy.set_profile(profile)
        await mission_service.emit(f"Link profile changed to {profile.name}", "info", "link")
        return profile

    return app
