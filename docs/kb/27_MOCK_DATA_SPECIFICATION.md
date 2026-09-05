# Mock Data Specification

## Suggested Scale
- Payments: 20,000–50,000
- Orders: 8,000–20,000
- Customers: 4,000–10,000
- Intervention outcomes: 5,000+

These are recommended ranges, not mandatory requirements.

## Payment Fields
payment_id, order_id, customer_id, amount, timestamp, method, status, error_source, error_step, error_reason.

## Customer Fields
customer_id, successful methods, failure counts, AOV, recency, frequency.

## Order Fields
order_id, customer_id, amount, timestamp, category.

## Outcome Fields
payment_id, intervention, success, recovered_amount, time_to_recovery.

## Policy Fields
approval thresholds, max contacts, max incentive, confidence threshold.

## Controlled Patterns
Data must encode relationships such as:
- repeated card authentication failures + successful alternate methods → alternate payment path more likely;
- transient/network failure → delayed retry more likely;
- repeated failures → no action more likely;
- recent/high-value customer context can influence recovery probability.

Do not present synthetic results as real merchant data.
