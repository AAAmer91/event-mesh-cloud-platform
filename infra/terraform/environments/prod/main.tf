terraform {
  required_version = ">= 1.8.0"

  backend "s3" {}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "event-mesh-cloud-platform"
      ManagedBy   = "Terraform"
      Repository  = "AAAmer91/event-mesh-cloud-platform"
    }
  }
}

module "messaging" {
  source = "../../modules/messaging"
  prefix = var.prefix
}

module "storage" {
  source      = "../../modules/storage"
  prefix      = var.prefix
  enable_pitr = true
}

module "compute" {
  source = "../../modules/compute"

  prefix              = var.prefix
  environment         = var.environment
  enable_api_gateway  = true
  sns_topic_arn       = module.messaging.sns_topic_arn
  order_queue_arn     = module.messaging.order_queue_arn
  dlq_arn             = module.messaging.dlq_arn
  dynamodb_table_name = module.storage.dynamodb_table_name
  dynamodb_table_arn  = module.storage.dynamodb_table_arn
  s3_bucket_name      = module.storage.s3_bucket_name
  s3_bucket_arn       = module.storage.s3_bucket_arn
  lambda_package_path = var.lambda_package_path
}

module "observability" {
  source = "../../modules/observability"

  prefix                     = var.prefix
  order_ingest_function_name = module.compute.order_ingest_lambda_name
  order_worker_function_name = module.compute.order_worker_lambda_name
  s3_processor_function_name = module.compute.s3_processor_lambda_name
  dlq_name                   = module.messaging.dlq_name
  log_retention_days         = var.log_retention_days
}
