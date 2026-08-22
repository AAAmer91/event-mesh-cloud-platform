terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.60"
    }
  }
}

# ==============================================================================
# AWS Provider configured for LocalStack
# ==============================================================================
provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true
  s3_use_path_style           = true

  endpoints {
    apigateway   = "http://localhost:4566"
    apigatewayv2 = "http://localhost:4566"
    cloudwatch   = "http://localhost:4566"
    dynamodb     = "http://localhost:4566"
    iam          = "http://localhost:4566"
    lambda       = "http://localhost:4566"
    logs         = "http://localhost:4566"
    s3           = "http://localhost:4566"
    sns          = "http://localhost:4566"
    sqs          = "http://localhost:4566"
    sts          = "http://localhost:4566"
  }

  default_tags {
    tags = {
      Environment = "local"
      Project     = "event-mesh-cloud-platform"
      ManagedBy   = "Terraform"
    }
  }
}

# ==============================================================================
# Modules
# ==============================================================================
module "messaging" {
  source = "../../modules/messaging"

  prefix = var.prefix
}

module "storage" {
  source = "../../modules/storage"

  prefix      = var.prefix
  enable_pitr = false # LocalStack optimization
}

module "compute" {
  source = "../../modules/compute"

  prefix              = var.prefix
  environment         = "local"
  enable_api_gateway  = false # LocalStack Community optimization (apigatewayv2 is a Pro feature)
  sns_topic_arn       = module.messaging.sns_topic_arn
  order_queue_arn     = module.messaging.order_queue_arn
  dlq_arn             = module.messaging.dlq_arn
  dynamodb_table_name = module.storage.dynamodb_table_name
  dynamodb_table_arn  = module.storage.dynamodb_table_arn
  s3_bucket_name      = module.storage.s3_bucket_name
  s3_bucket_arn       = module.storage.s3_bucket_arn
  lambda_package_path = abspath("${path.root}/../../../../dist/lambda-package.zip")
}

module "observability" {
  source = "../../modules/observability"

  prefix                     = var.prefix
  order_ingest_function_name = module.compute.order_ingest_lambda_name
  order_worker_function_name = module.compute.order_worker_lambda_name
  s3_processor_function_name = module.compute.s3_processor_lambda_name
  dlq_name                   = module.messaging.dlq_name
  log_retention_days         = 1
}
