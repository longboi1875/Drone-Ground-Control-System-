import asyncio
import contextlib
from uuid import UUID, uuid4

from skylink.broadcast import Broadcast
from skylink.config import Settings
from skylink.database import CommandConflictError, Database
from skylink.link_proxy import LinkProxy
from skylink.models import (
    CommandRecord,
    CommandRequest,
    CommandState,
    GroundEvent,
    Mission,
    TelemetrySnapshot,
)
from skylink.replay import ReplayController
from skylink.vehicle import DemoVehicle, MavsdkVehicle, VehicleAdapter


class MissionService:
    def __init__(self, config: Settings, vehicle: VehicleAdapter | None = None) -> None:
        self.config = config
        self.database = Database(config.database_path)
        self.vehicle = vehicle or (
            DemoVehicle(config.telemetry_hz)
            if config.mode == "demo"
            else MavsdkVehicle(config.vehicle_host, config.vehicle_port)
        )
        self.telemetry_bus: Broadcast[TelemetrySnapshot] = Broadcast()
        self.event_bus: Broadcast[GroundEvent] = Broadcast()
        self.replay = ReplayController(self.database, self.telemetry_bus)
        self.link_proxy = (
            LinkProxy(config.px4_link_port, config.relay_port, config.vehicle_port)
            if config.mode == "px4"
            else None
        )
        self.flight_id: UUID | None = None
        self.latest: TelemetrySnapshot | None = None
        self._telemetry_task: asyncio.Task[None] | None = None
        self._dispatching: set[UUID] = set()

    async def start(self) -> None:
        await self.database.connect()
        if self.link_proxy:
            await self.link_proxy.start()
        self.flight_id = uuid4()
        await self.database.start_flight(
            self.flight_id,
            "Demo flight" if self.config.mode == "demo" else "PX4 flight",
            self.config.mode,
        )
        self._telemetry_task = asyncio.create_task(self._stream_telemetry())
        await self.emit("Vehicle service started", "success", "connection")

    async def stop(self) -> None:
        if self._telemetry_task:
            self._telemetry_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._telemetry_task
        await self.replay.stop()
        await self.vehicle.close()
        if self.link_proxy:
            self.link_proxy.close()
        if self.flight_id:
            await self.database.end_flight(self.flight_id)

    async def _stream_telemetry(self) -> None:
        backoff = 0.5
        while True:
            try:
                async for snapshot in self.vehicle.telemetry():
                    self.latest = snapshot
                    if self.flight_id and not self.replay.active:
                        await self.database.log_telemetry(self.flight_id, snapshot)
                    if not self.replay.active:
                        await self.telemetry_bus.publish(snapshot)
                    backoff = 0.5
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await self.emit(f"Telemetry disconnected: {exc}", "warning", "connection")
                await asyncio.sleep(backoff)
                backoff = min(8.0, backoff * 2)

    async def issue_command(self, request: CommandRequest) -> tuple[CommandRecord, bool]:
        if self.replay.active:
            raise RuntimeError("commands are disabled during replay")
        record, created = await self.database.create_command(request, self.flight_id)
        if created and request.id not in self._dispatching:
            self._dispatching.add(request.id)
            asyncio.create_task(self._dispatch(request))
        return record, created

    async def _dispatch(self, request: CommandRequest) -> None:
        try:
            await self.database.update_command(request.id, CommandState.SENT, 1)
            await self.emit(f"{request.type.value} #{str(request.id)[:8]} sent", "info", "command")
            try:
                acknowledgement = await asyncio.wait_for(self.vehicle.execute(request), timeout=8)
            except TimeoutError:
                await self.database.update_command(
                    request.id, CommandState.TIMED_OUT, 1, error="acknowledgement timeout"
                )
                await self.emit(f"{request.type.value} timed out", "warning", "command")
                return
            await self.database.update_command(
                request.id, CommandState.ACKNOWLEDGED, 1, acknowledgement=acknowledgement
            )
            await self.emit(f"{request.type.value} acknowledged", "success", "command")
        except Exception as exc:
            await self.database.update_command(request.id, CommandState.FAILED, 1, error=str(exc))
            await self.emit(f"{request.type.value} failed: {exc}", "error", "command")
        finally:
            self._dispatching.discard(request.id)

    async def emit(self, message: str, severity: str = "info", kind: str = "system") -> None:
        event = GroundEvent(message=message, severity=severity, kind=kind)  # type: ignore[arg-type]
        await self.event_bus.publish(event)

    async def save_mission(self, mission: Mission) -> None:
        await self.database.save_mission(mission)
        await self.emit(f"Mission saved · {len(mission.waypoints)} waypoints", "success", "mission")

    async def upload_mission(self, mission_id: UUID) -> str:
        if self.replay.active:
            raise RuntimeError("mission upload is disabled during replay")
        mission = await self.database.get_mission(mission_id)
        if mission is None:
            raise KeyError(mission_id)
        acknowledgement = await self.vehicle.upload_mission(mission)
        await self.emit(acknowledgement, "success", "mission")
        return acknowledgement


__all__ = ["CommandConflictError", "MissionService"]
