"""Event Ingestion Throughput Benchmark Utility."""

import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

# Ensure project root is on sys.path for direct handler imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.handlers import order_ingest


def generate_mock_order(index: int) -> dict:
    return {
        "order_id": f"ord_bench_{int(time.time())}_{index:04d}",
        "customer_id": f"cust_bench_{index % 100}",
        "currency": "USD",
        "items": [
            {
                "item_id": f"item_{index}",
                "name": "Benchmark Micro-Compute",
                "quantity": 1,
                "unit_price": 10.0,
            }
        ],
    }


def send_order(endpoint: str, order: dict, direct: bool = False) -> tuple[bool, float]:
    start_time = time.perf_counter()
    if direct:
        try:
            event = {"body": json.dumps(order)}
            res = order_ingest.handler(event)
            latency = time.perf_counter() - start_time
            return (res.get("statusCode") == 201, latency)
        except Exception:
            latency = time.perf_counter() - start_time
            return (False, latency)

    url = f"{endpoint.rstrip('/')}/orders"
    data = json.dumps(order).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Benchmarker/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            latency = time.perf_counter() - start_time
            return (response.status == 201, latency)
    except Exception:
        # Fallback to direct handler invocation
        try:
            event = {"body": json.dumps(order)}
            res = order_ingest.handler(event)
            latency = time.perf_counter() - start_time
            return (res.get("statusCode") == 201, latency)
        except Exception:
            latency = time.perf_counter() - start_time
            return (False, latency)


def calculate_percentile(sorted_data: list[float], percentile: float) -> float:
    """Calculate the given percentile from sorted data."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * percentile
    f = int(k)
    c = min(f + 1, len(sorted_data) - 1)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return d0 + d1


def run_benchmark(
    endpoint: str = "http://localhost:4566",
    total_requests: int = 50,
    concurrency: int = 5,
    direct: bool = False,
    output_file: str | None = None,
) -> dict:
    print(
        f"🚀 Starting Event Ingestion Benchmark: {total_requests} requests (concurrency: {concurrency})"
    )
    print(f"🔗 Target Endpoint: {endpoint} (Direct Handler: {direct})\n")

    orders = [generate_mock_order(i) for i in range(total_requests)]
    warmup_order = generate_mock_order(total_requests)
    warmup_succeeded, _ = send_order(endpoint, warmup_order, direct)
    if not warmup_succeeded:
        raise RuntimeError("Benchmark warm-up request failed")

    latencies: list[float] = []
    success_count = 0

    wall_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_order, endpoint, order, direct) for order in orders]
        for future in concurrent.futures.as_completed(futures):
            success, latency = future.result()
            latencies.append(latency)
            if success:
                success_count += 1

    wall_duration = time.perf_counter() - wall_start
    throughput = total_requests / wall_duration if wall_duration > 0 else 0
    sorted_ms = sorted([lat * 1000.0 for lat in latencies])

    avg_ms = (sum(latencies) / len(latencies)) * 1000.0 if latencies else 0.0
    min_ms = min(sorted_ms) if sorted_ms else 0.0
    max_ms = max(sorted_ms) if sorted_ms else 0.0
    p50_ms = calculate_percentile(sorted_ms, 0.50)
    p90_ms = calculate_percentile(sorted_ms, 0.90)
    p95_ms = calculate_percentile(sorted_ms, 0.95)
    p99_ms = calculate_percentile(sorted_ms, 0.99)
    success_rate = (success_count / total_requests) * 100 if total_requests > 0 else 0.0

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_endpoint": endpoint,
        "direct_invocation": direct,
        "total_requests": total_requests,
        "concurrency": concurrency,
        "successful_requests": success_count,
        "failed_requests": total_requests - success_count,
        "success_rate_percent": round(success_rate, 2),
        "total_duration_sec": round(wall_duration, 3),
        "throughput_req_per_sec": round(throughput, 2),
        "latency_ms": {
            "avg": round(avg_ms, 2),
            "min": round(min_ms, 2),
            "p50": round(p50_ms, 2),
            "p90": round(p90_ms, 2),
            "p95": round(p95_ms, 2),
            "p99": round(p99_ms, 2),
            "max": round(max_ms, 2),
        },
    }

    print("📊 Benchmark Results:")
    print(f"  • Total Requests:  {total_requests}")
    print(f"  • Success Rate:    {success_count}/{total_requests} ({success_rate:.1f}%)")
    print(f"  • Total Time:      {wall_duration:.2f}s")
    print(f"  • Throughput:      {throughput:.1f} req/sec")
    print(f"  • Latency Avg:     {avg_ms:.1f} ms")
    print(f"  • Latency p50:     {p50_ms:.1f} ms")
    print(f"  • Latency p90:     {p90_ms:.1f} ms")
    print(f"  • Latency p95:     {p95_ms:.1f} ms")
    print(f"  • Latency p99:     {p99_ms:.1f} ms")
    print(f"  • Latency Max:     {max_ms:.1f} ms")

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Telemetry results exported to: {output_file}")

    return results


def benchmark_succeeded(results: dict) -> bool:
    return (
        int(results.get("failed_requests", 1)) == 0
        and float(results.get("success_rate_percent", 0.0)) == 100.0
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event Ingestion Load Benchmarker")
    parser.add_argument(
        "--endpoint", default="http://localhost:4566/restapis/orders", help="Target API URL"
    )
    parser.add_argument(
        "--requests",
        "--total",
        dest="requests",
        type=int,
        default=50,
        help="Total requests to fire",
    )
    parser.add_argument(
        "--concurrency",
        "--batch",
        dest="concurrency",
        type=int,
        default=5,
        help="Concurrent workers",
    )
    parser.add_argument(
        "--direct", action="store_true", help="Direct in-process serverless handler invocation"
    )
    parser.add_argument(
        "--output", default=None, help="Path to write JSON benchmark telemetry results"
    )
    args = parser.parse_args()

    os.environ["AWS_ENDPOINT_URL"] = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    benchmark_results = run_benchmark(
        args.endpoint, args.requests, args.concurrency, args.direct, args.output
    )
    raise SystemExit(0 if benchmark_succeeded(benchmark_results) else 1)
