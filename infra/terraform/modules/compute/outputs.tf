output "api_endpoint" {
  description = "Base URL of the API Gateway HTTP API"
  value       = var.enable_api_gateway ? try(aws_apigatewayv2_stage.default_stage[0].invoke_url, "") : "Direct-Lambda-Invocation (LocalStack Community Mode)"
}


output "order_ingest_lambda_arn" {
  description = "ARN of the Order Ingest Lambda"
  value       = aws_lambda_function.order_ingest.arn
}

output "order_ingest_lambda_name" {
  description = "Name of the Order Ingest Lambda"
  value       = aws_lambda_function.order_ingest.function_name
}

output "order_worker_lambda_arn" {
  description = "ARN of the Order Worker Lambda"
  value       = aws_lambda_function.order_worker.arn
}

output "order_worker_lambda_name" {
  description = "Name of the Order Worker Lambda"
  value       = aws_lambda_function.order_worker.function_name
}

output "s3_processor_lambda_arn" {
  description = "ARN of the S3 Processor Lambda"
  value       = aws_lambda_function.s3_processor.arn
}

output "s3_processor_lambda_name" {
  description = "Name of the S3 Processor Lambda"
  value       = aws_lambda_function.s3_processor.function_name
}
