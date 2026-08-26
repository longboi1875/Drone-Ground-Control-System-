import pytest
from skylink.heartbeat import connection_state
from skylink.models import ConnectionState


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (0, ConnectionState.HEALTHY),
        (1499, ConnectionState.HEALTHY),
        (1500, ConnectionState.DEGRADED),
        (3999, ConnectionState.DEGRADED),
        (4000, ConnectionState.LOST),
    ],
)
def test_connection_state_boundaries(age: int, expected: ConnectionState) -> None:
    assert connection_state(age, 1500, 4000) == expected


def test_connection_state_rejects_bad_thresholds() -> None:
    with pytest.raises(ValueError):
        connection_state(1, 4000, 1500)
