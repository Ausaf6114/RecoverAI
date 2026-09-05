# System Architecture

```text
Merchant / UI
     ↓
FastAPI API Layer
     ↓
Agent Orchestrator
     ↓
Context Engine ──→ Diagnosis Engine
     ↓                   ↓
     └────────→ Decision Engine
                    ↓
               Guardrail Engine
                    ↓
              Approval / Auto-act
                    ↓
              Action Executor
                    ↓
              Razorpay MCP/API
                    ↓
             Payment Link / Action
                    ↓
               Webhook/Event
                    ↓
             Outcome Processor
                    ↓
                  DB
                    ↓
          Measurement + Learning
                    ↓
                Re-plan
```

## Components
- Frontend: merchant views and approval.
- API: REST interface.
- Orchestrator: stateful agent workflow.
- Context Engine: gathers structured evidence.
- Diagnosis Engine: failure hypothesis.
- Decision Engine: action scoring/selection.
- Guardrail Engine: deterministic policy enforcement.
- Action Executor: Razorpay tool wrapper.
- Measurement: baseline and outcome analytics.
- Learning: update action effectiveness.
- Database: persistent state/audit.
- Simulator: large-scale synthetic evaluation.

## Boundary Principle
Real Razorpay integration proves execution; synthetic simulation proves batch-scale impact.
