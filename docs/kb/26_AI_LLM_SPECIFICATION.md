# AI / LLM Specification

## Deterministic Logic
Use code/SQL for:
- amount/revenue calculations
- aggregation
- eligibility
- policy limits
- state transitions
- idempotency
- metric computation

## Statistical / ML Logic
Use a simple model initially for:
- recovery probability
- action effectiveness
- calibration

Candidate first model: Logistic Regression; XGBoost can be evaluated if dataset structure justifies it.

## LLM / Agent Logic
Use LLM reasoning for:
- contextual investigation
- interpreting failure/order/customer evidence
- generating structured diagnosis
- explaining candidate trade-offs
- tool sequencing
- re-planning after new outcomes

## LLM Output Principle
Prefer structured JSON/schema-constrained outputs. Never let free-form LLM text directly execute an external action without deterministic validation.

## Prompting
Prompts should instruct the model to:
- use only supplied/verified context,
- state uncertainty,
- choose only from allowed strategies,
- never override policy,
- return structured reasoning fields.

Exact model/provider is **TO VALIDATE**.
