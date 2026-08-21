"""CloudWatch Custom Metrics Emitter."""

from __future__ import annotations

import os
from typing import Any

import boto3
from botocore.config import Config

from src.core.logger import get_logger

logger = get_logger("metrics-emitter")


class CloudWatchMetrics:
    """Helper to emit custom CloudWatch metrics."""

    def __init__(self, namespace: str = "EventMeshPlatform/Orders", client: Any | None = None):
        self.namespace = namespace
        self._client = client

    @property
    def client(self) -> Any:
        """Lazily initialize boto3 CloudWatch client."""
        if self._client is None:
            endpoint_url = os.getenv("AWS_ENDPOINT_URL")
            config = Config(
                max_pool_connections=200,
                retries={"max_attempts": 0, "mode": "standard"},
                connect_timeout=1,
                read_timeout=1,
            )
            self._client = boto3.client(
                "cloudwatch", endpoint_url=endpoint_url, region_name="us-east-1", config=config
            )
        return self._client

    def put_metric(
        self,
        metric_name: str,
        value: float = 1.0,
        unit: str = "Count",
        dimensions: dict[str, str] | None = None,
    ) -> bool:
        """Publishes a single metric data point to CloudWatch."""
        dims = [{"Name": k, "Value": v} for k, v in (dimensions or {}).items()]
        environment = os.getenv("ENVIRONMENT", "local")
        dims.append({"Name": "Environment", "Value": environment})

        metric_data = {
            "MetricName": metric_name,
            "Value": value,
            "Unit": unit,
            "Dimensions": dims,
        }

        try:
            self.client.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data],
            )
            return True
        except Exception as e:
            logger.warning(
                f"Failed to publish metric {metric_name} to CloudWatch: {e}",
                extra={"extra_data": {"metric": metric_name, "error": str(e)}},
            )
            return False
