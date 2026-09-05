# RecoverAI — Project Master

## 🔒 FINAL LOCKED DECISION

**Project:** RecoverAI — Context-Aware Revenue Recovery Agent  
**Track:** AI Revenue Recovery  
**Status:** Final MVP specification / ready for implementation after Phase 0 integration validation.

### One-line description
RecoverAI is an AI agent that investigates failed payments, understands payment/customer context, selects the best eligible recovery intervention, executes a bounded action through Razorpay, measures actual recovery, and learns from outcomes.

### Core loop
**Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Re-plan**

## Problem
A failed payment creates revenue at risk, but the best next recovery action can vary by payment method, failure reason, customer history, order value, previous attempts, and merchant constraints. RecoverAI addresses the decision gap between identifying a failed payment and choosing the best next intervention.

## Final solution
For each eligible failed payment, RecoverAI builds context, diagnoses the situation, evaluates candidate interventions, predicts recovery potential, chooses the best policy-valid action, executes it when supported/approved, observes the result, attributes recovered value, and uses the result for future decisioning.

## Differentiation
Do **not** position RecoverAI as a replacement for Razorpay's existing recovery capabilities or as a better retry engine.

Position it as:

> **A context-aware recovery decision layer that chooses the right intervention for the individual payment and proves incremental value.**

## Target user
Indian SMB/D2C/ecommerce merchants using Razorpay, especially founders/operators/payment or revenue teams responsible for recovering failed-payment revenue.

## MVP boundary
### Inside
- failed-payment recovery;
- payment/customer/order/failure context;
- diagnosis;
- candidate intervention selection;
- recovery prediction/scoring;
- expected-value decisioning;
- merchant guardrails;
- human approval where required;
- Standard Razorpay Payment Link Test Mode execution;
- outcome/webhook processing;
- audit trail;
- baseline comparison;
- held-out batch evaluation;
- learning/re-planning demonstration;
- one graceful failure scenario.

### Outside
- generic merchant chatbot;
- broad AI Business Growth Agent;
- full agentic commerce platform;
- full subscription/receivables suite;
- production UPI recovery dependency;
- unsupported/private Razorpay systems;
- production-scale deployment.

## Baseline
The MVP baseline is a simple fixed recovery policy, implemented deterministically and documented before evaluation. The same held-out records must be evaluated with both baseline and RecoverAI.

## Primary metric
**Incremental Recovered GMV = RecoverAI recovered GMV − Baseline recovered GMV**

No final performance number may be fabricated.

## Data strategy
Use a controlled synthetic simulator for large-batch evaluation and Razorpay Test Mode for genuine integration proof. Synthetic data must contain explainable recovery patterns and an 80/20 train/held-out split.

## AI boundary
- deterministic code: arithmetic, policy, thresholds, state/idempotency;
- ML/statistics: recovery probabilities and intervention effectiveness;
- LLM/agent: investigation, tool use, candidate reasoning, explanation, sequencing and re-planning.

## Execution
Primary demo action: **Standard Razorpay Payment Link in Test Mode**.  
UPI Payment Links are not a Test Mode dependency.

## Guardrails
- max attempts;
- max contacts;
- confidence threshold;
- max incentive where applicable;
- approval threshold;
- stop if payment is already successful;
- stop if customer opted out;
- duplicate prevention;
- model cannot override policy;
- bounded tool retry then stop/replan.

## Final implementation order
0. Razorpay integration validation  
1. Simulator + baseline  
2. Decision engine  
3. Agent orchestration  
4. Razorpay execution  
5. Outcome attribution  
6. Frontend  
7. Demo hardening

## Major decisions
- D-001: Build RecoverAI as the Buildathon MVP.
- D-002: Use AI Revenue Recovery track.
- D-003: Differentiate through context-aware intervention selection.
- D-004: Use incremental recovered GMV versus baseline as primary proof.
- D-005: Use Standard Razorpay Payment Link for Test Mode execution proof.
- D-006: Do not depend on UPI Payment Links in Test Mode.
- D-007: Use synthetic simulation for batch evidence and Test Mode for real integration proof.
- D-008: Separate deterministic logic, ML prediction, and agentic reasoning.
- D-009: Keep broad Merchant Copilot/Growth Agent as future scope.
- D-010: Validate actual MCP/API capabilities before coding against them.

## Open integration questions
1. Which exact Razorpay MCP tools are exposed in the team's connected environment?
2. Which webhook events/payloads are available?
3. Which recovery actions are actually executable in the connected environment?
4. Which model and threshold perform best on held-out data?
5. What approval thresholds should be used for the demo?

## Source hierarchy
1. `FINAL_IMPLEMENTATION_HANDOFF.md`
2. this Master document
3. MVP/product/technical specifications
4. implementation planning
5. research/historical notes

If an older document conflicts with this final handoff, update the older document to match the final handoff rather than reviving the older decision.
