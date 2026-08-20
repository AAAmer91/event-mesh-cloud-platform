"""S3 Batch Ingestion Integration Test."""

import json
import uuid
import boto3
import pytest

from src.handlers import s3_processor


@pytest.mark.integration
def test_s3_file_batch_ingestion(localstack_endpoint):
    """Verifies that an uploaded batch JSON file is parsed and stored in DynamoDB."""
    s3 = boto3.client("s3", endpoint_url=localstack_endpoint, region_name="us-east-1")
    dynamodb = boto3.resource("dynamodb", endpoint_url=localstack_endpoint, region_name="us-east-1")

    bucket_name = "event-mesh-local-event-ingestion-payloads"
    table_name = "event-mesh-local-orders-table"

    batch_order_id = f"ord_s3_{uuid.uuid4().hex[:8]}"
    batch_payload = [
        {
            "order_id": batch_order_id,
            "customer_id": "cust_bulk_importer",
            "total_amount": 1500.00,
            "currency": "USD",
            "created_at": "2026-08-21T01:00:00Z",
            "items": [{"item_id": "it_100", "name": "Bulk Storage", "quantity": 10, "unit_price": 150.0}],
        }
    ]

    key = f"batches/{uuid.uuid4().hex}/orders.json"
    s3.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(batch_payload),
    )

    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": key},
                }
            }
        ]
    }

    processor_res = s3_processor.handler(event)
    assert processor_res["statusCode"] == 200

    # Query DynamoDB
    table = dynamodb.Table(table_name)
    record = table.get_item(Key={"order_id": batch_order_id, "created_at": "2026-08-21T01:00:00Z"})
    assert "Item" in record
    assert record["Item"]["customer_id"] == "cust_bulk_importer"
    assert record["Item"]["status"] == "BATCH_PROCESSED"
