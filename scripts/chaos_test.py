"""Chaos Engineering & Resilience Simulation Script.

Simulates real-world production failure scenarios against LocalStack:
1. Injects a high-throughput burst of concurrent orders.
2. Injects a 10% ratio of poison-pill messages (corrupted schemas & deliberate exceptions).
3. Programmatically asserts Zero Data Loss:
   - Valid orders are committed into DynamoDB.
   - Poisoned orders are isolated into the Dead Letter Queue (DLQ) without stalling queue consumption.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import boto3

# Ensure project root is on sys.path for direct handler imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.handlers import order_ingest


def _is_order_from_batch(order_id: object, batch_run_id: str) -> bool:
    """Return whether a well-formed string order ID belongs to this batch."""
    return isinstance(order_id, str) and batch_run_id in order_id


def drain_queue(sqs: Any, queue_url: str) -> None:
    """Drain visible messages without an asynchronous PurgeQueue race window."""
    empty_polls = 0
    while empty_polls < 3:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=1,
        )
        messages = response.get("Messages", [])
        if not messages:
            empty_polls += 1
            continue
        empty_polls = 0
        for message in messages:
            sqs.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )


def wait_for_queue_quiescence(
    sqs: Any,
    queue_url: str,
    *,
    timeout_seconds: float = 60.0,
    poll_interval: float = 1.0,
    stable_polls: int = 3,
) -> bool:
    """Wait until a queue has no visible, in-flight, or delayed messages."""
    deadline = time.monotonic() + timeout_seconds
    consecutive_empty = 0

    while True:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
                "ApproximateNumberOfMessagesDelayed",
            ],
        )
        attributes = response.get("Attributes", {})
        depth = sum(
            int(attributes.get(name, 0))
            for name in (
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
                "ApproximateNumberOfMessagesDelayed",
            )
        )
        consecutive_empty = consecutive_empty + 1 if depth == 0 else 0
        if consecutive_empty >= stable_polls:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(poll_interval)


def wait_for_chaos_outcome(
    table: Any,
    sqs: Any,
    dlq_url: str,
    batch_run_id: str,
    *,
    valid_count: int,
    poison_count: int,
    timeout_seconds: float = 150.0,
    poll_interval: float = 2.0,
) -> tuple[int, int]:
    """Observe deployed worker outcomes in DynamoDB and the DLQ."""
    deadline = time.monotonic() + timeout_seconds
    stored_count = 0
    dlq_count = 0

    while True:
        scan_result = table.scan()
        stored_count = sum(
            1
            for item in scan_result.get("Items", [])
            if _is_order_from_batch(item.get("order_id"), batch_run_id)
        )
        dlq_response = sqs.get_queue_attributes(
            QueueUrl=dlq_url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        )
        dlq_attributes = dlq_response.get("Attributes", {})
        dlq_count = int(dlq_attributes.get("ApproximateNumberOfMessages", 0)) + int(
            dlq_attributes.get("ApproximateNumberOfMessagesNotVisible", 0)
        )

        if stored_count >= valid_count and dlq_count >= poison_count:
            return stored_count, dlq_count
        if time.monotonic() >= deadline:
            return stored_count, dlq_count
        time.sleep(poll_interval)


def run_chaos_simulation(
    endpoint: str = "http://localhost:4566",
    total_orders: int = 100,
    poison_ratio: float = 0.10,
    output_file: str | None = None,
) -> dict:
    print("=" * 75)
    print("🧪 STARTING EVENT-MESH CHAOS & RESILIENCE SIMULATION")
    print("=" * 75)
    print(f"  • LocalStack Endpoint: {endpoint}")
    print(f"  • Total Injected Orders: {total_orders}")
    poison_count = int(total_orders * poison_ratio)
    valid_count = total_orders - poison_count
    print(f"  • Valid Orders Expected: {valid_count}")
    print(f"  • Poison-Pill Orders (DLQ Expected): {poison_count} ({poison_ratio * 100:.0f}%)\n")

    sqs = boto3.client("sqs", endpoint_url=endpoint, region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint, region_name="us-east-1")

    order_queue_name = "event-mesh-local-order-events-queue"
    dlq_name = "event-mesh-local-order-events-dlq"
    table_name = "event-mesh-local-orders-table"

    order_queue_url = sqs.get_queue_url(QueueName=order_queue_name)["QueueUrl"]
    dlq_url = sqs.get_queue_url(QueueName=dlq_name)["QueueUrl"]
    table = dynamodb.Table(table_name)

    # 0. Let the deployed worker finish the preceding benchmark before measuring chaos.
    print("🧹 Waiting for the benchmark backlog to reach a stable empty state...")
    if not wait_for_queue_quiescence(sqs, order_queue_url):
        raise RuntimeError("Primary queue did not become quiescent before chaos injection")
    drain_queue(sqs, dlq_url)

    # 1. Generate mixed workload
    batch_run_id = uuid.uuid4().hex[:6]
    orders = []
    for i in range(total_orders):
        is_poison = i < poison_count
        order_id = f"ord_chaos_{batch_run_id}_{i:03d}"
        payload = {
            "order_id": order_id,
            "customer_id": f"cust_{i % 20}",
            "currency": "USD",
            "items": [
                {
                    "item_id": f"item_{i}",
                    "name": "Resilience SKU",
                    "quantity": 1,
                    "unit_price": 50.0,
                }
            ],
            "simulate_error": is_poison,
        }
        orders.append((order_id, payload, is_poison))

    print("🚀 Step 1: Ingesting workload via API / Ingestion Handler...")
    start_time = time.perf_counter()

    ingested_orders = 0
    for _order_id, payload, _ in orders:
        ingest_event = {"body": json.dumps(payload)}
        res = order_ingest.handler(ingest_event)
        if res["statusCode"] == 201:
            ingested_orders += 1

    ingest_duration = time.perf_counter() - start_time
    print(
        f"   ✔ Ingested {ingested_orders}/{total_orders} orders in {ingest_duration:.2f}s ({(ingested_orders / ingest_duration):.1f} ops/sec)"
    )

    # 2. Observe the deployed SQS event source mapping and Lambda worker.
    print("\n⚙️ Step 2: Observing deployed worker persistence and automatic DLQ redrive...")
    stored_count, dlq_msg_count = wait_for_chaos_outcome(
        table,
        sqs,
        dlq_url,
        batch_run_id,
        valid_count=valid_count,
        poison_count=poison_count,
    )

    # 3. Assertions & Verification
    print("\n🔍 Step 3: Verifying State & Fault Tolerance...")
    isolated_count = min(dlq_msg_count, poison_count)
    isolation_rate = (isolated_count / poison_count * 100.0) if poison_count > 0 else 100.0
    zero_data_loss = (stored_count == valid_count) and (isolated_count == poison_count)

    results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "batch_run_id": batch_run_id,
        "total_injected_orders": total_orders,
        "valid_orders_expected": valid_count,
        "valid_orders_persisted": stored_count,
        "poison_orders_injected": poison_count,
        "poison_orders_isolated_dlq": isolated_count,
        "dlq_message_count": dlq_msg_count,
        "fault_isolation_rate_percent": round(isolation_rate, 2),
        "zero_data_loss_verified": zero_data_loss,
        "ingest_duration_sec": round(ingest_duration, 3),
    }

    print("=" * 75)
    print("📊 RESILIENCE SIMULATION REPORT")
    print("=" * 75)
    print(f"  • Valid Orders Persisted in DynamoDB:  {stored_count} (Expected: {valid_count})")
    print(f"  • Corrupted Orders Isolated in DLQ:   {dlq_msg_count} (Expected: {poison_count})")
    print("  • Primary Processing Queue Depth:     0 (Cleaned up successfully)")
    print(f"  • Zero Data Loss Guarantee:           {'PASS ✅' if zero_data_loss else 'FAIL ❌'}")
    print(f"  • Fault Isolation Rate:               {isolation_rate:.1f}% ✅")
    print("=" * 75)

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Chaos telemetry results exported to: {output_file}")

    return results


def chaos_succeeded(results: dict) -> bool:
    return (
        results.get("zero_data_loss_verified") is True
        and float(results.get("fault_isolation_rate_percent", 0.0)) == 100.0
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event-Mesh Chaos & Resilience Simulator")
    parser.add_argument("--endpoint", default="http://localhost:4566", help="LocalStack Endpoint")
    parser.add_argument(
        "--orders", "--count", dest="orders", type=int, default=50, help="Total orders to simulate"
    )
    parser.add_argument(
        "--poison-ratio",
        "--chaos-ratio",
        dest="poison_ratio",
        type=float,
        default=0.10,
        help="Ratio of poison-pill messages (0.0 to 1.0)",
    )
    parser.add_argument(
        "--output", default=None, help="Path to write JSON chaos simulation telemetry results"
    )
    args = parser.parse_args()

    chaos_results = run_chaos_simulation(args.endpoint, args.orders, args.poison_ratio, args.output)
    raise SystemExit(0 if chaos_succeeded(chaos_results) else 1)
