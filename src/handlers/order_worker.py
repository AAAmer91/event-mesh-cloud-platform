"""Order Worker SQS Consumer Lambda Handler (Idempotent DynamoDB Persistence)."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.core.logger import get_logger
from src.core.metrics import CloudWatchMetrics

logger = get_logger("order-worker")
metrics = CloudWatchMetrics()


def get_dynamodb_resource() -> Any:
    """Returns a boto3 DynamoDB resource configured with local endpoint if available."""
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    return boto3.resource("dynamodb", endpoint_url=endpoint_url)


def parse_sqs_body(record_body: str) -> dict[str, Any]:
    """Parses SQS message body, unwrapping SNS envelope if present."""
    data = json.loads(record_body)
    if isinstance(data, dict) and "TopicArn" in data and "Message" in data:
        # Message was routed through SNS -> SQS fanout
        return json.loads(data["Message"])
    return data


def process_single_order(order_data: dict[str, Any], table: Any) -> bool:
    """Processes a single order with idempotent DynamoDB write."""
    order_id = order_data["order_id"]
    customer_id = order_data["customer_id"]
    created_at = order_data["created_at"]
    processed_at = datetime.now(timezone.utc).isoformat()

    # Simulate deliberate failure for DLQ resilience testing
    if order_data.get("simulate_error") is True:
        logger.error(
            "Simulating processing failure as requested in payload",
            extra={"extra_data": {"order_id": order_id}},
        )
        raise ValueError(f"Simulated processing error for order: {order_id}")

    # Convert floats to Decimals for DynamoDB
    total_amount = Decimal(str(order_data.get("total_amount", 0.0)))

    item = {
        "order_id": order_id,
        "created_at": created_at,
        "customer_id": customer_id,
        "status": "PROCESSED",
        "total_amount": total_amount,
        "currency": order_data.get("currency", "USD"),
        "items": order_data.get("items", []),
        "processed_at": processed_at,
        "trace_id": order_data.get("trace_id", "none"),
    }

    try:
        # Idempotent write: write only if order hasn't already been processed
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(order_id)",
        )
        logger.info(
            "Order successfully persisted to DynamoDB",
            extra={"extra_data": {"order_id": order_id, "customer_id": customer_id}},
        )
        metrics.put_metric("OrdersProcessed", 1.0)
        return True

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            logger.warning(
                "Order already processed (idempotent duplicate ignored)",
                extra={"extra_data": {"order_id": order_id}},
            )
            metrics.put_metric("DuplicateOrdersIgnored", 1.0)
            return True
        else:
            logger.error(
                "DynamoDB write error",
                extra={"extra_data": {"order_id": order_id, "error": str(e)}},
            )
            raise


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Processes a batch of SQS messages and reports partial batch failures."""
    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    if not table_name:
        raise RuntimeError("DYNAMODB_TABLE_NAME environment variable is not configured")

    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(table_name)

    batch_item_failures: list[dict[str, str]] = []
    records = event.get("Records", [])

    logger.info(f"Processing batch of {len(records)} SQS message(s)")

    for record in records:
        message_id = record.get("messageId", "unknown")
        try:
            order_data = parse_sqs_body(record["body"])
            process_single_order(order_data, table)
        except Exception as exc:
            logger.error(
                f"Failed to process SQS message {message_id}: {exc}",
                extra={"extra_data": {"message_id": message_id, "error": str(exc)}},
            )
            metrics.put_metric("OrderWorkerFailures", 1.0)
            # Add to batch failures so SQS only retries failed messages
            batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
