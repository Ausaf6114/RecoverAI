# Non-Functional Requirements

## Reliability
Critical actions must be idempotent and fail safely.

## Performance
Interactive decision views should return within a practical demo-friendly latency. Exact SLO: **TO VALIDATE**.

## Security
Secrets must remain server-side. Do not expose Razorpay credentials in frontend code.

## Explainability
Every material action should expose the decision rationale and relevant evidence.

## Auditability
Record state transitions, policy checks, action execution, approvals, and outcomes.

## Scalability
Architecture should separate synchronous UI paths from batch simulation/evaluation.

## Maintainability
Use modular services with clear interfaces.

## Observability
Log decision IDs, action IDs, tool failures, model scores, and outcome transitions.

Exact production SLOs and compliance controls are **TO VALIDATE**.
