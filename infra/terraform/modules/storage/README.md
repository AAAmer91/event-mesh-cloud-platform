# Storage Module

This module creates the DynamoDB orders table and the S3 bucket used for JSON batch ingestion.

## DynamoDB table

The table uses on-demand billing with:

- `order_id` as the partition key;
- `created_at` as the sort key;
- `CustomerIndex` for customer and creation-time queries;
- `StatusIndex` for status and creation-time queries;
- optional point-in-time recovery, enabled by default.

The worker's conditional insert uses `order_id` as part of its duplicate-write protection. Index design should be revisited against observed query patterns and partition distribution before production use.

## S3 bucket

The batch-ingestion bucket enables object versioning and Amazon S3-managed AES-256 encryption. The compute module attaches the JSON object-created notification because it owns the target Lambda and invocation permission.

The module does not define lifecycle expiration, public-access-block resources, access logging, replication, or a customer-managed KMS key. Apply those controls according to the target account's baseline and data classification.

## Inputs

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `prefix` | `string` | `"event-mesh"` | Resource-name prefix |
| `enable_pitr` | `bool` | `true` | Enables DynamoDB point-in-time recovery |
| `tags` | `map(string)` | `{}` | Tags merged into resources |

## Outputs

| Name | Description |
| --- | --- |
| `dynamodb_table_name` / `dynamodb_table_arn` | Orders table identifiers |
| `s3_bucket_name` / `s3_bucket_arn` | Batch-ingestion bucket identifiers |
