# ==============================================================================
# SQS Dead Letter Queue (DLQ)
# ==============================================================================
resource "aws_sqs_queue" "order_dlq" {
  name                      = "${var.prefix}-order-events-dlq"
  message_retention_seconds = var.dlq_message_retention_seconds

  tags = merge(var.tags, {
    Component = "Messaging"
    Role      = "DeadLetterQueue"
  })
}

# ==============================================================================
# SQS Primary Order Processing Queue (with Redrive Policy)
# ==============================================================================
resource "aws_sqs_queue" "order_queue" {
  name                       = "${var.prefix}-order-events-queue"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  message_retention_seconds  = var.message_retention_seconds
  receive_wait_time_seconds  = 10 # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.order_dlq.arn
    maxReceiveCount     = var.max_receive_count
  })

  tags = merge(var.tags, {
    Component = "Messaging"
    Role      = "PrimaryProcessingQueue"
  })
}

# ==============================================================================
# SQS Notifications Queue
# ==============================================================================
resource "aws_sqs_queue" "notification_queue" {
  name                      = "${var.prefix}-notification-events-queue"
  message_retention_seconds = var.message_retention_seconds
  receive_wait_time_seconds = 10

  tags = merge(var.tags, {
    Component = "Messaging"
    Role      = "NotificationQueue"
  })
}

# ==============================================================================
# SNS Topic: Order Events
# ==============================================================================
resource "aws_sns_topic" "order_events" {
  name = "${var.prefix}-order-events-topic"

  tags = merge(var.tags, {
    Component = "Messaging"
    Role      = "EventBusTopic"
  })
}

# ==============================================================================
# SNS -> SQS Subscriptions (Fanout)
# ==============================================================================
resource "aws_sns_topic_subscription" "order_queue_sub" {
  topic_arn            = aws_sns_topic.order_events.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.order_queue.arn
  raw_message_delivery = false
}

resource "aws_sns_topic_subscription" "notification_queue_sub" {
  topic_arn            = aws_sns_topic.order_events.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.notification_queue.arn
  raw_message_delivery = false
}

# SQS Queue Policies allowing SNS topic to send messages
resource "aws_sqs_queue_policy" "order_queue_policy" {
  queue_url = aws_sqs_queue.order_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNSSend"
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.order_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.order_events.arn
          }
        }
      }
    ]
  })
}

resource "aws_sqs_queue_policy" "notification_queue_policy" {
  queue_url = aws_sqs_queue.notification_queue.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNSSend"
        Effect    = "Allow"
        Principal = "*"
        Action    = "sqs:SendMessage"
        Resource  = aws_sqs_queue.notification_queue.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.order_events.arn
          }
        }
      }
    ]
  })
}
