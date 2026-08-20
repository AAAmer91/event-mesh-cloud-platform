"""S3 Batch Ingestion Processor Lambda Handler."""

from __future__ import annotations

import json
import os
import urllib.parse
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3


from src.core.logger import get_logger
from src.core.metrics import CloudWatchMetrics

logger = get_logger("s3-processor")
metrics = CloudWatchMetrics()


def get_s3_client() -> Any:
    """Returns a boto3 S3 client configured with local endpoint if available."""
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    return boto3.client("s3", endpoint_url=endpoint_url)


def get_dynamodb_resource() -> Any:
    """Returns a boto3 DynamoDB resource configured with local endpoint if available."""
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    return boto3.resource("dynamodb", endpoint_url=endpoint_url)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Processes S3 ObjectCreated events, reads batch JSON files, and persists orders to DynamoDB."""
    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    if not table_name:
        raise RuntimeError("DYNAMODB_TABLE_NAME environment variable is not configured")

    s3 = get_s3_client()
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)

    processed_count = 0
    records = event.get("Records", [])

    for record in records:
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])

        logger.info(f"Processing S3 object s3://{bucket}/{key}")

        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
            payload = json.loads(content)

            # Support single order object or array of orders
            orders = payload if isinstance(payload, list) else [payload]

            with table.batch_writer() as batch:
                for order in orders:
                    order_id = order.get("order_id")
                    if not order_id:
                        continue

                    total_amount = Decimal(str(order.get("total_amount", 0.0)))
                    created_at = order.get("created_at", datetime.now(timezone.utc).isoformat())

                    item = {
                        "order_id": order_id,
                        "created_at": created_at,
                        "customer_id": order.get("customer_id", "unknown"),
                        "status": "BATCH_PROCESSED",
                        "total_amount": total_amount,
                        "currency": order.get("currency", "USD"),
                        "items": order.get("items", []),
                        "source_file": f"s3://{bucket}/{key}",
                        "processed_at": datetime.now(timezone.utc).isoformat(),
                    }
                    batch.put_item(Item=item)
                    processed_count += 1

            logger.info(f"Successfully processed {processed_count} order(s) from s3://{bucket}/{key}")
            metrics.put_metric("S3BatchOrdersProcessed", float(processed_count))

        except Exception as exc:
            logger.error(
                f"Failed to process S3 file s3://{bucket}/{key}: {exc}",
                extra={"extra_data": {"bucket": bucket, "key": key, "error": str(exc)}},
            )
            metrics.put_metric("S3BatchProcessingFailures", 1.0)
            raise

    return {
        "statusCode": 200,
        "body": json.dumps({"processed_orders": processed_count}),
    }
