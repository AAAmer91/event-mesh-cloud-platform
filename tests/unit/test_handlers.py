"""Unit Tests for Lambda Handlers, Logger, and Metrics."""

import json
from decimal import Decimal
import pytest

from src.handlers import order_ingest, order_worker, s3_processor
from src.core.logger import get_logger
from src.core.metrics import CloudWatchMetrics


@pytest.mark.unit
def test_order_ingest_happy_path(moto_sns):
    """Test successful order ingestion and SNS publishing."""
    sns_client, topic_arn = moto_sns

    payload = {
        "customer_id": "cust_12345",
        "items": [
            {"item_id": "item_1", "name": "Cloud Server Instance", "quantity": 2, "unit_price": 50.0},
            {"item_id": "item_2", "name": "Load Balancer", "quantity": 1, "unit_price": 25.0},
        ],
        "currency": "USD",
    }

    event = {"body": json.dumps(payload)}
    response = order_ingest.handler(event)

    assert response["statusCode"] == 201
    body = json.loads(response["body"])
    assert body["status"] == "PENDING"
    assert body["total_amount"] == 125.0
    assert "order_id" in body
    assert "trace_id" in body


@pytest.mark.unit
def test_order_ingest_malformed_json():
    """Test response when payload contains invalid JSON."""
    event = {"body": "{invalid-json-content"}
    response = order_ingest.handler(event)

    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "Malformed JSON" in body["error"]


@pytest.mark.unit
def test_order_ingest_validation_failure():
    """Test response when required fields are missing or invalid."""
    # Empty items list and negative quantity
    payload = {
        "customer_id": "cust_12345",
        "items": [],
    }

    event = {"body": json.dumps(payload)}
    response = order_ingest.handler(event)

    assert response["statusCode"] == 422
    body = json.loads(response["body"])
    assert body["error"] == "Validation failed"


@pytest.mark.unit
def test_order_worker_processing(moto_dynamodb):
    """Test SQS order worker writing records to DynamoDB."""
    dynamodb, table = moto_dynamodb

    sqs_event = {
        "Records": [
            {
                "messageId": "msg_001",
                "body": json.dumps(
                    {
                        "order_id": "ord_unit_test_1",
                        "customer_id": "cust_999",
                        "total_amount": 99.99,
                        "currency": "USD",
                        "created_at": "2026-08-21T00:00:00Z",
                        "items": [{"item_id": "i1", "name": "Widget", "quantity": 1, "unit_price": 99.99}],
                    }
                ),
            }
        ]
    }

    response = order_worker.handler(sqs_event)
    assert response["batchItemFailures"] == []

    # Verify DynamoDB record
    db_record = table.get_item(
        Key={"order_id": "ord_unit_test_1", "created_at": "2026-08-21T00:00:00Z"}
    )
    assert "Item" in db_record
    assert db_record["Item"]["status"] == "PROCESSED"
    assert db_record["Item"]["total_amount"] == Decimal("99.99")


@pytest.mark.unit
def test_order_worker_idempotency(moto_dynamodb):
    """Test that duplicate SQS messages are idempotently ignored without error."""
    dynamodb, table = moto_dynamodb

    order_payload = {
        "order_id": "ord_duplicate_1",
        "customer_id": "cust_dup",
        "total_amount": 45.00,
        "created_at": "2026-08-21T00:00:00Z",
        "items": [],
    }

    sqs_event = {"Records": [{"messageId": "msg_dup_1", "body": json.dumps(order_payload)}]}

    # First delivery
    res1 = order_worker.handler(sqs_event)
    assert res1["batchItemFailures"] == []

    # Second delivery (duplicate retry)
    res2 = order_worker.handler(sqs_event)
    assert res2["batchItemFailures"] == []


@pytest.mark.unit
def test_order_worker_batch_failure_reporting(moto_dynamodb):
    """Test that failed messages are added to batchItemFailures for SQS redrive."""
    dynamodb, table = moto_dynamodb

    sqs_event = {
        "Records": [
            {
                "messageId": "msg_fail_1",
                "body": json.dumps(
                    {
                        "order_id": "ord_fail_1",
                        "customer_id": "cust_err",
                        "created_at": "2026-08-21T00:00:00Z",
                        "simulate_error": True,
                    }
                ),
            }
        ]
    }

    response = order_worker.handler(sqs_event)
    assert len(response["batchItemFailures"]) == 1
    assert response["batchItemFailures"][0]["itemIdentifier"] == "msg_fail_1"


@pytest.mark.unit
def test_s3_processor(moto_s3, moto_dynamodb):
    """Test S3 event processor reading JSON file and batch writing to DynamoDB."""
    s3, bucket_name = moto_s3
    dynamodb, table = moto_dynamodb

    # Upload test batch file to S3
    batch_data = [
        {"order_id": "s3_ord_1", "customer_id": "cust_s3_1", "total_amount": 10.0},
        {"order_id": "s3_ord_2", "customer_id": "cust_s3_2", "total_amount": 20.0},
    ]
    key = "uploads/orders_2026.json"
    s3.put_object(Bucket=bucket_name, Key=key, Body=json.dumps(batch_data))

    s3_event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": key},
                }
            }
        ]
    }

    response = s3_processor.handler(s3_event)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["processed_orders"] == 2


@pytest.mark.unit
def test_logger_and_metrics(mocked_aws):
    """Test structured logger and CloudWatch metrics formatting."""
    logger = get_logger("unit-test-logger")
    assert logger is not None

    metrics = CloudWatchMetrics()
    result = metrics.put_metric("TestMetric", 1.0)
    assert result is True
