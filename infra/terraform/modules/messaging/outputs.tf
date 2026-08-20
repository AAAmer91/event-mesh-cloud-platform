output "sns_topic_arn" {
  description = "ARN of the Order Events SNS Topic"
  value       = aws_sns_topic.order_events.arn
}

output "sns_topic_name" {
  description = "Name of the Order Events SNS Topic"
  value       = aws_sns_topic.order_events.name
}

output "order_queue_url" {
  description = "URL of the primary order processing queue"
  value       = aws_sqs_queue.order_queue.id
}

output "order_queue_arn" {
  description = "ARN of the primary order processing queue"
  value       = aws_sqs_queue.order_queue.arn
}

output "order_queue_name" {
  description = "Name of the primary order processing queue"
  value       = aws_sqs_queue.order_queue.name
}

output "notification_queue_url" {
  description = "URL of the notifications queue"
  value       = aws_sqs_queue.notification_queue.id
}

output "notification_queue_arn" {
  description = "ARN of the notifications queue"
  value       = aws_sqs_queue.notification_queue.arn
}

output "dlq_url" {
  description = "URL of the order processing Dead Letter Queue"
  value       = aws_sqs_queue.order_dlq.id
}

output "dlq_arn" {
  description = "ARN of the order processing Dead Letter Queue"
  value       = aws_sqs_queue.order_dlq.arn
}

output "dlq_name" {
  description = "Name of the order processing Dead Letter Queue"
  value       = aws_sqs_queue.order_dlq.name
}
