variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "event-mesh"
}

variable "environment" {
  description = "Deployment environment (local, dev, prod)"
  type        = string
  default     = "local"
}

variable "sns_topic_arn" {
  description = "ARN of the Order Events SNS Topic"
  type        = string
}

variable "order_queue_arn" {
  description = "ARN of the SQS Order Queue"
  type        = string
}

variable "dlq_arn" {
  description = "ARN of the Dead Letter Queue"
  type        = string
}

variable "dynamodb_table_name" {
  description = "Name of the DynamoDB Orders Table"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "ARN of the DynamoDB Orders Table"
  type        = string
}

variable "s3_bucket_name" {
  description = "Name of the S3 Ingestion Bucket"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the S3 Ingestion Bucket"
  type        = string
}

variable "enable_api_gateway" {
  description = "Whether to provision the API Gateway HTTP API v2 (LocalStack Community supports direct Lambda/REST API, Pro supports HTTP API v2)"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
