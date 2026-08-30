import asyncio
from types import SimpleNamespace

import pytest
from skylink.vehicle import MavsdkVehicle


async def one_update(value: object):
    yield value
    await asyncio.Event().wait()


class FakeTelemetry:
    def position(self):
        return one_update(
            SimpleNamespace(
                latitude_deg=49.2606,
                longitude_deg=-123.246,
                relative_altitude_m=3.0,
            )
        )

    def velocity_ned(self):
        return one_update(SimpleNamespace(north_m_s=2.0, east_m_s=1.0))

    def heading(self):
        return one_update(SimpleNamespace(heading_deg=90.0))

    def battery(self):
        return one_update(SimpleNamespace(remaining_percent=0.8))

    def gps_info(self):
        return one_update(SimpleNamespace(fix_type="FIX_3D", num_satellites=10))

    def armed(self):
        return one_update(False)

    def flight_mode(self):
        return one_update("HOLD")


@pytest.mark.asyncio
async def test_mavsdk_adapter_does_not_repeat_a_stale_snapshot() -> None:
    adapter = MavsdkVehicle("127.0.0.1", 14542)
    adapter._drone = SimpleNamespace(telemetry=FakeTelemetry())
    stream = adapter.telemetry()

    snapshot = await asyncio.wait_for(anext(stream), 1)
    assert snapshot.source == "px4"

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(stream), 0.35)
