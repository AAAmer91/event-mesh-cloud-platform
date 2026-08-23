# Messaging Module

This module creates the SNS-to-SQS fanout used by the order flow. One published order event is delivered to an order-processing queue and a notification queue. Persistent order-processing failures are redirected to a dead-letter queue.

## Resources and behavior

- `${prefix}-order-events-topic` is the SNS distribution point.
- `${prefix}-order-events-queue` uses 10-second long polling and the configured redrive policy.
- `${prefix}-notification-events-queue` receives a separate fanout copy; its consumer is outside this repository's current scope.
- `${prefix}-order-events-dlq` retains order messages that exceeded `max_receive_count`.
- Queue policies allow `sqs:SendMessage` only when the source ARN is the module's topic.

SNS and SQS provide at-least-once delivery. Consumers must tolerate duplicate messages, and DLQ messages require an operational review and replay policy.

## Inputs

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| `prefix` | `string` | `"event-mesh"` | Resource-name prefix |
| `max_receive_count` | `number` | `3` | Deliveries allowed before redrive to the DLQ |
| `visibility_timeout_seconds` | `number` | `30` | Period in which an in-flight order message is hidden |
| `message_retention_seconds` | `number` | `345600` | Primary and notification queue retention; four days |
| `dlq_message_retention_seconds` | `number` | `1209600` | DLQ retention; fourteen days |
| `tags` | `map(string)` | `{}` | Tags merged into resources |

## Outputs

| Name | Description |
| --- | --- |
| `sns_topic_arn` / `sns_topic_name` | Order topic identifiers |
| `order_queue_arn` / `order_queue_url` / `order_queue_name` | Order queue identifiers |
| `notification_queue_arn` / `notification_queue_url` | Notification queue identifiers |
| `dlq_arn` / `dlq_url` / `dlq_name` | Dead-letter queue identifiers |

## Operating notes

The visibility timeout must remain longer than expected processing time, including retry behavior. Retention and receive-count defaults are evaluation settings and should be selected from recovery objectives, message volume, and the team's ability to respond to DLQ alarms.
