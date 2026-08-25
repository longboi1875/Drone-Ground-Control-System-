import asyncio
from uuid import UUID

from skylink.broadcast import Broadcast
from skylink.database import Database
from skylink.models import ReplayControl, TelemetrySnapshot


class ReplayController:
    def __init__(self, database: Database, output: Broadcast[TelemetrySnapshot]) -> None:
        self.database = database
        self.output = output
        self.task: asyncio.Task[None] | None = None
        self.paused = False
        self.speed = 1.0
        self.index = 0
        self.frames: list[TelemetrySnapshot] = []

    @property
    def active(self) -> bool:
        return self.task is not None and not self.task.done()

    async def start(self, flight_id: UUID) -> None:
        await self.stop()
        self.frames = await self.database.telemetry_for_flight(flight_id)
        if not self.frames:
            raise ValueError("flight has no recorded telemetry")
        self.index = 0
        self.paused = False
        self.task = asyncio.create_task(self._run())

    async def control(self, control: ReplayControl) -> None:
        self.speed = control.speed
        if control.action == "pause":
            self.paused = True
        elif control.action == "play":
            self.paused = False
        elif control.action == "restart":
            self.index = 0
            self.paused = False
        elif control.action == "seek" and self.frames:
            start = self.frames[0].timestamp
            self.index = next(
                (
                    i
                    for i, frame in enumerate(self.frames)
                    if (frame.timestamp - start).total_seconds() >= control.positionSeconds
                ),
                len(self.frames) - 1,
            )
        elif control.action == "stop":
            await self.stop()

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.task = None
        self.frames = []

    async def _run(self) -> None:
        while self.index < len(self.frames):
            if self.paused:
                await asyncio.sleep(0.1)
                continue
            frame = self.frames[self.index].model_copy(update={"source": "replay"})
            await self.output.publish(frame)
            if self.index + 1 < len(self.frames):
                delta = (
                    self.frames[self.index + 1].timestamp - self.frames[self.index].timestamp
                ).total_seconds()
                await asyncio.sleep(max(0.01, delta / self.speed))
            self.index += 1
