# User Personas and Use Cases

## Primary Persona — Merchant / Business Operator
**Goal:** recover legitimate revenue without unnecessary customer friction.

### UC-01 Detect Revenue at Risk
- Actor: merchant/system
- Trigger: failed payment/event
- Inputs: payment status, amount, failure context
- Behavior: identify eligible recovery opportunity
- Output: revenue-at-risk record
- Success: eligible failures are correctly surfaced.

### UC-02 Investigate a Failed Payment
- Actor: merchant/recovery agent
- Trigger: recovery opportunity
- Inputs: payment, order, customer history, prior attempts
- Behavior: build contextual profile and diagnosis
- Output: structured context + root-cause hypothesis
- Success: decision-relevant context is available.

### UC-03 Select Recovery Intervention
- Actor: agent
- Trigger: diagnosed opportunity
- Inputs: context, candidate strategies, model scores, policies
- Behavior: score eligible actions and choose best expected value
- Output: recommended action, confidence, explanation
- Success: decision follows policy and baseline comparison is possible.

### UC-04 Execute Recovery
- Actor: agent/merchant
- Trigger: approved eligible decision
- Inputs: selected action
- Behavior: execute through supported Razorpay integration
- Output: action ID/status
- Success: action is executed once and audited.

### UC-05 Track Outcome
- Actor: system
- Trigger: payment/action outcome
- Inputs: webhook/API state
- Behavior: associate outcome with intervention
- Output: recovery outcome
- Success: outcome attribution is persisted.

### UC-06 Evaluate Incremental Impact
- Actor: merchant
- Trigger: experiment/batch completion
- Inputs: baseline and agent outcomes
- Behavior: compare recovery performance
- Output: recovered GMV and incremental recovery
- Success: impact is transparent and attributable.

### UC-07 Safe Stop
- Actor: system
- Trigger: policy violation, uncertainty, duplicate state, completed payment, or tool failure
- Behavior: stop/escalate/replan
- Output: safe terminal state
- Success: no prohibited action is executed.

## Secondary Actors
- Customer: receives/uses recovery communication/payment link.
- Internal system actors: webhook processor, database, model service, audit logger.
