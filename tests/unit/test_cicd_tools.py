"""Regression tests for CI/CD evidence and release artifacts."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from scripts.benchmark_events import benchmark_succeeded
from scripts.build_lambda import create_deterministic_zip, validate_lambda_archive
from scripts.chaos_test import _is_order_from_batch, chaos_succeeded
from scripts.generate_summary import generate_dashboard
from scripts.release_version import determine_bump, next_version
from scripts.render_performance_site import append_history, render_site
from scripts.validate_results import evaluate_results, main


def _passing_benchmark() -> dict:
    return {
        "total_requests": 100,
        "successful_requests": 100,
        "failed_requests": 0,
        "success_rate_percent": 100.0,
        "throughput_req_per_sec": 50.0,
        "total_duration_sec": 2.0,
        "latency_ms": {
            "avg": 20.0,
            "min": 10.0,
            "p50": 18.0,
            "p90": 30.0,
            "p95": 35.0,
            "p99": 50.0,
            "max": 60.0,
        },
    }


def _passing_chaos() -> dict:
    return {
        "total_injected_orders": 50,
        "valid_orders_expected": 40,
        "valid_orders_persisted": 40,
        "poison_orders_injected": 10,
        "poison_orders_isolated_dlq": 10,
        "fault_isolation_rate_percent": 100.0,
        "zero_data_loss_verified": True,
    }


def test_dashboard_fails_closed_when_results_are_missing(tmp_path: Path) -> None:
    dashboard = generate_dashboard(
        str(tmp_path / "missing-benchmark.json"),
        str(tmp_path / "missing-chaos.json"),
    )

    assert "NO DATA" in dashboard
    assert "100% VERIFIED" not in dashboard
    assert "🟢 **PASS**" not in dashboard


def test_result_evaluation_rejects_missing_evidence() -> None:
    report = evaluate_results({}, {})

    assert report["passed"] is False
    assert "benchmark evidence is missing" in report["failures"]
    assert "chaos evidence is missing" in report["failures"]


def test_result_evaluation_detects_performance_regression() -> None:
    current = _passing_benchmark()
    baseline = _passing_benchmark()
    current["throughput_req_per_sec"] = 35.0
    current["latency_ms"]["p99"] = 70.0

    report = evaluate_results(
        current,
        _passing_chaos(),
        baseline=baseline,
        max_throughput_regression_percent=20.0,
        max_p99_regression_percent=25.0,
    )

    assert report["passed"] is False
    assert any("throughput regressed" in failure for failure in report["failures"])
    assert any("p99 latency regressed" in failure for failure in report["failures"])


def test_benchmark_cli_gate_rejects_failed_requests() -> None:
    result = _passing_benchmark()
    result["failed_requests"] = 1
    result["successful_requests"] = 99
    result["success_rate_percent"] = 99.0

    assert benchmark_succeeded(result) is False


def test_chaos_cli_gate_requires_zero_data_loss() -> None:
    result = _passing_chaos()
    result["zero_data_loss_verified"] = False

    assert chaos_succeeded(result) is False


@pytest.mark.parametrize("malformed_order_id", [None, 42, b"chaos-test-123"])
def test_batch_matching_ignores_non_string_order_ids(malformed_order_id: object) -> None:
    assert _is_order_from_batch(malformed_order_id, "chaos-test") is False


def test_batch_matching_accepts_a_string_order_id_from_the_batch() -> None:
    assert _is_order_from_batch("chaos-test-123", "chaos-test") is True


def test_validator_cli_writes_report_and_returns_failure(tmp_path: Path) -> None:
    benchmark_path = tmp_path / "benchmark.json"
    chaos_path = tmp_path / "chaos.json"
    report_path = tmp_path / "validation.json"
    benchmark_path.write_text(json.dumps({}), encoding="utf-8")
    chaos_path.write_text(json.dumps({}), encoding="utf-8")

    exit_code = main(
        [
            "--benchmark",
            str(benchmark_path),
            "--chaos",
            str(chaos_path),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 1
    assert json.loads(report_path.read_text(encoding="utf-8"))["passed"] is False


def test_lambda_archive_is_deterministic_and_contains_dependencies(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    (package_dir / "src" / "handlers").mkdir(parents=True)
    (package_dir / "src" / "handlers" / "order_ingest.py").write_text(
        "def handler(event, context=None): return event\n", encoding="utf-8"
    )
    (package_dir / "src" / "handlers" / "order_worker.py").write_text(
        "def handler(event, context=None): return event\n", encoding="utf-8"
    )
    (package_dir / "pydantic").mkdir()
    (package_dir / "pydantic" / "__init__.py").write_text("", encoding="utf-8")
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_digest = create_deterministic_zip(package_dir, first)
    second_digest = create_deterministic_zip(package_dir, second)

    assert first_digest == second_digest
    assert validate_lambda_archive(first, required_modules=("pydantic",)) == first_digest
    with zipfile.ZipFile(first) as archive:
        assert archive.namelist() == sorted(archive.namelist())
        assert "src/handlers/order_ingest.py" in archive.namelist()


def test_lambda_archive_validation_rejects_missing_dependency(tmp_path: Path) -> None:
    package_dir = tmp_path / "package"
    (package_dir / "src").mkdir(parents=True)
    (package_dir / "src" / "__init__.py").write_text("", encoding="utf-8")
    archive = tmp_path / "lambda.zip"
    create_deterministic_zip(package_dir, archive)

    with pytest.raises(ValueError, match="pydantic"):
        validate_lambda_archive(archive, required_modules=("pydantic",))


@pytest.mark.parametrize(
    ("messages", "expected"),
    [
        (["docs: clarify setup"], None),
        (["fix: handle retries"], "patch"),
        (["perf(worker): pool clients"], "patch"),
        (["feat: add replay support", "fix: typo"], "minor"),
        (["feat!: replace event schema"], "major"),
        (["feat: new schema\n\nBREAKING CHANGE: schema v2"], "major"),
    ],
)
def test_release_bump_uses_conventional_commits(messages: list[str], expected: str | None) -> None:
    assert determine_bump(messages) == expected


@pytest.mark.parametrize(
    ("current", "bump", "expected"),
    [
        ("v0.7.3", "patch", "v0.7.4"),
        ("v0.7.3", "minor", "v0.8.0"),
        ("v0.7.3", "major", "v1.0.0"),
        (None, "minor", "v0.1.0"),
    ],
)
def test_next_version_increments_semver(current: str | None, bump: str, expected: str) -> None:
    assert next_version(current, bump) == expected


def test_performance_history_is_deduplicated_and_bounded() -> None:
    history = [
        {"run_id": str(index), "timestamp": f"2026-08-{index + 1:02d}"} for index in range(5)
    ]
    duplicate = {"run_id": "4", "timestamp": "2026-08-22", "passed": True}

    updated = append_history(history, duplicate, limit=3)

    assert [entry["run_id"] for entry in updated] == ["2", "3", "4"]
    assert len([entry for entry in updated if entry["run_id"] == "4"]) == 1
    assert updated[-1]["passed"] is True


def test_performance_site_contains_latest_evidence(tmp_path: Path) -> None:
    history = [
        {
            "run_id": "123",
            "timestamp": "2026-08-22T00:00:00Z",
            "sha": "abcdef123456",
            "passed": True,
            "benchmark": {
                "throughput_req_per_sec": 42.5,
                "success_rate_percent": 100.0,
                "latency_ms": {"p50": 20.0, "p99": 75.0},
            },
            "chaos": {
                "fault_isolation_rate_percent": 100.0,
                "zero_data_loss_verified": True,
            },
        }
    ]

    render_site(history, tmp_path)

    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "42.5 req/s" in html
    assert "abcdef1" in html
    assert "PASS" in html
    assert (tmp_path / "history.json").is_file()
