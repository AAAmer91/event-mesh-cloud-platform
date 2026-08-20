output "dynamodb_table_name" {
  description = "Name of the DynamoDB Orders table"
  value       = aws_dynamodb_table.orders_table.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB Orders table"
  value       = aws_dynamodb_table.orders_table.arn
}

output "s3_bucket_name" {
  description = "Name of the S3 event ingestion bucket"
  value       = aws_s3_bucket.ingestion_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN of the S3 event ingestion bucket"
  value       = aws_s3_bucket.ingestion_bucket.arn
}
