"""Validate benchmark and chaos evidence for CI quality gates.

The validator deliberately fails closed: missing or malformed telemetry is a
failed quality gate, never a successful empty run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _percent_change(previous: float, current: float) -> float:
    if previous == 0:
        return 0.0
    return ((current - previous) / previous) * 100.0


def evaluate_results(
    benchmark: dict[str, Any],
    chaos: dict[str, Any],
    *,
    baseline: dict[str, Any] | None = None,
    max_throughput_regression_percent: float = 20.0,
    max_p99_regression_percent: float = 25.0,
    min_success_rate: float = 99.0,
    min_throughput: float = 25.0,
    max_p99_ms: float = 2500.0,
    min_isolation_rate: float = 99.9,
) -> dict[str, Any]:
    failures: list[str] = []

    if not benchmark:
        failures.append("benchmark evidence is missing")
    if not chaos:
        failures.append("chaos evidence is missing")

    success_rate = float(benchmark.get("success_rate_percent", 0.0))
    throughput = float(benchmark.get("throughput_req_per_sec", 0.0))
    p99 = float(benchmark.get("latency_ms", {}).get("p99", float("inf")))
    isolation_rate = float(chaos.get("fault_isolation_rate_percent", 0.0))
    zero_data_loss = chaos.get("zero_data_loss_verified") is True

    if benchmark:
        if success_rate < min_success_rate:
            failures.append(f"success rate {success_rate:.2f}% is below {min_success_rate:.2f}%")
        if throughput < min_throughput:
            failures.append(
                f"throughput {throughput:.2f} req/s is below {min_throughput:.2f} req/s"
            )
        if p99 > max_p99_ms:
            failures.append(f"p99 latency {p99:.2f} ms exceeds {max_p99_ms:.2f} ms")

    if chaos:
        if isolation_rate < min_isolation_rate:
            failures.append(
                f"fault isolation {isolation_rate:.2f}% is below {min_isolation_rate:.2f}%"
            )
        if not zero_data_loss:
            failures.append("zero data loss was not verified")

    throughput_regression = 0.0
    p99_regression = 0.0
    if baseline:
        baseline_throughput = float(baseline.get("throughput_req_per_sec", 0.0))
        baseline_p99 = float(baseline.get("latency_ms", {}).get("p99", 0.0))
        throughput_regression = -_percent_change(baseline_throughput, throughput)
        p99_regression = _percent_change(baseline_p99, p99)
        if throughput_regression > max_throughput_regression_percent:
            failures.append(
                "throughput regressed "
                f"{throughput_regression:.2f}% (limit {max_throughput_regression_percent:.2f}%)"
            )
        if p99_regression > max_p99_regression_percent:
            failures.append(
                "p99 latency regressed "
                f"{p99_regression:.2f}% (limit {max_p99_regression_percent:.2f}%)"
            )

    return {
        "passed": not failures,
        "failures": failures,
        "metrics": {
            "success_rate_percent": success_rate,
            "throughput_req_per_sec": throughput,
            "p99_latency_ms": p99 if p99 != float("inf") else None,
            "fault_isolation_rate_percent": isolation_rate,
            "zero_data_loss_verified": zero_data_loss,
            "throughput_regression_percent": round(throughput_regression, 2),
            "p99_regression_percent": round(p99_regression, 2),
        },
    }


def _load_json(path: str | None) -> dict[str, Any]:
    if not path or not Path(path).is_file():
        return {}
    with Path(path).open(encoding="utf-8") as handle:
        value = json.load(handle)
    return value if isinstance(value, dict) else {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate performance and resilience evidence")
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--chaos", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--output", default="validation_results.json")
    parser.add_argument("--min-success-rate", type=float, default=99.0)
    parser.add_argument("--min-throughput", type=float, default=25.0)
    parser.add_argument("--max-p99-ms", type=float, default=2500.0)
    parser.add_argument("--min-isolation-rate", type=float, default=99.9)
    parser.add_argument("--max-throughput-regression-percent", type=float, default=20.0)
    parser.add_argument("--max-p99-regression-percent", type=float, default=25.0)
    args = parser.parse_args(argv)

    report = evaluate_results(
        _load_json(args.benchmark),
        _load_json(args.chaos),
        baseline=_load_json(args.baseline) if args.baseline else None,
        min_success_rate=args.min_success_rate,
        min_throughput=args.min_throughput,
        max_p99_ms=args.max_p99_ms,
        min_isolation_rate=args.min_isolation_rate,
        max_throughput_regression_percent=args.max_throughput_regression_percent,
        max_p99_regression_percent=args.max_p99_regression_percent,
    )
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
