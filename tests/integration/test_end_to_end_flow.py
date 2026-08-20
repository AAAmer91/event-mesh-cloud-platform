"""End-to-End Integration Tests against LocalStack / AWS."""

import json
import time
import uuid

import boto3
import pytest

from src.handlers import order_ingest, order_worker


@pytest.mark.integration
def test_end_to_end_order_flow(localstack_endpoint):
    """Verifies complete flow: Ingest Order -> SNS Topic -> SQS Queue -> Worker -> DynamoDB."""
    sqs = boto3.client("sqs", endpoint_url=localstack_endpoint, region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", endpoint_url=localstack_endpoint, region_name="us-east-1")

    order_id = f"ord_e2e_{uuid.uuid4().hex[:8]}"
    customer_id = "cust_e2e_vip"

    payload = {
        "order_id": order_id,
        "customer_id": customer_id,
        "items": [
            {
                "item_id": "item_compute_1",
                "name": "EC2 c6g.xlarge",
                "quantity": 1,
                "unit_price": 136.0,
            },
        ],
        "currency": "USD",
    }

    # Step 1: Ingest order
    ingest_event = {"body": json.dumps(payload)}
    ingest_res = order_ingest.handler(ingest_event)
    assert ingest_res["statusCode"] == 201

    # Step 2: Poll SQS for message delivered via SNS fanout
    queue_url_res = sqs.get_queue_url(QueueName="event-mesh-local-order-events-queue")
    queue_url = queue_url_res["QueueUrl"]

    messages = []
    for _ in range(10):
        recv_res = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=2,
        )
        messages = recv_res.get("Messages", [])
        if messages:
            break
        time.sleep(0.5)

    assert len(messages) > 0, "No message received in SQS order queue from SNS topic"
    msg = messages[0]

    # Step 3: Trigger order worker Lambda with received SQS message
    worker_event = {
        "Records": [
            {
                "messageId": msg["MessageId"],
                "body": msg["Body"],
            }
        ]
    }
    worker_res = order_worker.handler(worker_event)
    assert worker_res["batchItemFailures"] == []

    # Step 4: Delete message from queue
    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"])

    # Step 5: Query DynamoDB for order record
    table = dynamodb.Table("event-mesh-local-orders-table")
    scan_res = table.scan(
        FilterExpression="order_id = :oid",
        ExpressionAttributeValues={":oid": order_id},
    )

    items = scan_res.get("Items", [])
    assert len(items) == 1
    assert items[0]["order_id"] == order_id
    assert items[0]["customer_id"] == customer_id
    assert items[0]["status"] == "PROCESSED"
