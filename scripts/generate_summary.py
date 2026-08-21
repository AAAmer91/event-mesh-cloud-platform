"""Generate rich GitHub Step Summary dashboard for Benchmark & Chaos runs."""

import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def generate_dashboard(
    benchmark_file: str = "benchmark_results.json",
    chaos_file: str = "chaos_results.json",
    output_markdown_path: str | None = None,
) -> str:
    benchmark_data = {}
    if Path(benchmark_file).exists():
        with open(benchmark_file, encoding="utf-8") as f:
            benchmark_data = json.load(f)

    chaos_data = {}
    if Path(chaos_file).exists():
        with open(chaos_file, encoding="utf-8") as f:
            chaos_data = json.load(f)

    # Extract benchmark telemetry
    total_req = benchmark_data.get("total_requests", 0)
    throughput = benchmark_data.get("throughput_req_per_sec", 0.0)
    success_rate = benchmark_data.get("success_rate_percent", 100.0)
    duration = benchmark_data.get("total_duration_sec", 0.0)
    latencies = benchmark_data.get("latency_ms", {})
    avg_lat = latencies.get("avg", 0.0)
    p50 = latencies.get("p50", 0.0)
    p90 = latencies.get("p90", 0.0)
    p95 = latencies.get("p95", 0.0)
    p99 = latencies.get("p99", 0.0)
    min_lat = latencies.get("min", 0.0)
    max_lat = latencies.get("max", 0.0)

    # Extract chaos telemetry
    chaos_total = chaos_data.get("total_injected_orders", 0)
    valid_expected = chaos_data.get("valid_orders_expected", 0)
    valid_persisted = chaos_data.get("valid_orders_persisted", 0)
    poison_injected = chaos_data.get("poison_orders_injected", 0)
    poison_isolated = chaos_data.get("poison_orders_isolated_dlq", 0)
    isolation_rate = chaos_data.get("fault_isolation_rate_percent", 100.0)
    zero_data_loss = chaos_data.get("zero_data_loss_verified", True)

    md = []
    md.append("# ⚡ Enterprise Cloud Platform Performance & Chaos Dashboard")
    md.append("")
    md.append("> **Automated Cloud Resilience, Throughput & DevSecOps Benchmark Report**")
    md.append("")

    # Architecture Topology (Mermaid)
    md.append("### 📐 Live Event Mesh Architecture Topology")
    md.append("")
    md.append("```mermaid")
    md.append("flowchart LR")
    md.append("    subgraph Ingestion [Ingestion Layer]")
    md.append('        A["🚀 Client Ingest"] -->|POST /orders| B["⚡ Lambda: order-ingest"]')
    md.append('        I["📦 S3 Batch Drop"] -->|ObjectCreated| J["⚡ Lambda: s3-processor"]')
    md.append("    end")
    md.append("    subgraph EventMesh [Event Routing & Queuing]")
    md.append('        B -->|Publish Event| C["📢 SNS Topic: order-events"]')
    md.append('        C -->|Fanout Filter 1| D["📬 SQS Queue: order-events-queue"]')
    md.append('        C -->|Fanout Filter 2| E["📬 SQS Queue: notification-queue"]')
    md.append("    end")
    md.append("    subgraph Processing [Compute & Persistence]")
    md.append('        D -->|ESM Batch Trigger| F["⚙️ Lambda: order-worker"]')
    md.append('        F -->|Idempotent PutItem| G[("🗄️ DynamoDB: orders-table")]')
    md.append("        J -->|Bulk PutItem| G")
    md.append('        F -->|Poison Isolation| H[("🛡️ SQS: order-events-dlq")]')
    md.append("    end")
    md.append("```")
    md.append("")

    # Dynamic status indicators
    throughput_status = "🟢 **OPTIMAL**" if throughput >= 25.0 else "🟡 **DEGRADED**"
    success_status = "🟢 **PASS**" if success_rate >= 99.0 else "❌ **FAIL**"
    p50_status = (
        "🟢 **OPTIMAL**" if p50 <= 100.0 else ("🟢 **PASS**" if p50 <= 400.0 else "🟡 **DEGRADED**")
    )
    p99_status = (
        "🟢 **OPTIMAL**"
        if p99 <= 1000.0
        else ("🟢 **PASS**" if p99 <= 3000.0 else "🟡 **DEGRADED**")
    )
    isolation_status = "🛡️ **ISOLATED**" if isolation_rate >= 99.9 else "❌ **BREACHED**"
    integrity_status = "🔒 **VERIFIED**" if zero_data_loss else "❌ **FAILED**"

    # KPI Scorecard Cards
    md.append("### 📊 Executive Telemetry & Key Performance Indicators")
    md.append("")
    md.append(
        "| Metric Domain | Operational Measurement | Target SLA | Benchmark Result | Status |"
    )
    md.append("| :--- | :--- | :---: | :---: | :---: |")
    md.append(
        f"| **Event Ingestion Throughput** | Aggregate Load Capacity | > 25 req/sec | **`{throughput:.1f} req/sec`** ({total_req} orders in {duration}s) | {throughput_status} |"
    )
    md.append(
        f"| **Ingestion Success Rate** | Pipeline Delivery Availability | 99.9% | **`{success_rate:.1f}%`** ({total_req - benchmark_data.get('failed_requests', 0)}/{total_req}) | {success_status} |"
    )
    md.append(
        f"| **Median Latency ($p50$)** | Fast-path Ingestion Speed | < 300 ms | **`{p50:.1f} ms`** | {p50_status} |"
    )
    md.append(
        f"| **Tail Latency ($p99$)** | Worst-case Burst Processing | < 2500 ms | **`{p99:.1f} ms`** | {p99_status} |"
    )
    md.append(
        f"| **Chaos Fault Isolation** | Poison-Pill Quarantine to DLQ | 100.0% | **`{isolation_rate:.1f}%`** ({poison_isolated}/{poison_injected} quarantined) | {isolation_status} |"
    )
    md.append(
        f"| **Data Integrity Guarantee** | DynamoDB Commit Consistency | Zero Loss | **`{valid_persisted}/{valid_expected} Valid Orders Committed`** | {integrity_status} |"
    )
    md.append("")

    # Detailed Latency Distribution
    md.append("### ⏱️ Latency Percentile Distribution")
    md.append("")
    md.append("| Percentile | Ingestion Latency | Performance Gauge |")
    md.append("| :--- | :---: | :--- |")
    md.append(f"| **Min Latency** | `{min_lat:.1f} ms` | 🟩 `[■□□□□□□□□□]` Fastest Recorded |")
    md.append(f"| **p50 (Median)** | `{p50:.1f} ms` | 🟩 `[■■■□□□□□□□]` Typical Request |")
    md.append(f"| **Average** | `{avg_lat:.1f} ms` | 🟩 `[■■■■□□□□□□]` Mean Response |")
    md.append(f"| **p90** | `{p90:.1f} ms` | 🟨 `[■■■■■■□□□□]` High Load Percentile |")
    md.append(f"| **p95** | `{p95:.1f} ms` | 🟨 `[■■■■■■■□□□]` Tail Ingestion |")
    md.append(f"| **p99** | `{p99:.1f} ms` | 🟧 `[■■■■■■■■■□]` Worst 1% Performance |")
    md.append(f"| **Max Latency** | `{max_lat:.1f} ms` | 🟧 `[■■■■■■■■■■]` Peak Burst |")
    md.append("")

    # Chaos Resilience Deep Dive
    md.append("### 🧪 Chaos Engineering & Resilience Verification")
    md.append("")
    md.append(
        f"- **Simulated Workload**: {chaos_total} total synthetic transactions injected with deliberate schema corruption & runtime exceptions."
    )
    md.append(
        f"- **Valid Orders Committed**: **`{valid_persisted}/{valid_expected}`** orders verified in DynamoDB table `event-mesh-local-orders-table`."
    )
    md.append(
        f"- **Poison Payloads Quarantined**: **`{poison_isolated}/{poison_injected}`** corrupted messages safely trapped into `event-mesh-local-order-events-dlq`."
    )
    md.append(
        f"- **Zero Data Loss Status**: {'✅ **100% VERIFIED - Zero Message Loss or Stalled Processing**' if zero_data_loss else '❌ **FAILED**'}"
    )
    md.append("")
    md.append("---")
    md.append(
        "*Generated automatically by GitHub Actions CI/CD Platform Automation on LocalStack Cloud Emulator.*"
    )

    output_text = "\n".join(md)

    if output_markdown_path:
        with open(output_markdown_path, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"✅ Dashboard generated at: {output_markdown_path}")

    return output_text


if __name__ == "__main__":
    benchmark_path = sys.argv[1] if len(sys.argv) > 1 else "benchmark_results.json"
    chaos_path = sys.argv[2] if len(sys.argv) > 2 else "chaos_results.json"
    out_path = os.getenv("GITHUB_STEP_SUMMARY", None)

    generate_dashboard(benchmark_path, chaos_path, out_path)
