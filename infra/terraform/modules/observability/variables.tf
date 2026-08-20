variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "event-mesh"
}

variable "order_ingest_function_name" {
  description = "Name of the Order Ingest Lambda"
  type        = string
}

variable "order_worker_function_name" {
  description = "Name of the Order Worker Lambda"
  type        = string
}

variable "s3_processor_function_name" {
  description = "Name of the S3 Processor Lambda"
  type        = string
}

variable "dlq_name" {
  description = "Name of the Dead Letter Queue"
  type        = string
}

variable "log_retention_days" {
  description = "Days to retain CloudWatch logs"
  type        = number
  default     = 14
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
