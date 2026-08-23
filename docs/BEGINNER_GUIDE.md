# Beginner Guide

This guide explains the project without assuming previous AWS or event-driven architecture experience.

## The problem being explored

An order endpoint should respond quickly even when several downstream tasks need to happen. Calling every downstream service during the HTTP request would couple their speed and availability to the client response.

This proof of concept accepts an order, turns it into an event, and lets independent consumers process that event later. The result is a small working model for evaluating asynchronous AWS services and the operational controls around them.

## Follow one order

1. A client sends `POST /orders` through API Gateway.
2. `order_ingest` validates the JSON and gives the event an order ID and trace ID.
3. The handler publishes the event to an SNS topic.
4. SNS copies the event into the order and notification SQS queues.
5. SQS invokes `order_worker` with one or more queued records.
6. The worker writes the order to DynamoDB only if that order ID is not already present.
7. If processing repeatedly fails, SQS moves the message to a dead-letter queue.

The notification queue is included to show fanout. A notification consumer is outside the current proof-of-concept scope.

## The main terms

| Term | Plain-language meaning |
| --- | --- |
| Event | A record that something happened, such as an order being accepted |
| Producer | Code that publishes an event |
| Consumer | Code that reads and handles an event |
| SNS topic | A distribution point that copies one event to multiple subscribers |
| SQS queue | A durable waiting line between a producer and a consumer |
| Lambda | Code AWS starts in response to an HTTP request, queue message, or file event |
| DynamoDB | A managed key-value and document database |
| Dead-letter queue | A separate queue for messages that exceeded their retry limit |
| Idempotency | Processing the same input more than once without duplicating the intended result |
| Terraform | Configuration that creates and connects cloud resources through APIs |
| LocalStack | A local implementation of selected AWS APIs used for development and tests |

## Why duplicates are expected

SQS provides at-least-once delivery. A worker can finish its work but fail before acknowledging the message, so the same event may arrive again. The order worker uses a DynamoDB condition that rejects a second insert for an existing `order_id`.

That condition protects this write; it is not a general exactly-once guarantee. Any additional side effect, such as charging a card or sending an email, needs its own idempotency design.

## How failures are contained

The Lambda integration reports individual failed records instead of failing an entire batch. Successful records are removed while failed records become visible for another attempt. After the configured receive count, SQS moves a persistent failure to the DLQ and a CloudWatch alarm can notify operators.

This separates retryable failures from healthy work, but operators still need a documented process to inspect, correct, and replay DLQ messages.

## LocalStack and AWS

The same Terraform modules are composed for two contexts:

- the local environment points AWS providers and clients to LocalStack;
- the AWS environment uses real service endpoints and GitHub OIDC for deployment identity.

LocalStack makes integration tests repeatable and avoids requiring cloud credentials for daily development. It does not reproduce every AWS behavior, quota, IAM boundary, performance characteristic, or regional failure mode. AWS validation remains necessary before production use.

## A practical reading path

1. Use the [README](../README.md#local-development) to create the local environment.
2. Read [Architecture](../ARCHITECTURE.md) while following an event through the diagram.
3. Look at `src/handlers/order_ingest.py` and `src/handlers/order_worker.py`.
4. Read the messaging and compute module READMEs under `infra/terraform/modules/`.
5. Read [CI/CD operations](CICD.md) to understand how a tested artifact is released and promoted.

## Proof-of-concept boundaries

The repository does not implement customer authentication, a notification consumer, cross-region recovery, organization-wide networking, production alert delivery, or a DLQ replay service. Those boundaries are deliberate so the event path, infrastructure composition, and delivery controls can be evaluated independently.
