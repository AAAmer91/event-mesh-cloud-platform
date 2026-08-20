# 📨 Messaging Terraform Module

Provisions an asynchronous, high-throughput event mesh fanout using **Amazon SNS** and **Amazon SQS** with redrive policies and Dead-Letter Queue (DLQ) support.

---

## 🏗️ Architecture
- **SNS Topic:** `order-events-topic` (Event bus).
- **Primary Queue:** `order-events-queue` (with 10-second long polling and SQS redrive policy).
- **Secondary Queue:** `notification-events-queue` (subscribes to order topic for fanout).
- **Dead Letter Queue (DLQ):** `order-events-dlq` (quarantines messages failing 3 deliveries).

---

## 📥 Inputs

| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `prefix` | `string` | `"event-mesh"` | Resource name prefix. |
| `max_receive_count` | `number` | `3` | Maximum receive attempts before sending to DLQ. |
| `visibility_timeout_seconds` | `number` | `30` | Queue visibility timeout in seconds. |
| `message_retention_seconds` | `number` | `345600` | Retention duration for standard queue (4 days). |
| `dlq_message_retention_seconds` | `number` | `1209600` | Retention duration for DLQ (14 days). |
| `tags` | `map(string)` | `{}` | Key-value tags. |

---

## 📤 Outputs

| Name | Description |
| :--- | :--- |
| `sns_topic_arn` | ARN of the SNS topic. |
| `order_queue_arn` / `order_queue_url` | ARN and URL of the primary order processing queue. |
| `notification_queue_arn` / `notification_queue_url` | ARN and URL of the notifications queue. |
| `dlq_arn` / `dlq_url` | ARN and URL of the Dead Letter Queue. |
