# Demo Script

**Opening:** “Every failed payment is revenue at risk, but not every failure deserves the same recovery action.”

**Show dashboard:** “RecoverAI has identified this batch of failed payments and the associated revenue at risk.”

**Open case:** “This payment failed. Instead of immediately retrying, RecoverAI gathers payment, order, customer, and historical context.”

**Decision:** “It evaluates eligible interventions and predicts which has the best expected recovery value under the merchant's policy.”

**Guardrail:** “The policy checks confidence, duplicate state, attempt limits, and approval requirements.”

**Execute:** “The merchant approves, and RecoverAI creates a Standard Razorpay Payment Link in Test Mode.”

**Outcome:** “We complete the test payment and feed the resulting state back into RecoverAI.”

**Measure:** “At batch scale, we compare RecoverAI against a fixed baseline and measure incremental recovered revenue.”

**Failure:** “If the payment is already complete or the external action fails, RecoverAI stops safely or re-plans.”

**Close:** “Razorpay already knows when a payment fails. RecoverAI decides what should happen next — and proves whether it recovered more money.”
