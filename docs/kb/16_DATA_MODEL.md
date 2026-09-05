# Data Model

## Core Entities
### Merchant
merchant_id, name, policy_id, created_at

### Customer
customer_id, merchant_id, history aggregates, preferences/opt-out where available

### Order
order_id, merchant_id, customer_id, amount, currency, created_at

### Payment
payment_id, order_id, customer_id, amount, status, method, failure fields, timestamps

### Payment Attempt
attempt_id, payment_id/order_id, method, status, failure context, timestamp

### Failure
failure_id, payment_id, source, step, reason, normalized_category, observed_at

### Recovery Action
action_id, opportunity_id, strategy, status, parameters, executed_at

### Recovery Outcome
outcome_id, action_id, success, recovered_amount, time_to_recovery, observed_at

### Agent Decision
decision_id, opportunity_id, candidates, scores, selected_action, confidence, rationale, policy_result

### Experiment
experiment_id, name, treatment, baseline, start/end, population rules

### Baseline
baseline_id, strategy, version, metrics

## Relationships
Merchant 1→N Customers/Orders/Payments.  
Order 1→N Payments/Attempts.  
Payment 1→N Failures.  
Opportunity 1→N Decisions/Actions.  
Action 1→1 or N Outcome records depending on retry/action model.  
Experiment 1→N evaluation records.
