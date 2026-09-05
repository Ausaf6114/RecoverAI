# RecoverAI — Final Implementation Roadmap
### Cross-verified against your knowledge base + current Antigravity + Razorpay MCP capabilities (Sept 2026)

---

## 1. Verdict on your knowledge base

Your KB (39 files) is unusually well-structured for a hackathon — most teams don't have a documented decision hierarchy, guardrail spec, or honesty rules ("never fabricate a number"). It is **implementation-ready**, not just an idea doc. A few things need tightening before you hand it to Antigravity:

### What's solid — keep as-is
- The **Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Re-plan** loop is a genuinely good agentic framing for judges — it's a real state machine, not a chatbot wrapper.
- The **deterministic vs ML vs LLM boundary** (18_DECISION_ENGINE, 26_AI_LLM_SPEC) is exactly right and will save you from the #1 hackathon AI-agent failure mode: judges asking "wait, is the LLM actually doing anything, or is this just an if/else tree with a chat wrapper on top?" Your architecture lets you answer that cleanly.
- **Standard Payment Link in Test Mode as the real-execution proof, explicitly avoiding UPI Payment Links** — this is correct and current. UPI Payment Links still are not supported in Razorpay Test Mode, so this constraint is real, not outdated.
- The **incremental-GMV-vs-baseline** metric and the "never fabricate a number" rule is the right north star for a "Revenue Recovery" track — judges will trust a modest real number over an impressive fake one.

### Gaps / things to fix before build
1. **No named LLM/model.** `26_AI_LLM_SPECIFICATION.md` marks the model as "TO VALIDATE." You need to lock this now — see §3.
2. **No hosting decision.** `38_TECH_STACK.md` marks deployment as "TO VALIDATE." A hackathon submission needs a live URL — decide now, not on demo day.
3. **Cost model is hand-wavy.** The expected-value formula (`P(recovery) × amount − costs`) is fine, but for MVP, just set `action_cost` and `friction_cost` to small fixed constants (e.g. ₹0 for a Payment Link resend, a friction penalty that increases with `attempt_number`) rather than trying to model them precisely. Don't burn hackathon time here — deterministic constants are enough, and it keeps your "no fake precision" rule intact.
4. **Webhook signature verification isn't spelled out.** `30_SECURITY_AND_PRIVACY.md` says "validate webhook authenticity per official requirements" but doesn't say how. Razorpay webhooks are HMAC-SHA256 signed with a webhook secret you set in the dashboard — verify this in Phase 0, not Phase 4, or you'll build against fake webhook data all the way through.
5. **LangGraph is listed as optional** ("only if it materially improves..."). For a 5-person-week hackathon build, skip it. A plain Python state machine (a `dict`-based state object passed through pure functions, persisted to Postgres between steps) is faster to build, easier to debug live during judging, and just as demonstrable. Reserve LangGraph for the "Learning" future-scope notes if you want to namedrop it in the pitch.
6. **No mention of what LLM framework/SDK you'll call.** Decide: raw Anthropic/Gemini SDK with function-calling + Pydantic-validated structured output (`response_model` style), not an agent framework. This matches your own principle #26: "never let free-form LLM text directly execute an action without deterministic validation."
7. **"MVP boundary" doesn't mention rate limiting / concurrency**, which matters once you're running a batch simulation of 20–50k payments through an LLM call per opportunity — that's expensive and slow. See §5 for the fix (only call the LLM for diagnosis/explanation on a sampled subset + demo cases; use the ML model for the batch-scale probability scoring, exactly as your own AI boundary already specifies).

None of this changes your architecture — it just closes the "TO VALIDATE" gaps your own docs flagged, so Antigravity isn't left guessing mid-build.

---

## 2. What exactly are we building (plain description)

**RecoverAI** is an AI agent for Razorpay merchants that sits between "a payment just failed" and "what happens next." Instead of applying one fixed retry/reminder rule to every failed payment, it:

