variable "prefix" {
  description = "Resource name prefix"
  type        = string
  default     = "event-mesh"
}

variable "visibility_timeout_seconds" {
  description = "Visibility timeout for primary processing queue in seconds"
  type        = number
  default     = 30
}

variable "message_retention_seconds" {
  description = "Retention period for SQS messages in seconds (default 4 days)"
  type        = number
  default     = 345600
}

variable "dlq_message_retention_seconds" {
  description = "Retention period for DLQ messages in seconds (default 14 days)"
  type        = number
  default     = 1209600
}

variable "max_receive_count" {
  description = "Number of times a message is delivered before being sent to DLQ"
  type        = number
  default     = 3
}

variable "tags" {
  description = "Resource tags"
  type        = map(string)
  default     = {}
}
