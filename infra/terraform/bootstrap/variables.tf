variable "aws_region" {
  description = "AWS region for the Terraform state bucket"
  type        = string
  default     = "us-east-1"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for Terraform state"
  type        = string
}

variable "github_repository" {
  description = "GitHub owner/repository allowed to request deployment tokens"
  type        = string
  default     = "AAAmer91/event-mesh-cloud-platform"
}
