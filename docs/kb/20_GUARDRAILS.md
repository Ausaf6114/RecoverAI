# Guardrails

## Core Rules
- Maximum recovery attempts: **example policy; final value TO VALIDATE**
- Maximum automated contacts: **example policy; final value TO VALIDATE**
- Minimum confidence: **example 65%; final value TO VALIDATE**
- Maximum incentive: **example 10%; final value TO VALIDATE**
- High-value action may require approval.
- If payment is already successful: STOP.
- If terminal/refunded state: STOP.
- If duplicate action exists: STOP.
- If customer has opted out where applicable: STOP.
- Model recommendation cannot override policy.
- Tool failures use bounded retry then stop/replan.
- Every material decision/action is audited.

## Safety Principle
Guardrails are deterministic and authoritative. The LLM cannot bypass them.

## Regulatory / Legal
No new regulatory requirements should be invented here. Specific privacy, consent, communications, and financial compliance requirements are **TO VALIDATE** for the deployment context.
