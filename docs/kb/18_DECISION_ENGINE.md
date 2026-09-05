# Decision Engine

## Core Question
Which eligible recovery intervention has the highest expected recovery value subject to merchant constraints?

## Inputs
- payment amount
- payment method
- error_source
- error_step
- error_reason
- customer success/failure history
- historical methods
- order value/category
- recency/frequency
- previous recovery actions
- merchant policy

## Candidate Actions
- retry/delayed retry where supported by the implementation
- Standard Payment Link
- reminder/payment-link resend
- no action
- human review

Exact executable actions depend on verified integration capabilities.

## Scoring
For each action:
`Expected Net Recovery = P(recovery | context, action) × recoverable_amount − action_cost − expected_incentive_cost − friction_cost`

The exact cost model is **MVP DESIGN / TO VALIDATE**.

## Decision
1. Filter ineligible actions.
2. Estimate recovery probability.
3. Calculate expected value.
4. Apply policy.
5. Select highest valid action.
6. If confidence is insufficient, review/stop.

## Deterministic vs AI
Deterministic:
- arithmetic
- thresholds
- policy
- state/idempotency
- eligibility

ML/statistics:
- recovery probability
- action effectiveness
- calibration

LLM/agent:
- contextual investigation
- candidate explanation
- tool sequencing
- re-planning
- human-readable rationale

## Example
Illustrative only:
₹12,000 failed payment; card authentication issue; customer has several prior alternative-method successes.

Possible estimated recovery:
Retry 12%; reminder 31%; Payment Link 68%.

If Payment Link has the highest policy-valid expected value, select it.

Numbers are examples only and must not be presented as measured results.
