from skylink.link_proxy import ImpairmentEngine
from skylink.models import LinkProfile


def test_impairment_is_repeatable_with_seed() -> None:
    profile = LinkProfile(lossPercent=30, delayMs=80, jitterMs=20, duplicatePercent=25, seed=481)
    first = ImpairmentEngine(profile)
    second = ImpairmentEngine(profile)
    assert [first.decisions("vehicle_to_app") for _ in range(50)] == [
        second.decisions("vehicle_to_app") for _ in range(50)
    ]


def test_total_loss_drops_every_packet() -> None:
    engine = ImpairmentEngine(LinkProfile(lossPercent=100))
    assert all(engine.decisions("app_to_vehicle")[0] for _ in range(10))
    assert engine.stats["app_to_vehicle"].dropped == 10
