# Observability Module

This module creates CloudWatch log groups for the three Lambda functions and an alarm when at least one message is visible in the order dead-letter queue.

## Resources

- one log group for each supplied Lambda function name, using the configured retention period;
- one SQS `ApproximateNumberOfMessagesVisible` alarm evaluated over a 60-second period;
- tags identifying the resources as logging or alerting components.

The alarm has no notification target in this module. Alert delivery is an environment concern so the adopting system can connect its approved SNS topic, incident platform, or operations channel.

## Inputs

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `prefix` | `string` | `"event-mesh"` | Resource-name prefix |
| `order_ingest_function_name` | `string` | Required | Ingestion Lambda name |
| `order_worker_function_name` | `string` | Required | Worker Lambda name |
| `s3_processor_function_name` | `string` | Required | S3 processor Lambda name |
| `dlq_name` | `string` | Required | Queue name used as the alarm dimension |
| `log_retention_days` | `number` | `14` | CloudWatch log retention period |
| `tags` | `map(string)` | `{}` | Tags merged into resources |

## Outputs

| Name | Description |
| --- | --- |
| `dlq_alarm_arn` | ARN of the DLQ depth alarm |
| `dlq_alarm_name` | Name of the DLQ depth alarm |

## Operating notes

A non-empty DLQ is a useful correctness signal but not a complete service-level view. A production environment should add notification routing, ingestion and worker error rates, queue age and depth, Lambda throttles, latency objectives, dashboards, and ownership metadata.
