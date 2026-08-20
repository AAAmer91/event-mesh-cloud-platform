"""Order Ingestion API Gateway Lambda Handler."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3
from pydantic import BaseModel, Field, ValidationError

from src.core.logger import get_logger
from src.core.metrics import CloudWatchMetrics

logger = get_logger("order-ingest")
metrics = CloudWatchMetrics()


class OrderItem(BaseModel):
    """Model for an individual item in an order."""

    item_id: str
    name: str
    quantity: int = Field(gt=0, description="Quantity must be greater than zero")
    unit_price: float = Field(gt=0.0, description="Price must be positive")


class OrderPayload(BaseModel):
    """Model for incoming order payload."""

    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    currency: str = "USD"
    order_id: str | None = None
    trace_id: str | None = None


def get_sns_client() -> Any:
    """Returns a boto3 SNS client configured with local endpoint if available."""
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    return boto3.client("sns", endpoint_url=endpoint_url)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """Handles HTTP POST /orders requests, validates schema, and publishes to SNS."""
    trace_id = str(uuid.uuid4())
    logger.info("Received order ingestion request", extra={"extra_data": {"trace_id": trace_id}})

    # Extract body from API Gateway proxy event or direct invocation
    body_raw = event.get("body", event)
    if isinstance(body_raw, str):
        try:
            body = json.loads(body_raw)
        except json.JSONDecodeError as err:
            logger.error("Invalid JSON payload received", extra={"extra_data": {"error": str(err)}})
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Malformed JSON payload", "trace_id": trace_id}),
            }
    else:
        body = body_raw

    # Validate Schema with Pydantic
    try:
        order = OrderPayload.model_validate(body)
    except ValidationError as val_err:
        logger.warning("Order validation failed", extra={"extra_data": {"errors": val_err.errors()}})
        metrics.put_metric("OrderValidationErrors", 1.0)
        return {
            "statusCode": 422,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Validation failed", "details": val_err.errors()}),
        }

    # Generate Order Metadata
    order_id = order.order_id or f"ord_{uuid.uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()
    total_amount = sum(item.quantity * item.unit_price for item in order.items)

    order_event = {
        "event_type": "OrderCreated",
        "order_id": order_id,
        "customer_id": order.customer_id,
        "items": [item.model_dump() for item in order.items],
        "total_amount": round(total_amount, 2),
        "currency": order.currency,
        "status": "PENDING",
        "created_at": created_at,
        "trace_id": trace_id,
    }

    # Publish to SNS Event Mesh Topic
    sns_topic_arn = os.getenv("SNS_TOPIC_ARN")
    if not sns_topic_arn:
        logger.error("SNS_TOPIC_ARN environment variable is not configured")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Server misconfiguration", "trace_id": trace_id}),
        }

    sns = get_sns_client()
    try:
        sns_response = sns.publish(
            TopicArn=sns_topic_arn,
            Message=json.dumps(order_event),
            Subject="OrderCreated",
            MessageAttributes={
                "EventType": {"DataType": "String", "StringValue": "OrderCreated"},
                "CustomerID": {"DataType": "String", "StringValue": order.customer_id},
                "TraceID": {"DataType": "String", "StringValue": trace_id},
            },
        )
        message_id = sns_response.get("MessageId", "unknown")
        logger.info(
            "Order event published to SNS successfully",
            extra={"extra_data": {"order_id": order_id, "sns_message_id": message_id}},
        )
        metrics.put_metric("OrdersIngested", 1.0)

        return {
            "statusCode": 201,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "message": "Order accepted for processing",
                    "order_id": order_id,
                    "status": "PENDING",
                    "total_amount": total_amount,
                    "trace_id": trace_id,
                    "created_at": created_at,
                }
            ),
        }

    except Exception as exc:
        logger.error(
            "Failed to publish order event to SNS",
            extra={"extra_data": {"order_id": order_id, "error": str(exc)}},
        )
        metrics.put_metric("SNSOrderPublishFailures", 1.0)
        return {
            "statusCode": 502,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Failed to publish event to message bus", "trace_id": trace_id}),
        }
