output "api_endpoint" {
  description = "API Gateway LocalStack URL"
  value       = module.compute.api_endpoint
}

output "sns_topic_arn" {
  description = "SNS Topic ARN"
  value       = module.messaging.sns_topic_arn
}

output "order_queue_url" {
  description = "SQS Order Queue URL"
  value       = module.messaging.order_queue_url
}

output "dlq_url" {
  description = "SQS DLQ URL"
  value       = module.messaging.dlq_url
}

output "dynamodb_table_name" {
  description = "DynamoDB Table Name"
  value       = module.storage.dynamodb_table_name
}

output "s3_bucket_name" {
  description = "S3 Ingestion Bucket Name"
  value       = module.storage.s3_bucket_name
}
