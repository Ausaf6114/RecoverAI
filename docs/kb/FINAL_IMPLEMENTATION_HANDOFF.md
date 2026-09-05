# RecoverAI — FINAL IMPLEMENTATION HANDOFF

**Status: LOCKED FINAL MVP SPECIFICATION**  
**Use this file first. It is the implementation handoff for Claude, Antigravity, and the development team.**

## 1. Product

**Name:** RecoverAI  
**Full name:** Context-Aware Revenue Recovery Agent  
**Buildathon track:** AI Revenue Recovery

### One-line product
RecoverAI is an AI agent that investigates failed payments, understands the payment and customer context, chooses the best eligible recovery action, executes a bounded action through Razorpay, measures whether money was recovered, and uses outcomes to improve future decisions.

### Core loop
**Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Re-plan**

---

## 2. The problem

A failed online payment creates revenue at risk. The merchant may know that a payment failed, but the best next action can differ by customer, failure reason, payment method, order value, previous attempts, and merchant rules.

Example:
- Temporary/network failure → a later retry may be appropriate.
- Repeated card failures + previous successful alternative-method payments → a Payment Link may be better.
- Repeated failures or completed payment → stop instead of creating more friction.

The product problem is therefore:

> **How can a merchant choose the right recovery action for the right failed payment instead of applying the same recovery action to everyone?**

---

## 3. Final solution

For every eligible failed payment RecoverAI:

1. Detects the revenue-risk event.
2. Builds context from payment, customer, order, failure, and historical information.
3. Produces a structured diagnosis/root-cause hypothesis with uncertainty.
4. Generates only eligible recovery actions from the strategy catalogue.
5. Predicts the recovery potential of each candidate action.
6. Calculates expected recovery value.
7. Applies deterministic merchant guardrails.
8. Requests approval when required or executes when permitted.
9. Uses verified Razorpay capabilities for the action.
10. Observes the outcome through payment state/webhook data.
11. Attributes recovered revenue to the intervention.
12. Compares performance against a baseline.
13. Updates action/segment effectiveness and can re-plan when appropriate.

---

## 4. What we are NOT building

Do not expand the MVP into:
- a generic merchant chatbot;
- a general AI business assistant;
- a complete AI growth platform;
- a replacement payment gateway;
- a generic retry engine;
- a full subscription-recovery suite;
- a full receivables product;
- a broad agentic-commerce platform;
- production UPI recovery;
- unsupported/private Razorpay integrations.

The broader AI Merchant Copilot / AI Business Growth Strategist is **future scope only**.

---

## 5. Core user flow

```text
Customer payment fails
        ↓
RecoverAI detects revenue at risk
        ↓
Collect payment + customer + order + failure context
        ↓
Diagnose likely reason / situation
        ↓
Consider eligible actions
        ↓
Estimate recovery probability/value
        ↓
Choose best valid action
        ↓
Check guardrails
        ↓
Human approval OR bounded automatic action
        ↓
Razorpay execution
        ↓
Customer payment succeeds/fails
        ↓
Webhook/payment state confirms outcome
        ↓
Record recovered amount
        ↓
Compare with baseline
        ↓
Learn / re-plan
```

---

## 6. Baseline and proof of value

The baseline is the simple strategy we compare RecoverAI against.

**MVP baseline:** fixed retry-style policy where eligible failed payments receive the same simple recovery treatment.

The exact baseline implementation must be documented before evaluation. It must be deterministic and run on the same held-out records as RecoverAI.

Primary metric:

> **Incremental Recovered GMV = RecoverAI recovered GMV − Baseline recovered GMV**

Also measure:
- recovery rate;
- recovered GMV;
- uplift vs baseline;
- intervention success rate;
- false-intervention cost/rate;
- policy violations;
- tool failure rate;
- prediction calibration;
- expected vs actual recovery.

Never invent final uplift numbers. All final metrics must come from the controlled evaluation.

---

## 7. Synthetic evaluation

Build a reproducible controlled simulator before relying on the UI.

