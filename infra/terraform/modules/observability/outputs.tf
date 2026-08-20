output "dlq_alarm_arn" {
  description = "ARN of the DLQ CloudWatch metric alarm"
  value       = aws_cloudwatch_metric_alarm.dlq_alarm.arn
}

output "dlq_alarm_name" {
  description = "Name of the DLQ CloudWatch metric alarm"
  value       = aws_cloudwatch_metric_alarm.dlq_alarm.alarm_name
}
