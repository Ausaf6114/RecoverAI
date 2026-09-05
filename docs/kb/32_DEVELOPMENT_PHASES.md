# Development Phases

| Phase | Objective | Dependencies | Deliverables | Acceptance |
|---|---|---|---|---|
| 0 | Validate external integration | Test account | MCP/tool/read/action smoke test | real Test Mode flow works |
| 1 | Build data foundation | Phase 0 | DB + simulator | reproducible dataset |
| 2 | Build decision engine | Phase 1 | context/model/strategy/guardrails | controlled cases select correctly |
| 3 | Build agent loop | Phase 2 | orchestration | end-to-end local workflow |
| 4 | Connect execution | Phase 0/3 | Payment Link + webhook | action/outcome attributed |
| 5 | Build UI | Phase 3/4 | merchant dashboard | demo flow usable |
| 6 | Evaluate | Phase 1–5 | baseline/held-out metrics | measurable incremental recovery |
| 7 | Demo hardening | Phase 6 | script/scenarios | reliable 5-minute demo |
