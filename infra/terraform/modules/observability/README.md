# 📊 Observability Terraform Module

Provisions **Amazon CloudWatch Log Groups** with automated retention policies and **CloudWatch Metric Alarms** for monitoring Dead-Letter Queue (DLQ) depth.

---

## 🏗️ Resources
- **Log Groups:**
  - `/aws/lambda/order-ingest`
  - `/aws/lambda/order-worker`
  - `/aws/lambda/s3-processor`
- **Metric Alarm:**
  - `dlq-messages-visible-alarm`: Triggers whenever `ApproximateNumberOfMessagesVisible >= 1` on the DLQ over a 60-second window.

---

## 📥 Inputs

| Name | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `prefix` | `string` | `"event-mesh"` | Resource name prefix. |
| `log_retention_days` | `number` | `14` | Days to retain CloudWatch logs. |
| `dlq_name` | `string` | Required | SQS Dead Letter Queue name for alarm dimension. |

---

## 📤 Outputs

| Name | Description |
| :--- | :--- |
| `dlq_alarm_arn` | ARN of the CloudWatch DLQ Metric Alarm. |
| `dlq_alarm_name` | Name of the CloudWatch DLQ Metric Alarm. |