Target scale:
- 20,000–50,000 payment records;
- thousands of customers;
- multiple failure reasons;
- multiple payment methods;
- previous payment/recovery history;
- intervention outcomes.

The data must encode controlled, explainable patterns rather than arbitrary random labels.

Example pattern:
- repeated card failures + successful alternative-method history → higher Payment Link recovery potential;
- temporary/network issue → higher delayed-retry potential;
- repeated unsuccessful attempts → lower value of another intervention.

Use an 80/20 train/held-out split.

The model must be evaluated on unseen held-out data.

---

## 8. Recovery actions

Initial candidate catalogue:
- retry/delayed retry **only if supported by the verified implementation environment**;
- Standard Razorpay Payment Link;
- reminder/payment-link resend where supported;
- no action;
- human review.

Do not claim an action is executable until the actual Razorpay MCP/API environment has been verified.

### Test-mode execution decision
The primary real execution path for the demo is:

**Standard Razorpay Payment Link in Test Mode.**

Do not make UPI Payment Links a Test Mode dependency.

---

## 9. Decision engine

For every candidate action:

```text
1. Check eligibility
2. Estimate probability of recovery
3. Estimate expected recovery value
4. Account for known action/incentive/friction costs where modeled
5. Apply merchant policy
6. Select highest valid action
7. If confidence is insufficient → human review or no action
```

Conceptual scoring:

`Expected Net Recovery = P(recovery | context, action) × recoverable_amount − action_cost − expected_incentive_cost − friction_cost`

The cost model is **TO VALIDATE** for the MVP. Do not create fake precision around cost estimates.

### Deterministic vs AI boundary
**Deterministic code:** arithmetic, thresholds, policy, eligibility, idempotency, state checks.  
**ML/statistics:** recovery probability, intervention effectiveness, calibration.  
**LLM/agent:** contextual investigation, tool selection/sequence, candidate reasoning, explanation, re-planning.

---

## 10. Guardrails

Minimum rules:
- maximum recovery attempts;
- maximum customer contacts;
- minimum confidence threshold;
- maximum incentive/discount if incentives are enabled;
- high-value actions require approval;
- payment already successful → STOP;
- refunded/cancelled state → STOP where applicable;
- opted-out customer → STOP;
- duplicate action → BLOCK;
- model cannot override merchant policy;
- tool failure → bounded retry, then stop/replan/human review.

All material decisions and actions must be auditable.

---

## 11. Razorpay integration

Phase 0 must verify the actual connected environment before implementation depends on it.

Verify:
- MCP connection;
- exact exposed tools;
- payment read access;
- order read access;
- order-payment lookup if exposed;
- Payment Link creation;
- Payment Link state retrieval;
- Test Mode success;
- Test Mode failure;
- webhook/event path;
- outcome persistence.

Do not assume tool names from documentation are available in the team's environment. Capture the actual tool list and update integration notes.

Never request or commit secrets into the repository.

---

## 12. System architecture

```text
Merchant UI
   ↓
FastAPI API
   ↓
Agent Orchestrator / State Machine
   ↓
Context Builder → Diagnosis
   ↓
Decision Engine / Recovery Predictor
   ↓
Guardrail Engine
   ↓
Approval or Auto-Act
   ↓
Razorpay MCP/API Adapter
   ↓
Standard Payment Link / verified action
   ↓
Webhook + Payment State
   ↓
Outcome Processor
   ↓
PostgreSQL
   ↓
Measurement + Learning
   ↓
Re-plan
```

Recommended stack:
- Python
- FastAPI
- PostgreSQL
- Pandas/SQL
- Logistic Regression or XGBoost initially
- tool-calling LLM
- lightweight state machine or LangGraph if justified
- Razorpay MCP/API
- React/Next.js

Do not introduce additional infrastructure without a concrete requirement.

---

## 13. Data model — minimum entities

### Payment
`payment_id, order_id, customer_id, amount, timestamp, method, status, error_source, error_step, error_reason`

