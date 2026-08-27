from skylink.benchmark import run_profile, write_results
from skylink.models import LinkProfile


def test_clean_link_acknowledges_every_command() -> None:
    result = run_profile(LinkProfile(name="Clean"), commands=25)
    assert result.acknowledged == 25
    assert result.retries == 0
    assert result.duplicate_executions == 0


def test_benchmark_is_deterministic() -> None:
    profile = LinkProfile(name="Rough", lossPercent=25, delayMs=200, jitterMs=80, seed=481)
    assert run_profile(profile, 100) == run_profile(profile, 100)


def test_writes_json_and_csv(tmp_path) -> None:
    result = run_profile(LinkProfile(name="Clean"), commands=5)
    json_path, csv_path = write_results([result], tmp_path)
    assert '"duplicate_executions": 0' in json_path.read_text()
    assert "success_rate_percent" in csv_path.read_text()
