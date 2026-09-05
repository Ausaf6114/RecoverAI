# Agent Architecture

## Detect
**Input:** payment failure/event.  
**Output:** recovery opportunity.  
**Tools:** payment/order reads.  
**Failure:** event missing or duplicate.

## Diagnose
**Input:** opportunity + context.  
**Output:** structured failure hypothesis and uncertainty.  
**Tools:** context retrieval.  
**Guardrail:** do not invent facts.

## Decide
**Input:** context + candidate actions + model estimates.  
**Output:** ranked action + confidence + expected value + explanation.

## Guardrail
**Input:** proposed action.  
**Output:** allow / require approval / reject / stop.

## Execute
**Input:** approved action.  
**Output:** action ID/status.  
**Failure:** bounded retry, then stop/replan.

## Measure
**Input:** action + subsequent payment state.  
**Output:** recovered amount, recovery outcome, attribution.

## Learn
**Input:** historical outcomes.  
**Output:** updated action/segment effectiveness.

## Re-plan
**Input:** new evidence or failed action.  
**Output:** next eligible action or stop.

## Agent State
- opportunity_id
- payment_id
- context snapshot
- diagnosis
- candidate actions
- scores
- selected action
- policy result
- execution status
- outcome
- learning update
