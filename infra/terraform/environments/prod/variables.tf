variable "aws_region" {
  description = "AWS region used for the deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Protected GitHub environment being deployed"
  type        = string

  validation {
    condition     = contains(["dev", "production"], var.environment)
    error_message = "Environment must be dev or production."
  }
}

variable "prefix" {
  description = "Globally unique resource name prefix"
  type        = string
}

variable "lambda_package_path" {
  description = "Path to the previously tested Lambda deployment ZIP"
  type        = string
}

variable "log_retention_days" {
  description = "CloudWatch log retention period"
  type        = number
  default     = 30
}
