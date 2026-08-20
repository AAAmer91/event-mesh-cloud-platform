"""Distributed Tracing & Context Propagation Helper."""

from __future__ import annotations

import uuid
from typing import Any


class TraceContext:
    """Manages distributed trace correlation across API Gateway, SNS, and SQS."""

    def __init__(self, trace_id: str | None = None, parent_span_id: str | None = None):
        self.trace_id = trace_id or f"trace_{uuid.uuid4().hex}"
        self.span_id = f"span_{uuid.uuid4().hex[:16]}"
        self.parent_span_id = parent_span_id

    def inject_sns_attributes(self, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
        """Injects trace IDs into SNS MessageAttributes for propagation across fanout queues."""
        attrs = attributes or {}
        attrs["TraceID"] = {"DataType": "String", "StringValue": self.trace_id}
        attrs["SpanID"] = {"DataType": "String", "StringValue": self.span_id}
        return attrs

    @classmethod
    def extract_from_event(cls, event: dict[str, Any]) -> TraceContext:
        """Extracts trace correlation IDs from incoming API Gateway or SQS events."""
        # Check API Gateway headers (e.g. x-amzn-trace-id or x-trace-id)
        headers = event.get("headers", {})
        if isinstance(headers, dict):
            trace_header = headers.get("x-trace-id") or headers.get("x-amzn-trace-id")
            if trace_header:
                return cls(trace_id=trace_header)

        # Check direct payload
        body = event.get("body")
        if isinstance(body, dict) and "trace_id" in body:
            return cls(trace_id=body["trace_id"])

        return cls()
