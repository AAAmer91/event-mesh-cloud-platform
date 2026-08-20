# ⚡ Compute Terraform Module

Provisions serverless compute components: **AWS Lambda functions**, **Amazon API Gateway v2 (HTTP API)**, SQS Event Source Mappings with partial batch failure reporting, and S3 event triggers.

---

## 🏗️ Lambda Functions
1. **`order-ingest`**: Python 3.11 handler attached to API Gateway route `POST /orders`.
2. **`order-worker`**: SQS consumer attached to `order-events-queue` with `batch_size = 10` and `function_response_types = ["ReportBatchItemFailures"]`.
3. **`s3-processor`**: Batch worker triggered by S3 `ObjectCreated` events.

---

## 📥 Inputs

| Name | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `prefix` | `string` | No | Resource name prefix (`default: "event-mesh"`). |
| `environment` | `string` | No | Target environment (`local`, `dev`, `prod`). |
| `sns_topic_arn` | `string` | Yes | Target SNS Topic ARN for publishing. |
| `order_queue_arn` | `string` | Yes | SQS Queue ARN to bind worker trigger. |
| `dynamodb_table_name` | `string` | Yes | DynamoDB Table name for persistence. |
| `s3_bucket_name` | `string` | Yes | S3 bucket name for event triggers. |

---

## 📤 Outputs

| Name | Description |
| :--- | :--- |
| `api_endpoint` | Base URL of the API Gateway HTTP API. |
| `order_ingest_lambda_arn` | ARN of the ingestion Lambda. |
| `order_worker_lambda_arn` | ARN of the worker Lambda. |
| `s3_processor_lambda_arn` | ARN of the S3 processor Lambda. |
