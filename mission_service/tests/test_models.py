from uuid import uuid4

import pytest
from pydantic import ValidationError
from skylink.models import CommandRequest, MissionCreate, Waypoint


def test_waypoint_rejects_unsafe_altitude() -> None:
    with pytest.raises(ValidationError):
        Waypoint(
            latitudeDeg=49.26,
            longitudeDeg=-123.24,
            relativeAltitudeM=121,
            speedMps=8,
            acceptanceRadiusM=3,
        )


def test_change_waypoint_requires_index() -> None:
    with pytest.raises(ValidationError):
        CommandRequest(id=uuid4(), type="set_current_waypoint")


def test_mission_requires_a_waypoint() -> None:
    with pytest.raises(ValidationError):
        MissionCreate(name="Empty", waypoints=[])
