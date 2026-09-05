# API Specification

No implementation yet.

## GET /health
Purpose: service health.
Response: status/version.

## GET /payments/{payment_id}
Purpose: fetch local normalized payment/context.
Response: payment summary.

## GET /recovery/opportunities
Purpose: list revenue-at-risk opportunities.
Query: status, segment, date range.

## GET /recovery/opportunities/{id}
Purpose: decision detail and timeline.

## POST /recovery/opportunities/{id}/decide
Purpose: run decision engine.
Request: decision context/options if needed.
Response: decision ID, selected action, confidence, expected value, policy result.

## POST /recovery/actions/{id}/approve
Purpose: approve a gated action.
Response: approval/action status.

## POST /recovery/actions/{id}/execute
Purpose: execute approved action.
Response: external action ID/status.

## POST /webhooks/razorpay
Purpose: receive Razorpay events.
Response: acknowledgement.

## GET /analytics/recovery
Purpose: baseline vs RecoverAI metrics.

Authentication assumptions are **TO VALIDATE** for the deployed MVP. Razorpay credentials must remain backend-side.