1. Pulls the payment, order, and customer context (amount, failure reason, payment method, past behavior).
2. Diagnoses *why* it likely failed (auth failure, insufficient funds, network blip, etc.) using an LLM reasoning over that structured context.
3. Scores every eligible recovery action (retry, send a Payment Link, remind, do nothing, escalate to human) using a small ML model trained on historical outcomes, picking the one with the highest expected recovered value.
4. Runs the action through deterministic guardrails (attempt limits, confidence threshold, duplicate checks, already-paid checks).
5. Executes the approved action for real via the **Razorpay MCP server** — creating and sending a Standard Payment Link in Test Mode.
6. Listens for the Razorpay webhook confirming payment success/failure, attributes the recovered amount back to the action.
7. Compares its cumulative recovered GMV against a simple fixed-policy baseline on a large synthetic held-out dataset, and reports the incremental lift.

It is a **decision + measurement layer on top of Razorpay**, not a payment gateway, not a chatbot, not a retry engine.

---

## 3. Final tech stack (locked)

| Layer | Choice | Why |
|---|---|---|
| **Language (whole project)** | **Python** (backend/agent/ML) + **TypeScript** (frontend) | Matches your KB, matches what Antigravity + Gemini/Claude tool-calling ecosystems are strongest in, and Pydantic gives you the structured-output validation your own AI spec requires. |
| **Backend framework** | **FastAPI** | As specified. Async-native, auto OpenAPI docs (useful for judges to poke at), clean dependency injection for DB/session. |
| **Database** | **PostgreSQL** (hosted on **Supabase** or **Neon**, free tier) | As specified. Supabase/Neon give you a managed Postgres + connection pooling with zero DevOps — critical when you have ~1–2 weeks. |
| **ORM/migrations** | **SQLAlchemy 2.0 + Alembic** | Standard, works cleanly with FastAPI + Pydantic v2. |
| **Agent orchestration** | **Plain Python state machine** (no LangGraph) | See gap #5 above. One `RecoveryOpportunityState` dataclass, one `run_step()` per stage, persisted to a `agent_decisions` table after each transition. Faster to build, trivially explainable to judges, matches "do not use an LLM where deterministic logic is sufficient." |
| **LLM** | **Claude (Sonnet, via Anthropic API, tool-calling + structured JSON output)** for diagnosis/explanation/re-planning reasoning | Pick one vendor and commit — don't burn time multi-provider testing. Claude's tool-use + strict JSON mode fits your "never let free text execute an action" rule well. (If you build inside Antigravity, Gemini 3 is also available natively and free-tier friendly — either is fine; the important thing is picking **one** and locking it in Phase 0, not leaving it "TO VALIDATE.") |
| **ML model** | **scikit-learn LogisticRegression** for `P(recovery | context, action)`, calibrated with `CalibratedClassifierCV` | As specified — matches "start simple, escalate to XGBoost only if justified." Logistic regression is also trivially explainable in a judging Q&A ("here are the 6 features and their coefficients"). |
| **Data/analytics** | **Pandas** for the simulator + baseline/held-out evaluation notebooks | As specified. |
| **Payments** | **Razorpay MCP Server (Remote)** — read (`fetch_payment`, `fetch_all_payments`, `fetch_order`, `fetch_order_payments`) + write (`create_payment_link`) tools, called from your FastAPI backend as the tool layer behind the agent | See §6 for the exact tool list. |
| **Frontend** | **Next.js 14 (App Router) + TypeScript + Tailwind + shadcn/ui + Recharts** | React/Next as specified; Tailwind + shadcn gets you a professional-looking merchant dashboard fast without hand-rolling CSS — important since your own docs say "decision detail and impact comparison matter more than visual complexity," so don't overspend here. |
| **Auth (merchant login, MVP)** | Simple single-tenant API key or Supabase Auth email/password | You don't need multi-tenant merchant auth for a hackathon demo — one seeded merchant is enough. Don't over-build this. |
| **Testing** | **Pytest** (unit + integration) + a scripted **demo-scenario replay** | As specified. |
| **Deployment (backend + DB)** | **Render** or **Railway** (FastAPI + worker + Postgres) | Zero-DevOps, free/cheap tier, supports background workers for webhook processing and the batch simulator, gives you a stable public HTTPS URL for the Razorpay webhook. |
| **Deployment (frontend)** | **Vercel** | Native Next.js hosting, instant preview URLs — useful if you're iterating with Antigravity's agent making frequent commits. |
| **Webhooks** | Razorpay webhook → your Render backend endpoint, verified via **HMAC-SHA256 signature check** using the webhook secret from the Razorpay Dashboard (Test Mode) | Confirms real payment-link completion in the demo. |
| **Repo/CI** | GitHub + GitHub Actions (lint + pytest on push) | Antigravity commits directly to this repo; Actions gives you a green-checkmark to show judges your code is actually tested. |

