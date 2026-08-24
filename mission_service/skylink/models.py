from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1


def utc_now() -> datetime:
    return datetime.now(UTC)


class ConnectionState(StrEnum):
    CONNECTING = "connecting"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    LOST = "lost"


class CommandType(StrEnum):
    ARM = "arm"
    TAKEOFF = "takeoff"
    LAND = "land"
    RTL = "rtl"
    START_MISSION = "start_mission"
    SET_CURRENT_WAYPOINT = "set_current_waypoint"


class CommandState(StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


class Position(BaseModel):
    latitudeDeg: float = Field(ge=-90, le=90)
    longitudeDeg: float = Field(ge=-180, le=180)
    relativeAltitudeM: float


class GpsStatus(BaseModel):
    fixType: str
    satellites: int = Field(ge=0)


class TelemetrySnapshot(BaseModel):
    schemaVersion: Literal[1] = SCHEMA_VERSION
    timestamp: datetime = Field(default_factory=utc_now)
    source: Literal["demo", "px4", "replay"]
    connection: ConnectionState
    heartbeatAgeMs: int = Field(ge=0)
    position: Position
    groundSpeedMps: float = Field(ge=0)
    headingDeg: float = Field(ge=0, lt=360)
    batteryPercent: float = Field(ge=0, le=100)
    gps: GpsStatus
    armed: bool
    flightMode: str


class GroundEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=utc_now)
    severity: Literal["info", "success", "warning", "error"] = "info"
    message: str
    kind: str = "system"


class Waypoint(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    latitudeDeg: float = Field(ge=-90, le=90)
    longitudeDeg: float = Field(ge=-180, le=180)
    relativeAltitudeM: float = Field(gt=0, le=120)
    speedMps: float = Field(gt=0, le=25)
    acceptanceRadiusM: float = Field(gt=0, le=50)
    flyThrough: bool = False


class MissionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    waypoints: list[Waypoint] = Field(min_length=1, max_length=100)


class Mission(MissionCreate):
    id: UUID = Field(default_factory=uuid4)
    createdAt: datetime = Field(default_factory=utc_now)


class CommandRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    type: CommandType
    parameters: dict[str, Any] = Field(default_factory=dict)
    createdAt: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_parameters(self) -> "CommandRequest":
        if self.type == CommandType.SET_CURRENT_WAYPOINT:
            index = self.parameters.get("index")
            if not isinstance(index, int) or index < 0:
                raise ValueError("set_current_waypoint requires a non-negative integer index")
        return self


class CommandRecord(CommandRequest):
    state: CommandState = CommandState.QUEUED
    attempts: int = 0
    updatedAt: datetime = Field(default_factory=utc_now)
    acknowledgement: str | None = None
    error: str | None = None


class LinkProfile(BaseModel):
    name: str = "Clean"
    lossPercent: float = Field(default=0, ge=0, le=100)
    delayMs: int = Field(default=0, ge=0, le=10_000)
    jitterMs: int = Field(default=0, ge=0, le=10_000)
    duplicatePercent: float = Field(default=0, ge=0, le=100)
    seed: int = 481


class LinkStats(BaseModel):
    received: int = 0
    forwarded: int = 0
    dropped: int = 0
    delayed: int = 0
    duplicated: int = 0


class ReplayControl(BaseModel):
    action: Literal["play", "pause", "seek", "restart", "stop"]
    speed: Literal[0.5, 1.0, 2.0, 4.0] = 1.0
    positionSeconds: float = Field(default=0, ge=0)
