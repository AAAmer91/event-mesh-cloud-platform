# ==============================================================================
# DynamoDB Orders Table
# ==============================================================================
resource "aws_dynamodb_table" "orders_table" {
  name         = "${var.prefix}-orders-table"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "order_id"
  range_key    = "created_at"

  attribute {
    name = "order_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "customer_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  global_secondary_index {
    name            = "CustomerIndex"
    hash_key        = "customer_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }

  tags = merge(var.tags, {
    Component = "Storage"
    Role      = "PrimaryOrdersDatabase"
  })
}

# ==============================================================================
# S3 Ingestion Bucket
# ==============================================================================
resource "aws_s3_bucket" "ingestion_bucket" {
  bucket = "${var.prefix}-event-ingestion-payloads"

  tags = merge(var.tags, {
    Component = "Storage"
    Role      = "BatchIngestionBucket"
  })
}

resource "aws_s3_bucket_versioning" "ingestion_bucket_versioning" {
  bucket = aws_s3_bucket.ingestion_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ingestion_bucket_encryption" {
  bucket = aws_s3_bucket.ingestion_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
