import asyncio
import contextlib
import math
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from skylink.models import (
    CommandRequest,
    CommandType,
    ConnectionState,
    GpsStatus,
    Mission,
    Position,
    TelemetrySnapshot,
)


class VehicleAdapter(ABC):
    @abstractmethod
    async def telemetry(self) -> AsyncIterator[TelemetrySnapshot]: ...

    @abstractmethod
    async def execute(self, command: CommandRequest) -> str: ...

    @abstractmethod
    async def upload_mission(self, mission: Mission) -> str: ...

    async def close(self) -> None:
        return None


class DemoVehicle(VehicleAdapter):
    def __init__(self, telemetry_hz: float = 5.0) -> None:
        self.telemetry_hz = telemetry_hz
        self.tick = 0
        self.armed = False
        self.altitude = 0.0
        self.mode = "HOLD"
        self.mission: Mission | None = None
        self.command_executions: dict[str, int] = {}

    async def telemetry(self) -> AsyncIterator[TelemetrySnapshot]:
        while True:
            angle = self.tick / 70
            if self.armed and self.mode not in {"LAND", "RTL"}:
                self.altitude = min(32, self.altitude + 0.35)
            elif self.mode == "LAND":
                self.altitude = max(0, self.altitude - 0.7)
                if self.altitude == 0:
                    self.armed = False
                    self.mode = "HOLD"
            yield TelemetrySnapshot(
                source="demo",
                connection=ConnectionState.HEALTHY,
                heartbeatAgeMs=40 + self.tick % 80,
                position=Position(
                    latitudeDeg=49.2606 + math.sin(angle) * 0.0018,
                    longitudeDeg=-123.246 + math.cos(angle) * 0.0027,
                    relativeAltitudeM=self.altitude,
                ),
                groundSpeedMps=8.4 + math.sin(angle) if self.armed else 0,
                headingDeg=(self.tick * 3.2) % 360,
                batteryPercent=max(20, 96 - self.tick * 0.018),
                gps=GpsStatus(fixType="3D FIX", satellites=18 + self.tick % 3),
                armed=self.armed,
                flightMode=self.mode,
            )
            self.tick += 1
            await asyncio.sleep(1 / self.telemetry_hz)

    async def execute(self, command: CommandRequest) -> str:
        key = str(command.id)
        self.command_executions[key] = self.command_executions.get(key, 0) + 1
        await asyncio.sleep(0.08)
        if command.type == CommandType.ARM:
            self.armed = True
            self.mode = "HOLD"
        elif command.type == CommandType.TAKEOFF:
            if not self.armed:
                raise RuntimeError("vehicle must be armed before takeoff")
            self.mode = "TAKEOFF"
        elif command.type == CommandType.LAND:
            self.mode = "LAND"
        elif command.type == CommandType.RTL:
            self.mode = "RTL"
        elif command.type == CommandType.START_MISSION:
            if self.mission is None:
                raise RuntimeError("upload a mission before starting it")
            self.mode = "MISSION"
        elif command.type == CommandType.SET_CURRENT_WAYPOINT:
            if self.mission is None:
                raise RuntimeError("no active mission")
            index = int(command.parameters["index"])
            if index >= len(self.mission.waypoints):
                raise RuntimeError("waypoint index is outside the mission")
        return "accepted"

    async def upload_mission(self, mission: Mission) -> str:
        self.mission = mission
        await asyncio.sleep(0.1)
        return f"uploaded {len(mission.waypoints)} waypoints"


class MavsdkVehicle(VehicleAdapter):
    """PX4 adapter. Importing MAVSDK lazily keeps demo mode lightweight."""

    def __init__(self, host: str, port: int) -> None:
        if host not in {"127.0.0.1", "::1"}:
            raise ValueError("only loopback PX4 endpoints are allowed")
        self.address = f"udpin://{host}:{port}"
        self._drone: Any = None

    async def _connect(self) -> Any:
        if self._drone is None:
            from mavsdk import System

            self._drone = System()
            await self._drone.connect(system_address=self.address)
            async for state in self._drone.core.connection_state():
                if state.is_connected:
                    break
        return self._drone

    async def telemetry(self) -> AsyncIterator[TelemetrySnapshot]:
        drone = await self._connect()
        latest: dict[str, Any] = {}

        async def consume(name: str, stream: Any) -> None:
            async for value in stream:
                latest[name] = value

        tasks = [
            asyncio.create_task(consume("position", drone.telemetry.position())),
            asyncio.create_task(consume("velocity", drone.telemetry.velocity_ned())),
            asyncio.create_task(consume("heading", drone.telemetry.heading())),
            asyncio.create_task(consume("battery", drone.telemetry.battery())),
            asyncio.create_task(consume("gps", drone.telemetry.gps_info())),
            asyncio.create_task(consume("armed", drone.telemetry.armed())),
            asyncio.create_task(consume("mode", drone.telemetry.flight_mode())),
        ]
        try:
            while True:
                if all(
                    key in latest
                    for key in (
                        "position",
                        "velocity",
                        "heading",
                        "battery",
                        "gps",
                        "armed",
                        "mode",
                    )
                ):
                    position = latest["position"]
                    velocity = latest["velocity"]
                    speed = math.hypot(velocity.north_m_s, velocity.east_m_s)
                    yield TelemetrySnapshot(
                        source="px4",
                        connection=ConnectionState.HEALTHY,
                        heartbeatAgeMs=0,
                        position=Position(
                            latitudeDeg=position.latitude_deg,
                            longitudeDeg=position.longitude_deg,
                            relativeAltitudeM=position.relative_altitude_m,
                        ),
                        groundSpeedMps=speed,
                        headingDeg=float(latest["heading"].heading_deg) % 360,
                        batteryPercent=max(0, min(100, latest["battery"].remaining_percent * 100)),
                        gps=GpsStatus(
                            fixType=str(latest["gps"].fix_type).split(".")[-1],
                            satellites=latest["gps"].num_satellites,
                        ),
                        armed=bool(latest["armed"]),
                        flightMode=str(latest["mode"]).split(".")[-1],
                    )
                await asyncio.sleep(0.2)
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    async def execute(self, command: CommandRequest) -> str:
        drone = await self._connect()
        actions = {
            CommandType.ARM: drone.action.arm,
            CommandType.TAKEOFF: drone.action.takeoff,
            CommandType.LAND: drone.action.land,
            CommandType.RTL: drone.action.return_to_launch,
            CommandType.START_MISSION: drone.mission.start_mission,
        }
        if command.type == CommandType.SET_CURRENT_WAYPOINT:
            await drone.mission.set_current_mission_item(int(command.parameters["index"]))
        else:
            await actions[command.type]()
        return "COMMAND_ACK accepted"

    async def upload_mission(self, mission: Mission) -> str:
        from mavsdk.mission import MissionItem, MissionPlan

        drone = await self._connect()
        items = [
            MissionItem(
                waypoint.latitudeDeg,
                waypoint.longitudeDeg,
                waypoint.relativeAltitudeM,
                waypoint.speedMps,
                waypoint.flyThrough,
                float("nan"),
                float("nan"),
                MissionItem.CameraAction.NONE,
                float("nan"),
                float("nan"),
                waypoint.acceptanceRadiusM,
                float("nan"),
                float("nan"),
                MissionItem.VehicleAction.NONE,
            )
            for waypoint in mission.waypoints
        ]
        await drone.mission.upload_mission(MissionPlan(items))
        return f"uploaded {len(items)} waypoints"
