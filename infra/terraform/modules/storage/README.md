# 🗄️ Storage Terraform Module

Provisions **Amazon DynamoDB** with Global Secondary Indexes (GSIs) and an **Amazon S3** batch ingestion bucket with versioning and AES-256 server-side encryption.

---

## 🏗️ Resources
- **DynamoDB Table:** `orders-table`
  - Partition Key: `order_id` (String)
  - Sort Key: `created_at` (String)
  - GSI 1: `CustomerIndex` (`customer_id` + `created_at`)
  - GSI 2: `StatusIndex` (`status` + `created_at`)
  - Billing Mode: `PAY_PER_REQUEST` (On-Demand Serverless)
- **S3 Bucket:** `event-ingestion-payloads` (Bucket versioning + SSE encryption).

---

## 📥 Inputs

| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `prefix` | `string` | `"event-mesh"` | Resource name prefix. |
| `enable_pitr` | `bool` | `true` | Enable Point-in-Time Recovery. |
| `tags` | `map(string)` | `{}` | Key-value tags. |

---

## 📤 Outputs

| Name | Description |
| :--- | :--- |
| `dynamodb_table_name` | Name of the DynamoDB Orders table. |
| `dynamodb_table_arn` | ARN of the DynamoDB Orders table. |
| `s3_bucket_name` | Name of the S3 ingestion bucket. |
| `s3_bucket_arn` | ARN of the S3 ingestion bucket. |
