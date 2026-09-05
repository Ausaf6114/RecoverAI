# Database Specification

PostgreSQL is the preferred MVP database.

## Tables
- merchants
- customers
- orders
- payments
- payment_attempts
- failures
- recovery_opportunities
- recovery_actions
- recovery_outcomes
- agent_decisions
- experiments
- baselines
- audit_events

## Keys
Use UUID/string identifiers internally where practical. External Razorpay IDs should be stored as unique indexed fields.

## Important Indexes
- payment_id
- order_id
- customer_id
- merchant_id
- status
- created_at
- opportunity_id
- action_id
- experiment_id

Exact schema types and indexes are implementation details to be finalized after API/data validation.
