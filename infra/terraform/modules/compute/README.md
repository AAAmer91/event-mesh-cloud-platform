# Compute Module

This module connects the tested Lambda package to the event-processing resources. It creates three Python 3.11 functions, their execution role and policy, an SQS event source mapping, an S3 notification, and an optional API Gateway HTTP API.

## Responsibilities

- `order-ingest` handles `POST /orders` and publishes to the supplied SNS topic.
- `order-worker` consumes the order queue in batches of up to 10 and reports individual batch failures.
- `s3-processor` handles JSON object-created events from the supplied S3 bucket.
- The IAM policy permits only the SNS, SQS, DynamoDB, S3, logging, and metric actions used by these handlers.

All functions use the same immutable ZIP path and its content hash. Packaging is intentionally outside this module so the same tested artifact can be promoted between environments.

## Inputs

| Name | Type | Required | Description |
| --- | --- | :---: | --- |
| `prefix` | `string` | No | Resource-name prefix; default is `event-mesh` |
| `environment` | `string` | No | Runtime environment label; default is `local` |
| `sns_topic_arn` | `string` | Yes | Topic used by the ingestion handler |
| `order_queue_arn` | `string` | Yes | Queue attached to the order worker |
| `dlq_arn` | `string` | Yes | DLQ included in the worker IAM policy |
| `dynamodb_table_name` | `string` | Yes | Table name passed to consumers |
| `dynamodb_table_arn` | `string` | Yes | Table and index IAM scope |
| `s3_bucket_name` | `string` | Yes | Bucket receiving the Lambda notification |
| `s3_bucket_arn` | `string` | Yes | Bucket IAM and invocation scope |
| `enable_api_gateway` | `bool` | No | Creates the HTTP API when true; default is `true` |
| `lambda_package_path` | `string` | Yes | Absolute path to the tested deployment ZIP |
| `tags` | `map(string)` | No | Tags merged into supported resources |

## Outputs

| Name | Description |
| --- | --- |
| `api_endpoint` | API Gateway invoke URL, or the direct-invocation marker when disabled |
| `order_ingest_lambda_arn` / `order_ingest_lambda_name` | Ingestion function identifiers |
| `order_worker_lambda_arn` / `order_worker_lambda_name` | Worker function identifiers |
| `s3_processor_lambda_arn` / `s3_processor_lambda_name` | S3 processor identifiers |

## Operating notes

The API's permissive CORS configuration and the shared execution role are suitable for the current proof of concept. A production implementation should define allowed origins from the client contract and consider separate roles per function to reduce permission overlap.
