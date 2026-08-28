import argparse
import asyncio
import random
from collections.abc import Callable

from skylink.models import LinkProfile, LinkStats

Address = tuple[str, int]


class ImpairmentEngine:
    def __init__(self, profile: LinkProfile | None = None) -> None:
        self.profile = profile or LinkProfile()
        self.stats = {"vehicle_to_app": LinkStats(), "app_to_vehicle": LinkStats()}
        self._random = random.Random(self.profile.seed)

    def set_profile(self, profile: LinkProfile) -> None:
        self.profile = profile
        self._random = random.Random(profile.seed)

    def decisions(self, direction: str) -> tuple[bool, float, int]:
        stats = self.stats[direction]
        stats.received += 1
        dropped = self._random.random() * 100 < self.profile.lossPercent
        if dropped:
            stats.dropped += 1
            return True, 0, 0
        jitter = self._random.uniform(-self.profile.jitterMs, self.profile.jitterMs)
        delay = max(0, self.profile.delayMs + jitter) / 1000
        copies = 2 if self._random.random() * 100 < self.profile.duplicatePercent else 1
        if delay:
            stats.delayed += copies
        if copies == 2:
            stats.duplicated += 1
        stats.forwarded += copies
        return False, delay, copies


class RelayProtocol(asyncio.DatagramProtocol):
    def __init__(self, receiver: Callable[[bytes, Address], None]) -> None:
        self.receiver = receiver

    def datagram_received(self, data: bytes, addr: Address) -> None:
        self.receiver(data, addr)


class LinkProxy:
    def __init__(
        self,
        vehicle_port: int = 14540,
        relay_port: int = 14541,
        app_port: int = 14542,
        profile: LinkProfile | None = None,
    ) -> None:
        self.vehicle_port = vehicle_port
        self.relay_port = relay_port
        self.app_target: Address = ("127.0.0.1", app_port)
        self.engine = ImpairmentEngine(profile)
        self.vehicle_peer: Address | None = None
        self.vehicle_transport: asyncio.DatagramTransport | None = None
        self.app_transport: asyncio.DatagramTransport | None = None

    async def start(self) -> None:
        loop = asyncio.get_running_loop()
        vehicle_transport, _ = await loop.create_datagram_endpoint(
            lambda: RelayProtocol(self._from_vehicle), local_addr=("127.0.0.1", self.vehicle_port)
        )
        app_transport, _ = await loop.create_datagram_endpoint(
            lambda: RelayProtocol(self._from_app), local_addr=("127.0.0.1", self.relay_port)
        )
        self.vehicle_transport = vehicle_transport
        self.app_transport = app_transport

    def close(self) -> None:
        if self.vehicle_transport:
            self.vehicle_transport.close()
        if self.app_transport:
            self.app_transport.close()

    def set_profile(self, profile: LinkProfile) -> None:
        self.engine.set_profile(profile)

    def _from_vehicle(self, data: bytes, addr: Address) -> None:
        self.vehicle_peer = addr
        self._forward(data, self.app_transport, self.app_target, "vehicle_to_app")

    def _from_app(self, data: bytes, _addr: Address) -> None:
        if self.vehicle_peer:
            self._forward(data, self.vehicle_transport, self.vehicle_peer, "app_to_vehicle")

    def _forward(
        self,
        data: bytes,
        transport: asyncio.DatagramTransport | None,
        target: Address,
        direction: str,
    ) -> None:
        if transport is None:
            return
        dropped, delay, copies = self.engine.decisions(direction)
        if dropped:
            return
        loop = asyncio.get_running_loop()
        for copy in range(copies):
            loop.call_later(delay + copy * 0.001, transport.sendto, data, target)

    def stats(self) -> dict[str, LinkStats]:
        return self.engine.stats


async def _serve(args: argparse.Namespace) -> None:
    proxy = LinkProxy(args.vehicle_port, args.relay_port, args.app_port)
    await proxy.start()
    try:
        await asyncio.Event().wait()
    finally:
        proxy.close()


def run() -> None:
    parser = argparse.ArgumentParser(description="SkyLink MAVLink UDP impairment relay")
    parser.add_argument("--vehicle-port", type=int, default=14540)
    parser.add_argument("--relay-port", type=int, default=14541)
    parser.add_argument("--app-port", type=int, default=14542)
    asyncio.run(_serve(parser.parse_args()))


if __name__ == "__main__":
    run()
