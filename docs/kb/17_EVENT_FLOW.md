# Event Flow

1. Payment failure occurs.
2. Failure event enters RecoverAI.
3. Idempotency check runs.
4. Context is collected.
5. Failure is normalized/diagnosed.
6. Recovery opportunity is scored.
7. Candidate interventions are generated.
8. Predictions and expected values are calculated.
9. Guardrails are evaluated.
10. Action is approved or rejected.
11. Supported action executes.
12. Razorpay state/webhook is observed.
13. Outcome is attributed.
14. Metrics update.
15. Learning update is generated.
16. Agent may re-plan if another action is eligible.

### Stop Conditions
- payment already successful
- refunded/terminal state
- opted out where applicable
- confidence below threshold
- policy limit reached
- duplicate action
- action unavailable
- tool failure after bounded retry
