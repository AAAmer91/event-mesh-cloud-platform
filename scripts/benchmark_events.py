"""Event Ingestion Throughput Benchmark Utility."""

import argparse
import concurrent.futures
import json
import time
import urllib.request
import uuid


def generate_mock_order(index: int) -> dict:
    return {
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


def send_order(endpoint: str, order: dict) -> tuple[bool, float]:
    url = f"{endpoint.rstrip('/')}/orders"
    data = json.dumps(order).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Benchmarker/1.0"},
        method="POST",
    )

    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            latency = time.perf_counter() - start_time
            return (response.status == 201, latency)
    except Exception:
        latency = time.perf_counter() - start_time
        return (False, latency)


def run_benchmark(endpoint: str, total_requests: int = 50, concurrency: int = 5):
    print(f"🚀 Starting Event Ingestion Benchmark: {total_requests} requests (concurrency: {concurrency})")
    print(f"🔗 Target Endpoint: {endpoint}\n")

    orders = [generate_mock_order(i) for i in range(total_requests)]
    latencies: list[float] = []
    success_count = 0

    wall_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_order, endpoint, order) for order in orders]
        for future in concurrent.futures.as_completed(futures):
            success, latency = future.result()
            latencies.append(latency)
            if success:
                success_count += 1

    wall_duration = time.perf_counter() - wall_start
    throughput = total_requests / wall_duration if wall_duration > 0 else 0

    print("📊 Benchmark Results:")
    print(f"  • Total Requests:  {total_requests}")
    print(f"  • Success Rate:    {success_count}/{total_requests} ({(success_count/total_requests)*100:.1f}%)")
    print(f"  • Total Time:      {wall_duration:.2f}s")
    print(f"  • Throughput:      {throughput:.1f} req/sec")
    if latencies:
        print(f"  • Avg Latency:     {(sum(latencies)/len(latencies))*1000:.1f} ms")
        print(f"  • Min Latency:     {min(latencies)*1000:.1f} ms")
        print(f"  • Max Latency:     {max(latencies)*1000:.1f} ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event Ingestion Load Benchmarker")
    parser.add_argument("--endpoint", default="http://localhost:4566/restapis/orders", help="Target API URL")
    parser.add_argument("--requests", type=int, default=50, help="Total requests to fire")
    parser.add_argument("--concurrency", type=int, default=5, help="Concurrent workers")
    args = parser.parse_args()

    run_benchmark(args.endpoint, args.requests, args.concurrency)
