"""Render the persistent performance evidence site."""

from __future__ import annotations

import argparse
import html
import json
import os
import time
from pathlib import Path
from typing import Any


def append_history(
    history: list[dict[str, Any]], entry: dict[str, Any], *, limit: int = 90
) -> list[dict[str, Any]]:
    run_id = str(entry.get("run_id", ""))
    updated = [item for item in history if str(item.get("run_id", "")) != run_id]
    updated.append(entry)
    return updated[-limit:]


def render_site(history: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    latest = history[-1] if history else {}
    benchmark = latest.get("benchmark", {})
    chaos = latest.get("chaos", {})
    latency = benchmark.get("latency_ms", {})
    passed = latest.get("passed") is True
    status = "PASS" if passed else "FAIL"
    status_class = "pass" if passed else "fail"
    sha = html.escape(str(latest.get("sha", "unknown"))[:7])
    timestamp = html.escape(str(latest.get("timestamp", "No evidence published")))
    throughput = float(benchmark.get("throughput_req_per_sec", 0.0))
    success_rate = float(benchmark.get("success_rate_percent", 0.0))
    p50 = float(latency.get("p50", 0.0))
    p99 = float(latency.get("p99", 0.0))
    isolation = float(chaos.get("fault_isolation_rate_percent", 0.0))
    integrity = "Verified" if chaos.get("zero_data_loss_verified") is True else "Failed"
    rows = "\n".join(
        f"<tr><td>{html.escape(str(item.get('timestamp', '')))}</td>"
        f"<td><code>{html.escape(str(item.get('sha', ''))[:7])}</code></td>"
        f"<td>{float(item.get('benchmark', {}).get('throughput_req_per_sec', 0.0)):.1f}</td>"
        f"<td>{float(item.get('benchmark', {}).get('latency_ms', {}).get('p99', 0.0)):.1f}</td>"
        f"<td>{'✅ PASS' if item.get('passed') is True else '❌ FAIL'}</td></tr>"
        for item in reversed(history[-20:])
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Event Mesh Delivery Evidence</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    body {{ max-width: 1120px; margin: 0 auto; padding: 2rem; background: #08111f; color: #dbeafe; }}
    header {{ display: flex; justify-content: space-between; gap: 2rem; align-items: end; border-bottom: 1px solid #24344d; padding-bottom: 1.5rem; }}
    h1 {{ margin: 0; font-size: clamp(2rem, 6vw, 4rem); }}
    .muted {{ color: #93a4bd; }} .status {{ border-radius: 999px; padding: .5rem 1rem; font-weight: 800; }}
    .pass {{ background: #064e3b; color: #6ee7b7; }} .fail {{ background: #5f1423; color: #fda4af; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; margin: 2rem 0; }}
    .card {{ background: #101c2f; border: 1px solid #24344d; border-radius: 14px; padding: 1.2rem; }}
    .metric {{ font-size: 1.8rem; font-weight: 800; margin-top: .35rem; color: #7dd3fc; }}
    table {{ width: 100%; border-collapse: collapse; background: #101c2f; border-radius: 14px; overflow: hidden; }}
    th, td {{ padding: .85rem; text-align: left; border-bottom: 1px solid #24344d; }} th {{ color: #7dd3fc; }}
    canvas {{ width: 100%; height: 260px; background: #101c2f; border: 1px solid #24344d; border-radius: 14px; margin: 1rem 0 2rem; }}
  </style>
</head>
<body>
  <header><div><p class="muted">GitHub Actions · LocalStack · Terraform</p><h1>Delivery Evidence</h1><p class="muted">Latest run {timestamp} · commit <code>{sha}</code></p></div><span class="status {status_class}">{status}</span></header>
  <section class="grid">
    <article class="card"><span class="muted">Throughput</span><div class="metric">{throughput:.1f} req/s</div></article>
    <article class="card"><span class="muted">Success rate</span><div class="metric">{success_rate:.1f}%</div></article>
    <article class="card"><span class="muted">p50 latency</span><div class="metric">{p50:.1f} ms</div></article>
    <article class="card"><span class="muted">p99 latency</span><div class="metric">{p99:.1f} ms</div></article>
    <article class="card"><span class="muted">Fault isolation</span><div class="metric">{isolation:.1f}%</div></article>
    <article class="card"><span class="muted">Data integrity</span><div class="metric">{integrity}</div></article>
  </section>
  <h2>Throughput trend</h2><canvas id="trend" width="1080" height="260"></canvas>
  <h2>Recent evidence</h2>
  <table><thead><tr><th>Timestamp</th><th>Commit</th><th>req/s</th><th>p99 ms</th><th>Gate</th></tr></thead><tbody>{rows}</tbody></table>
  <script>
    fetch('history.json').then(r => r.json()).then(history => {{
      const canvas = document.getElementById('trend'); const ctx = canvas.getContext('2d');
      const values = history.map(x => Number(x.benchmark?.throughput_req_per_sec || 0));
      if (values.length < 2) return; const max = Math.max(...values, 1); const pad = 30;
      ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 3; ctx.beginPath();
      values.forEach((value, index) => {{ const x = pad + index * (canvas.width - pad * 2) / (values.length - 1); const y = canvas.height - pad - value * (canvas.height - pad * 2) / max; index ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }});
      ctx.stroke();
    }});
  </script>
</body>
</html>"""
    (output_dir / "index.html").write_text(document, encoding="utf-8")


def _load_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update and render performance evidence")
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--chaos", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    existing = []
    if arguments.history.is_file():
        loaded = json.loads(arguments.history.read_text(encoding="utf-8"))
        existing = loaded if isinstance(loaded, list) else []
    validation = _load_object(arguments.validation)
    new_entry = {
        "run_id": os.getenv("GITHUB_RUN_ID", str(time.time_ns())),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sha": os.getenv("GITHUB_SHA", "local"),
        "run_url": os.getenv("GITHUB_SERVER_URL", "https://github.com")
        + "/"
        + os.getenv("GITHUB_REPOSITORY", "local/event-mesh")
        + "/actions/runs/"
        + os.getenv("GITHUB_RUN_ID", "local"),
        "passed": validation.get("passed") is True,
        "benchmark": _load_object(arguments.benchmark),
        "chaos": _load_object(arguments.chaos),
        "validation": validation,
    }
    updated_history = append_history(existing, new_entry)
    arguments.history.parent.mkdir(parents=True, exist_ok=True)
    arguments.history.write_text(json.dumps(updated_history, indent=2) + "\n", encoding="utf-8")
    render_site(updated_history, arguments.output_dir)
