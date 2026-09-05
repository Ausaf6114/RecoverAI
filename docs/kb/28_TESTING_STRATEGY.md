# Testing Strategy

## Unit
- expected-value calculations
- eligibility
- guardrails
- idempotency
- metric calculations

## Integration
- Razorpay MCP/API read
- Payment Link creation
- Payment Link retrieval
- webhook processing

## Agent
- diagnosis correctness on controlled cases
- candidate selection
- no hallucinated context
- structured output validity

## Decision Engine
- action ranking
- confidence thresholds
- policy overrides
- no-action cases

## API
- request validation
- auth assumptions
- errors
- idempotency

## Frontend
- opportunity rendering
- decision display
- approval
- outcome timeline

## End-to-End
Failed payment → context → decision → guardrail → action → outcome → metric.

## Demo Scenarios
1. High-confidence recovery.
2. Low-confidence stop.
3. Duplicate/completed payment stop.
4. External tool failure → bounded retry → stop/replan.
5. Batch baseline uplift.