### Customer
`customer_id, successful_payment_methods, failure_counts, AOV, recency, frequency`

### Order
`order_id, customer_id, amount, timestamp, product/category`

### Intervention outcome
`payment_id, intervention, success, recovered_amount, time_to_recovery`

### Merchant policy
`approval_thresholds, max_contacts, max_attempts, max_incentive, confidence_threshold`

### Agent/action audit
Store decision, reason, confidence, candidate scores, policy result, approval, tool call/result, outcome, timestamps, and stop reason.

---

## 14. Demo flow

### 0:00–0:30
Show revenue at risk from a seeded failed-payment batch.

### 0:30–1:15
Select one failed payment and show context gathering.

### 1:15–2:00
Show candidate actions and the selected intervention with explanation.

### 2:00–3:00
Approve/execute a Standard Razorpay Payment Link in Test Mode and complete a test payment.

### 3:00–4:00
Show held-out batch results: RecoverAI vs baseline.

### 4:00–4:30
Inject a failure such as action/API failure or already-completed payment and show safe stopping/re-planning.

### 4:30–5:00
Show predicted vs actual outcome and the learning/re-planning story.

Closing line:

> **Razorpay already knows when a payment fails. RecoverAI decides what should happen next — and proves whether it recovered more money.**

---

## 15. Implementation order — LOCKED

### Phase 0 — Integration validation
Do this first.

### Phase 1 — Simulator + baseline
Build the controlled dataset and simple baseline.

### Phase 2 — Decision engine
Build context, prediction, scoring, guardrails and held-out evaluation.

### Phase 3 — Agent orchestration
Implement Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Re-plan.

### Phase 4 — Razorpay execution
Implement the verified Razorpay adapter and Payment Link flow.

### Phase 5 — Outcome attribution
Connect webhooks/payment states to recovery outcomes.

### Phase 6 — Frontend
Build only the views needed to demonstrate the complete loop.

### Phase 7 — Demo hardening
Seed scenarios, failure injection, metrics, audit trail, and 5-minute presentation.

**Do not start with frontend polish.**

---

## 16. Acceptance criteria for the MVP

The MVP is not considered complete until it can:

1. Identify an eligible failed payment.
2. Build its context.
3. Produce a structured diagnosis.
4. Compare at least two candidate interventions.
5. Select an action using measurable decision logic.
6. Respect guardrails.
7. Require approval when configured.
8. Execute a verified Razorpay Test Mode action.
9. Observe a success/failure outcome.
10. Attribute recovered value.
11. Run batch evaluation on held-out data.
12. Compare against the baseline.
13. Show incremental recovered GMV.
14. Demonstrate one graceful failure.
15. Produce an audit trail.

---

## 17. Non-negotiable honesty rules

- Synthetic results must be labelled synthetic/simulated.
- Final performance numbers must come from the actual evaluation run.
- Do not claim guaranteed revenue uplift.
- Do not claim capabilities that the connected Razorpay environment has not exposed and tested.
- Do not describe RecoverAI as replacing Razorpay's existing recovery systems.
- Do not call a static LLM recommendation an autonomous agent.
- Do not use UPI Payment Links as a Test Mode requirement.
- If a decision cannot be justified by available data, choose review/no-action rather than inventing confidence.

---

## 18. Final product positioning

### Short pitch
> **RecoverAI is a context-aware revenue recovery agent for Razorpay merchants. When a payment fails, it investigates the customer and payment context, predicts which recovery action is most likely to work, applies merchant guardrails, executes the action, and measures whether it actually recovered more revenue than a simple recovery policy.**

### Core differentiation
> **We are not building another retry engine. We are building the decision layer that chooses the right recovery intervention for each failed payment and proves its incremental value.**

### Final product decision
**BUILD RECOVERAI.**

**Track:** AI Revenue Recovery  
**MVP wedge:** failed-payment recovery  
**Core differentiator:** context-aware intervention selection  
**Primary proof:** incremental recovered revenue vs baseline  
**Real integration proof:** Standard Razorpay Payment Link in Test Mode
