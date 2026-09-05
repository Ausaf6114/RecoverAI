# Backend Specification

## Suggested Modules
```text
app/
  api/
  agents/
  context/
  diagnosis/
  decision/
  guardrails/
  actions/
  integrations/
  outcomes/
  analytics/
  models/
  db/
  schemas/
  tests/
```

## Responsibilities
- API: HTTP interface.
- Orchestrator: workflow state.
- Context: data aggregation.
- Diagnosis: normalized failure reasoning.
- Decision: candidate scoring.
- Guardrails: deterministic policy.
- Actions: idempotent external execution.
- Outcomes: webhook/state processing.
- Analytics: baseline and experiment metrics.

## Design Principle
Keep business-critical policy and calculations out of prompt-only logic.
