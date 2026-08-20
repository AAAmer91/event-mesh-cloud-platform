# ==============================================================================
# CloudWatch Log Groups
# ==============================================================================
resource "aws_cloudwatch_log_group" "order_ingest_logs" {
  name              = "/aws/lambda/${var.order_ingest_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Component = "Observability"
    Role      = "LambdaLogGroup"
  })
}

resource "aws_cloudwatch_log_group" "order_worker_logs" {
  name              = "/aws/lambda/${var.order_worker_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Component = "Observability"
    Role      = "LambdaLogGroup"
  })
}

resource "aws_cloudwatch_log_group" "s3_processor_logs" {
  name              = "/aws/lambda/${var.s3_processor_function_name}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Component = "Observability"
    Role      = "LambdaLogGroup"
  })
}

# ==============================================================================
# CloudWatch Metric Alarm: DLQ Non-Empty
# ==============================================================================
resource "aws_cloudwatch_metric_alarm" "dlq_alarm" {
  alarm_name          = "${var.prefix}-dlq-messages-visible-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Maximum"
  threshold           = 1
  alarm_description   = "Alarm triggers when one or more messages land in the Dead Letter Queue"

  dimensions = {
    QueueName = var.dlq_name
  }

  tags = merge(var.tags, {
    Component = "Observability"
    Role      = "Alerting"
  })
}
