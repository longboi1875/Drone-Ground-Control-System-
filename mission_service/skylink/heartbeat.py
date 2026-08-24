from skylink.models import ConnectionState


def connection_state(age_ms: int, degraded_after_ms: int, lost_after_ms: int) -> ConnectionState:
    if age_ms < 0:
        raise ValueError("heartbeat age cannot be negative")
    if degraded_after_ms <= 0 or lost_after_ms <= degraded_after_ms:
        raise ValueError("heartbeat thresholds must be positive and ordered")
    if age_ms >= lost_after_ms:
        return ConnectionState.LOST
    if age_ms >= degraded_after_ms:
        return ConnectionState.DEGRADED
    return ConnectionState.HEALTHY
