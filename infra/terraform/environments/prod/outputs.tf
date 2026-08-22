output "api_endpoint" {
  description = "Public API endpoint used by post-deployment smoke tests"
  value       = module.compute.api_endpoint
}

output "sns_topic_arn" {
  value = module.messaging.sns_topic_arn
}

output "dlq_url" {
  value = module.messaging.dlq_url
}

output "dynamodb_table_name" {
  value = module.storage.dynamodb_table_name
}
