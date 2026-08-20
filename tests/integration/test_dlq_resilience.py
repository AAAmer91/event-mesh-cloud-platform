"""Dead Letter Queue (DLQ) Resilience Integration Test."""

import json
import uuid
import boto3
import pytest

from src.handlers import order_worker


@pytest.mark.integration
def test_dlq_redrive_on_repeated_failure(localstack_endpoint):
    """Verifies that an unprocessable message triggers batchItemFailure and can be routed to DLQ."""
    sqs = boto3.client("sqs", endpoint_url=localstack_endpoint, region_name="us-east-1")

    order_id = f"ord_dlq_{uuid.uuid4().hex[:8]}"

    # Send a poison-pill message directly to primary queue
    queue_url_res = sqs.get_queue_url(QueueName="event-mesh-local-order-events-queue")
    primary_queue_url = queue_url_res["QueueUrl"]

    corrupted_payload = {
        "order_id": order_id,
        "customer_id": "cust_bad_payload",
        "created_at": "2026-08-21T00:00:00Z",
        "simulate_error": True,
    }

    send_res = sqs.send_message(
        QueueUrl=primary_queue_url,
        MessageBody=json.dumps(corrupted_payload),
    )
    message_id = send_res["MessageId"]

    # Trigger worker
    event = {
        "Records": [
            {
                "messageId": message_id,
                "body": json.dumps(corrupted_payload),
            }
        ]
    }
    worker_res = order_worker.handler(event)

    # Worker must declare this item as a batch failure to allow SQS DLQ redrive
    assert len(worker_res["batchItemFailures"]) == 1
    assert worker_res["batchItemFailures"][0]["itemIdentifier"] == message_id
