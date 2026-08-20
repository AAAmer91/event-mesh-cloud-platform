"""End-to-End Integration Tests against LocalStack Cloud Infrastructure."""

import json
import os
import time
import uuid

import boto3
import pytest

from src.handlers import order_ingest, order_worker, s3_processor


@pytest.mark.integration
def test_end_to_end_order_flow(localstack_endpoint):
    """Verifies complete flow: Ingest Order -> SNS Topic -> SQS Queue -> Worker -> DynamoDB."""
    sns = boto3.client("sns", endpoint_url=localstack_endpoint, region_name="us-east-1")
    sqs = boto3.client("sqs", endpoint_url=localstack_endpoint, region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", endpoint_url=localstack_endpoint, region_name="us-east-1")

    # Configure environment for LocalStack
    topic_res = sns.create_topic(Name="event-mesh-local-order-events-topic")
    topic_arn = topic_res["TopicArn"]
    os.environ["SNS_TOPIC_ARN"] = topic_arn
    os.environ["DYNAMODB_TABLE_NAME"] = "event-mesh-local-orders-table"
    os.environ["AWS_ENDPOINT_URL"] = localstack_endpoint

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

    # Step 2: Resolve Queue URL and Poll SQS for message delivered via SNS fanout
    raw_url = sqs.get_queue_url(QueueName="event-mesh-local-order-events-queue")["QueueUrl"]
    # Normalize queue URL for localhost endpoint compatibility
    path_suffix = raw_url.split("/", 3)[-1] if raw_url.count("/") >= 3 else raw_url
    queue_url = f"{localstack_endpoint.rstrip('/')}/{path_suffix}"

    messages = []
    for _ in range(15):
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


@pytest.mark.integration
def test_s3_batch_ingestion_flow(localstack_endpoint):
    """Verifies S3 object creation event processing and bulk DynamoDB batch insert."""
    s3 = boto3.client("s3", endpoint_url=localstack_endpoint, region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", endpoint_url=localstack_endpoint, region_name="us-east-1")

    bucket_name = "event-mesh-local-event-ingestion-payloads"
    order_id_1 = f"ord_s3_{uuid.uuid4().hex[:8]}"
    order_id_2 = f"ord_s3_{uuid.uuid4().hex[:8]}"

    batch_payload = [
        {
            "order_id": order_id_1,
            "customer_id": "cust_batch_101",
            "items": [{"item_id": "i1", "name": "Storage", "quantity": 1, "unit_price": 50.0}],
            "total_amount": 50.0,
            "currency": "USD",
            "status": "PENDING",
            "created_at": "2026-08-20T22:00:00Z",
        },
        {
            "order_id": order_id_2,
            "customer_id": "cust_batch_102",
            "items": [{"item_id": "i2", "name": "Bandwidth", "quantity": 2, "unit_price": 25.0}],
            "total_amount": 50.0,
            "currency": "USD",
            "status": "PENDING",
            "created_at": "2026-08-20T22:00:00Z",
        },
    ]

    key = f"incoming/batch_{uuid.uuid4().hex[:6]}.json"
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(batch_payload),
        ContentType="application/json",
    )

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

    os.environ["DYNAMODB_TABLE_NAME"] = "event-mesh-local-orders-table"
    os.environ["AWS_ENDPOINT_URL"] = localstack_endpoint
    res = s3_processor.handler(s3_event)

    assert res["statusCode"] == 200
    res_body = json.loads(res["body"])
    assert res_body["processed_records"] == 2

    # Verify both records were persisted to DynamoDB
    table = dynamodb.Table("event-mesh-local-orders-table")
    item1 = table.get_item(Key={"order_id": order_id_1, "created_at": "2026-08-20T22:00:00Z"})
    assert "Item" in item1
    assert item1["Item"]["status"] == "PROCESSED"
