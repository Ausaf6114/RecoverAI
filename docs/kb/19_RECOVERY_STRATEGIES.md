# Recovery Strategy Catalogue

## S-01 Standard Payment Link
**Trigger:** eligible failed payment where an alternate payment completion path is appropriate.  
**Eligibility:** payment still recoverable; no duplicate/stop condition.  
**Context:** amount, failure reason, customer history, prior attempts.  
**Expected outcome:** customer completes payment through the link.  
**Risks:** unnecessary contact, duplicate recovery attempt.  
**Guardrails:** contact/attempt limit, payment-state check, idempotency.  
**Execution:** Razorpay Standard Payment Link.  
**Metric:** incremental recovered amount.  
**Fallback:** stop or review if execution fails.

## S-02 Retry / Delayed Retry
**Trigger:** transient failure pattern where retry is eligible.  
**Eligibility:** verified retry capability and policy.  
**Context:** failure source/step/reason, prior attempts.  
**Expected outcome:** subsequent payment succeeds.  
**Risks:** repeated failure/customer friction.  
**Guardrails:** maximum attempts and spacing.  
**Execution:** only if supported by verified integration.  
**Metric:** incremental recovery.  
**Fallback:** alternate eligible strategy or stop.

## S-03 Reminder / Resend
**Trigger:** payment remains incomplete and a communication is allowed.  
**Eligibility:** communication policy satisfied.  
**Context:** prior contact count, customer state.  
**Expected outcome:** customer returns and pays.  
**Risks:** over-contact.  
**Guardrails:** contact limit.  
**Execution:** supported notification/payment-link mechanism.  
**Metric:** recovered GMV per contact.  
**Fallback:** stop.

## S-04 No Action
**Trigger:** low expected value, high friction, repeated failure, or policy stop.  
**Eligibility:** always.  
**Outcome:** no unnecessary intervention.  
**Metric:** avoided intervention cost / false-intervention rate.

## S-05 Human Review
**Trigger:** high-value, uncertain, or policy-sensitive case.  
**Outcome:** merchant decides.  
**Metric:** reviewed recovery value and policy adherence.

The strategy catalogue is intentionally small for MVP.