**One deliberate change from your KB:** dropping LangGraph as a default (kept as a "could mention in future scope" line), and explicitly naming Claude (or Gemini, if you build fully inside Antigravity's native model) as the locked LLM instead of leaving it open. Everything else in your `38_TECH_STACK.md` is kept as-is because it was already the right call.

---

## 4. System architecture (final)

```
Next.js Dashboard (Vercel)
        │  REST (JSON)
        ▼
FastAPI Backend (Render)
        │
   ┌────┴─────────────────────────────────────────┐
   │  Agent Orchestrator (plain Python state machine) │
   └────┬─────────────────────────────────────────┘
        │
        ├─► Context Builder  ──► reads: payments/orders/customers (Postgres, mirrored from Razorpay MCP fetch tools)
        ├─► Diagnosis (Claude tool-call, structured JSON output, temp=0)
        ├─► Recovery Predictor (scikit-learn Logistic Regression, served in-process)
        ├─► Decision Engine (deterministic expected-value scoring)
        ├─► Guardrail Engine (deterministic policy checks)
        ├─► Action Executor ──► Razorpay MCP Server (create_payment_link, fetch_payment_link)
        │                          │
        │                          ▼
        │                   Razorpay Test Mode
        │                          │
        │            (customer completes/fails test payment)
        │                          ▼
        └─◄──────────── Webhook: payment_link.paid / payment.failed
                                   │
                                   ▼
                        Outcome Processor → Postgres
                                   │
                                   ▼
                    Measurement (baseline vs RecoverAI, incremental GMV)
                                   │
                                   ▼
                          Learning update (segment/action effectiveness table)
```

Batch synthetic evaluation (20–50k records) runs as a **separate offline Pandas job**, not through the live FastAPI request path — this avoids hammering the LLM per-record (see gap #7). Only the demo's live opportunities go through the full LLM-diagnosis path; the batch evaluation uses the ML probability model directly, exactly matching your own "ML/statistics: recovery probabilities" boundary.

---

## 5. Exact roadmap to build this in Antigravity

Antigravity (Google's agentic IDE, VS Code–based, with a "Manager Surface" for spawning/orchestrating agents and an "Editor View" for direct coding) is well suited to this project because your KB is already broken into discrete, well-scoped tasks (`33_TASK_BREAKDOWN.md`) — that's exactly the granularity its agent planning works best with. Here's how to run it, phase by phase, matching your KB's locked implementation order:

### Setup (before Phase 0)
1. Install Antigravity, sign in with your Google account, select your primary model (Gemini 3 Pro is native and free-tier; you can also point it at Claude Sonnet if you prefer — Antigravity supports both).
2. Create a fresh GitHub repo (`recoverai`), open it in Antigravity.
3. **Feed Antigravity your knowledge base first.** Drop the whole `RecoverAI/` folder into the repo under `/docs/kb/`, and in your first Manager Surface task, tell it explicitly: *"Read every file in /docs/kb before planning anything. FINAL_IMPLEMENTATION_HANDOFF.md and this roadmap file are the source of truth — treat older docs as historical only."* This is exactly what the "artifacts" (auto-generated task/plan docs) feature is good at digesting.
4. Get your Razorpay **Test Mode** API Key + Secret, and set up the Remote Razorpay MCP server connection (via `npx` — zero local install) inside Antigravity's MCP/tool config, or in your own FastAPI backend if you're calling the API directly rather than through MCP inside the IDE.

### Phase 0 — Integration validation (do this yourself, not the agent, first)
Spend an hour manually verifying, before you let Antigravity build anything on top of it:
- Razorpay Remote MCP connects; run `fetch_payment`, `fetch_all_payments`, `fetch_order` against your Test Mode account and confirm real responses.
- Run `create_payment_link` in Test Mode, open the link, complete a test payment with a Razorpay test card.
- Set up a webhook (Dashboard → Webhooks, Test Mode) pointing at a temporary tunnel (ngrok) or your first Render deploy; confirm the `payment_link.paid` event arrives and the HMAC signature check passes.
Write down the **exact tool names and payload shapes** you actually got back — this becomes your integration notes file, replacing every "TO VALIDATE" in the KB related to Razorpay.

### Phase 1 — Data foundation (Antigravity task)
Prompt Antigravity's Manager Surface: *"Build the Postgres schema from /docs/kb/16_DATA_MODEL.md and 25_DATABASE_SPECIFICATION.md using SQLAlchemy + Alembic, then build the synthetic data generator from 27_MOCK_DATA_SPECIFICATION.md producing 30,000 payments with the controlled patterns listed, 80/20 train/held-out split, plus the fixed baseline policy from 21_MEASUREMENT_AND_EXPERIMENTATION.md."* Review the generated plan artifact before letting it execute — Antigravity shows you a walkthrough doc first; check the patterns are actually encoded (not just random labels) before approving.

### Phase 2 — Decision core (Antigravity task, split into 3 sub-agents if useful)
- Context builder (reads Postgres, returns structured `PaymentContext`)
- Recovery predictor (train the Logistic Regression on the training split, expose `.predict_proba`)
- Decision engine + guardrail engine (deterministic; write these as plain, heavily unit-tested Python — this is the part where you want to review every line, since it's your core IP)

### Phase 3 — Agent orchestration
Have Antigravity wire the state machine: `detect → diagnose → decide → guardrail → execute → measure → learn → replan`, with the Claude/Gemini diagnosis call as one step, schema-validated with Pydantic before anything downstream reads it.

### Phase 4 — Razorpay execution
Wrap the verified MCP tool calls from Phase 0 into an `ActionExecutor` with idempotency keys (store `razorpay_payment_link_id` uniquely) and the webhook receiver + HMAC verification.

### Phase 5 — Outcome attribution + Phase 6 — Frontend
Build the outcome processor, then the 6 pages from `24_FRONTEND_SPECIFICATION.md` in Next.js. This is where Antigravity's browser-automation extension is genuinely useful — it can visually verify the dashboard renders correctly and click through the approval flow itself before you do.

### Phase 7 — Demo hardening
Seed the exact demo scenarios from `28_TESTING_STRATEGY.md` (high-confidence recovery, low-confidence stop, duplicate/completed-payment stop, forced tool failure, batch uplift view) as fixture data so the 5-minute demo is scripted and repeatable, not live-random.

**Working style inside Antigravity:** use the Manager Surface for whole-feature tasks (a phase = one agent task with its own artifact/walkthrough), and drop into Editor View yourself for the decision engine, guardrails, and scoring math — the parts judges will most likely ask you to explain line-by-line. Let the agent handle boilerplate (CRUD routes, Pydantic schemas, Alembic migrations, Tailwind components); you own the scoring formula and guardrail logic.

---

## 6. What exactly to take from Razorpay

You're building this **on top of the official Razorpay MCP Server** (`razorpay/mcp` — remote hosted, zero setup, `npx`-installable, or Docker for local). From its 35+ tools, you need:

**Reads (context building):**
- `fetch_payment` — payment status + failure fields for the individual opportunity
- `fetch_all_payments` — batch pull for populating your synthetic-context tables / cross-checking real Test Mode data
- `fetch_order`, `fetch_order_payments` — order-level and order→payment linkage
- `fetch_payment_card_details` (optional) — richer diagnosis signal if a card failure is involved

**Writes (execution):**
- `create_payment_link` — the **Standard** Payment Link (not `create_payment_link_upi`; UPI Payment Links aren't supported in Test Mode)
- Payment Link fetch/status tool (to poll link state as a fallback if the webhook is delayed)

**Events:**
- Razorpay **Webhooks** (Test Mode) — `payment_link.paid`, `payment.failed`, subscribed via the Dashboard, verified with HMAC-SHA256 using your webhook secret.

**Do not use:** Settlements, Payouts, Refunds, QR Code tools, or `capture_payment` — none of these are in your MVP scope, and pulling them in would blur your "we are a decision layer, not a payments product" positioning.

**Also pull from Razorpay for the pitch, not the code:** their public documentation on Agent Studio's Subscription Recovery / Abandoned Cart Conversion specialist agents (referenced in your own `05_RAZORPAY_ALIGNMENT.md`) — cite these explicitly in your judging deck as "the systems we complement," since naming them by name (correctly, respectfully) is stronger positioning than a vague "existing recovery tools."

---

## 7. Deployment plan

1. **Backend + worker + Postgres:** deploy FastAPI to Render (or Railway) as a Web Service; add a background worker (or Render Cron) for the batch simulator job so it doesn't block the API. Use Render's managed Postgres or an external Neon/Supabase instance.
2. **Frontend:** deploy Next.js to Vercel, pointed at the Render backend's public URL via an environment variable.
3. **Webhook endpoint:** `https://<your-render-app>.onrender.com/webhooks/razorpay` registered in the Razorpay Dashboard (Test Mode), secret stored as a Render environment variable — never in the repo.
4. **Secrets:** Razorpay Key/Secret, webhook secret, and your LLM API key all live in Render/Vercel environment variable stores — matches `30_SECURITY_AND_PRIVACY.md`'s "never expose credentials to frontend, never commit secrets" rule.
5. **Submission link:** a stable Vercel URL for the dashboard is what you'll paste into the buildathon submission form; keep Test Mode active there permanently so judges can click through it after your live demo too.

---

## 8. For the submission form — "What problem is it solving?"

Use this (trim to the form's character limit as needed):

> **Failed payments create revenue at risk, but merchants apply the same recovery action to every failure regardless of context — the actual gap is that "a payment failed" doesn't tell you "what to do next." RecoverAI closes that decision gap: for every failed payment it investigates the payment, order, and customer context, diagnoses the likely cause, predicts which eligible recovery action (retry, Payment Link, reminder, or no action) has the highest expected recovered value, enforces merchant guardrails, executes the action for real through Razorpay, and measures whether it actually recovered more revenue than a fixed baseline policy — proving incremental impact rather than just automating an existing workflow.**

---

## 9. Answering your direct questions

- **What language:** Python (backend, agent, ML) + TypeScript (Next.js frontend). No other languages needed.
- **What are we building:** see §2 — a context-aware recovery *decision and measurement layer* on top of Razorpay, not a new payment product.
- **How are we deploying:** Render/Railway (API + Postgres) + Vercel (frontend) — see §7.
- **What do we take from Razorpay:** the official Razorpay MCP Server's payment/order read tools + `create_payment_link` (Standard, Test Mode) + webhooks — see §6.
- **Antigravity's role:** it's your build environment — feed it the KB + this roadmap as source of truth, let it execute the phase-by-phase task breakdown from `33_TASK_BREAKDOWN.md`, review its generated plans before approving execution, and keep the scoring/guardrail logic under your own direct edit since that's your defensible IP for judging.
