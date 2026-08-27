import argparse
import csv
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean

from skylink.models import LinkProfile


@dataclass(frozen=True)
class BenchmarkResult:
    profile: str
    loss_percent: float
    delay_ms: int
    duplicate_percent: float
    commands: int
    acknowledged: int
    success_rate_percent: float
    average_ack_latency_ms: float
    retries: int
    duplicate_deliveries: int
    duplicate_executions: int


def run_profile(
    profile: LinkProfile, commands: int = 100, max_attempts: int = 5
) -> BenchmarkResult:
    rng = random.Random(profile.seed)
    acknowledged = retries = duplicate_deliveries = 0
    latencies: list[float] = []
    processed: set[int] = set()
    duplicate_executions = 0

    for command_id in range(commands):
        elapsed = 0.0
        for attempt in range(max_attempts):
            if attempt:
                retries += 1
                elapsed += 500 * (2 ** (attempt - 1))
            outbound_dropped = rng.random() * 100 < profile.lossPercent
            elapsed += max(0, profile.delayMs + rng.uniform(-profile.jitterMs, profile.jitterMs))
            if outbound_dropped:
                continue
            deliveries = 2 if rng.random() * 100 < profile.duplicatePercent else 1
            duplicate_deliveries += deliveries - 1
            for _ in range(deliveries):
                if command_id in processed:
                    continue
                processed.add(command_id)
            ack_dropped = rng.random() * 100 < profile.lossPercent
            elapsed += max(0, profile.delayMs + rng.uniform(-profile.jitterMs, profile.jitterMs))
            if ack_dropped:
                continue
            acknowledged += 1
            latencies.append(elapsed)
            break

    return BenchmarkResult(
        profile=profile.name,
        loss_percent=profile.lossPercent,
        delay_ms=profile.delayMs,
        duplicate_percent=profile.duplicatePercent,
        commands=commands,
        acknowledged=acknowledged,
        success_rate_percent=round(acknowledged / commands * 100, 2),
        average_ack_latency_ms=round(mean(latencies), 2) if latencies else 0,
        retries=retries,
        duplicate_deliveries=duplicate_deliveries,
        duplicate_executions=duplicate_executions,
    )


def profiles() -> list[LinkProfile]:
    return [
        LinkProfile(name="Clean", seed=481),
        LinkProfile(name="5% loss / 100 ms", lossPercent=5, delayMs=100, jitterMs=25, seed=481),
        LinkProfile(
            name="15% loss / 250 ms",
            lossPercent=15,
            delayMs=250,
            jitterMs=50,
            duplicatePercent=5,
            seed=481,
        ),
        LinkProfile(
            name="30% loss / 500 ms",
            lossPercent=30,
            delayMs=500,
            jitterMs=100,
            duplicatePercent=10,
            seed=481,
        ),
    ]


def write_results(results: list[BenchmarkResult], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "reliability.json"
    csv_path = output_dir / "reliability.csv"
    records = [asdict(result) for result in results]
    json_path.write_text(json.dumps(records, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    return json_path, csv_path


def run() -> None:
    parser = argparse.ArgumentParser(description="Run deterministic SkyLink reliability benchmarks")
    parser.add_argument("--commands", type=int, default=100)
    parser.add_argument("--output", type=Path, default=Path("data/benchmarks"))
    args = parser.parse_args()
    results = [run_profile(profile, args.commands) for profile in profiles()]
    json_path, csv_path = write_results(results, args.output)
    for result in results:
        summary = f"{result.success_rate_percent:6.2f}%  {result.average_ack_latency_ms:8.1f} ms"
        print(f"{result.profile:24} {summary}")
    print(f"Wrote {json_path} and {csv_path}")


if __name__ == "__main__":
    run()
