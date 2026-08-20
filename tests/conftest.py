"""Pytest Configuration and Fixtures for Unit and LocalStack Integration Tests."""

import os
import pytest
import boto3
from moto import mock_aws

# Set test environment variables before importing app modules
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["SNS_TOPIC_ARN"] = "arn:aws:sns:us-east-1:000000000000:test-order-topic"
os.environ["DYNAMODB_TABLE_NAME"] = "test-orders-table"


@pytest.fixture(scope="session")
def localstack_endpoint():
    """Returns the LocalStack endpoint URL (defaults to http://localhost:4566)."""
    return os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")


@pytest.fixture
def mocked_aws():
    """Fixture providing in-memory AWS mocking via moto for fast unit tests."""
    with mock_aws():
        yield


@pytest.fixture
def moto_sns(mocked_aws):
    """Provides a mocked SNS client and test topic."""
    sns = boto3.client("sns", region_name="us-east-1")
    topic = sns.create_topic(Name="test-order-topic")
    os.environ["SNS_TOPIC_ARN"] = topic["TopicArn"]
    return sns, topic["TopicArn"]


@pytest.fixture
def moto_dynamodb(mocked_aws):
    """Provides a mocked DynamoDB resource and test orders table."""
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="test-orders-table",
        KeySchema=[
            {"AttributeName": "order_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "order_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return dynamodb, table


@pytest.fixture
def moto_s3(mocked_aws):
    """Provides a mocked S3 client and test bucket."""
    s3 = boto3.client("s3", region_name="us-east-1")
    bucket_name = "test-ingestion-bucket"
    s3.create_bucket(Bucket=bucket_name)
    return s3, bucket_name
