# ==============================================================================
# IAM Role & Policies for Serverless Lambdas
# ==============================================================================
resource "aws_iam_role" "lambda_exec_role" {
  name = "${var.prefix}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_policy" "lambda_policy" {
  name = "${var.prefix}-lambda-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Sid    = "CloudWatchMetrics"
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      {
        Sid    = "SNSPublish"
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = var.sns_topic_arn
      },
      {
        Sid    = "SQSConsume"
        Effect = "Allow"
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          var.order_queue_arn,
          var.dlq_arn
        ]
      },
      {
        Sid    = "DynamoDBAccess"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          var.dynamodb_table_arn,
          "${var.dynamodb_table_arn}/index/*"
        ]
      },
      {
        Sid    = "S3Access"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          var.s3_bucket_arn,
          "${var.s3_bucket_arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_policy_attach" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

# ==============================================================================
# Packaged Lambda Source Bundle
# ==============================================================================
data "archive_file" "lambda_bundle_zip" {
  type        = "zip"
  output_path = "${path.module}/lambda_bundle.zip"

  source {
    content  = file("${path.module}/../../../../src/handlers/order_ingest.py")
    filename = "src/handlers/order_ingest.py"
  }
  source {
    content  = file("${path.module}/../../../../src/handlers/order_worker.py")
    filename = "src/handlers/order_worker.py"
  }
  source {
    content  = file("${path.module}/../../../../src/handlers/s3_processor.py")
    filename = "src/handlers/s3_processor.py"
  }
  source {
    content  = file("${path.module}/../../../../src/core/logger.py")
    filename = "src/core/logger.py"
  }
  source {
    content  = file("${path.module}/../../../../src/core/metrics.py")
    filename = "src/core/metrics.py"
  }
  source {
    content  = file("${path.module}/../../../../src/core/tracing.py")
    filename = "src/core/tracing.py"
  }
  source {
    content  = ""
    filename = "src/__init__.py"
  }
  source {
    content  = ""
    filename = "src/core/__init__.py"
  }
  source {
    content  = ""
    filename = "src/handlers/__init__.py"
  }
}

# ==============================================================================
# Lambda 1: Order Ingestion (API / Producer)
# ==============================================================================
resource "aws_lambda_function" "order_ingest" {
  function_name = "${var.prefix}-order-ingest"
  runtime       = "python3.11"
  handler       = "src.handlers.order_ingest.handler"
  role          = aws_iam_role.lambda_exec_role.arn
  timeout       = 15
  memory_size   = 256

  filename         = data.archive_file.lambda_bundle_zip.output_path
  source_code_hash = data.archive_file.lambda_bundle_zip.output_base64sha256

  environment {
    variables = {
      SNS_TOPIC_ARN           = var.sns_topic_arn
      ENVIRONMENT             = var.environment
      LOG_LEVEL               = "INFO"
      POWERTOOLS_SERVICE_NAME = "order-ingest"
    }
  }

  tags = merge(var.tags, {
    Role = "IngestionHandler"
  })
}

# ==============================================================================
# Lambda 2: Order Worker (SQS Consumer -> DynamoDB)
# ==============================================================================
resource "aws_lambda_function" "order_worker" {
  function_name = "${var.prefix}-order-worker"
  runtime       = "python3.11"
  handler       = "src.handlers.order_worker.handler"
  role          = aws_iam_role.lambda_exec_role.arn
  timeout       = 30
  memory_size   = 256

  filename         = data.archive_file.lambda_bundle_zip.output_path
  source_code_hash = data.archive_file.lambda_bundle_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE_NAME     = var.dynamodb_table_name
      ENVIRONMENT             = var.environment
      LOG_LEVEL               = "INFO"
      POWERTOOLS_SERVICE_NAME = "order-worker"
    }
  }

  tags = merge(var.tags, {
    Role = "QueueConsumer"
  })
}

# SQS -> Lambda Trigger (Event Source Mapping with Batch Failure Reporting)
resource "aws_lambda_event_source_mapping" "sqs_order_trigger" {
  event_source_arn                   = var.order_queue_arn
  function_name                      = aws_lambda_function.order_worker.arn
  batch_size                         = 10
  maximum_batching_window_in_seconds = 5
  function_response_types            = ["ReportBatchItemFailures"]
}

# ==============================================================================
# Lambda 3: S3 Batch Event Processor
# ==============================================================================
resource "aws_lambda_function" "s3_processor" {
  function_name = "${var.prefix}-s3-processor"
  runtime       = "python3.11"
  handler       = "src.handlers.s3_processor.handler"
  role          = aws_iam_role.lambda_exec_role.arn
  timeout       = 60
  memory_size   = 512

  filename         = data.archive_file.lambda_bundle_zip.output_path
  source_code_hash = data.archive_file.lambda_bundle_zip.output_base64sha256


  environment {
    variables = {
      DYNAMODB_TABLE_NAME     = var.dynamodb_table_name
      ENVIRONMENT             = var.environment
      LOG_LEVEL               = "INFO"
      POWERTOOLS_SERVICE_NAME = "s3-processor"
    }
  }

  tags = merge(var.tags, {
    Role = "S3BatchProcessor"
  })
}

# S3 Event Notification Trigger
resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.s3_processor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_bucket_arn
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = var.s3_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.s3_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}

# ==============================================================================
# API Gateway (HTTP API v2)
# ==============================================================================
resource "aws_apigatewayv2_api" "http_api" {
  name          = "${var.prefix}-http-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "GET", "OPTIONS"]
    allow_headers = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token"]
    max_age       = 300
  }

  tags = var.tags
}

resource "aws_apigatewayv2_stage" "default_stage" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.order_ingest.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "orders_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /orders"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_lambda_permission" "api_gw_permission" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.order_ingest.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}
