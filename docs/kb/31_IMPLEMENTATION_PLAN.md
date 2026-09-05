# Implementation Plan

## Stage 0 — Documentation & Integration Validation
- Review this knowledge base.
- Connect Razorpay MCP.
- Enumerate actual tools.
- Verify payment/order reads.
- Create Standard Payment Link in Test Mode.
- Verify success/failure state.
- Validate webhook path.

## Stage 1 — Data Foundation
- PostgreSQL schema.
- Synthetic generator.
- Seed data.
- Baseline.

## Stage 2 — Recovery Decision Core
- Context builder.
- Diagnosis.
- Strategy catalogue.
- Prediction/scoring.
- Expected value.
- Guardrails.

## Stage 3 — Agent Orchestration
- Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Re-plan.

## Stage 4 — Razorpay Execution
- Integration wrapper.
- Payment Link execution.
- webhook/outcome processor.
- idempotency.

## Stage 5 — Frontend
- recovery queue.
- decision view.
- approval.
- timeline.
- impact view.

## Stage 6 — Evaluation
- held-out batch.
- baseline comparison.
- metrics.
- edge cases.

## Stage 7 — Demo Hardening
- 5-minute script.
- seeded scenarios.
- failure injection.
- observability.
