# MVP Scope — FINAL LOCKED

## Objective
Prove that RecoverAI can make better failed-payment recovery decisions than a simple fixed recovery policy, execute at least one real Razorpay Test Mode recovery action, and measure the resulting outcome.

## MUST HAVE
- Controlled synthetic failed-payment dataset.
- Reproducible recovery simulator.
- Fixed baseline policy.
- 80/20 train/held-out evaluation.
- Context builder.
- Structured diagnosis.
- Candidate strategy catalogue.
- Recovery probability/scoring model.
- Expected-value decisioning.
- Deterministic guardrails.
- Human approval path where configured.
- Audit trail.
- Standard Razorpay Payment Link Test Mode execution.
- Outcome verification.
- Baseline vs RecoverAI batch metrics.
- Incremental recovered GMV calculation.
- Merchant-facing recovery decision view.
- One graceful failure scenario.

## SHOULD HAVE
- Re-planning demonstration.
- Prediction-vs-actual view.
- Segment-level evaluation.
- Explicit confidence calibration.

## NICE TO HAVE
- Additional verified recovery actions.
- Rich frontend animations.
- Voice/Hinglish recovery prototype.

## OUT OF SCOPE
- Generic AI merchant chatbot.
- Broad AI Business Growth Agent.
- Full agentic commerce platform.
- Production UPI recovery dependency.
- Full subscription recovery product.
- Full receivables product.
- Production-scale merchant deployment.
- Unsupported/private Razorpay APIs.
