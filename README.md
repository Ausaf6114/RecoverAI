# RecoverAI

**RecoverAI — Context-Aware Revenue Recovery Agent**

> Track: AI Revenue Recovery  
> Core loop: Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Re-plan  
> Primary proof: incremental recovered GMV versus a fixed baseline on held-out evaluation data.  
> Real integration proof: Standard Razorpay Payment Link in Test Mode.

---

## Deployment Guide

### Prerequisites

- Python 3.11+
- pip

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in the required values before running locally.
On cloud platforms (Render, Fly.io, Railway), set these as platform environment variables:

| Variable | Required | Description |
|:---|:---|:---|
| `RAZORPAY_WEBHOOK_SECRET` | **Yes** | Razorpay webhook signing secret (from Dashboard → Webhooks) |
| `PORT` | No | Port to bind (default: `8000`; auto-injected by most cloud platforms) |
| `APP_ENV` | No | `development` or `production` (default: `development`) |
| `DATABASE_PATH` | No | SQLite file path (default: `recoverai.db`; Phase 0 only) |

> ⚠️ **Never commit `.env` to version control.** It is listed in `.gitignore`.

### 3. Start Command

**Local:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Production / Cloud (Render, Fly.io, Railway):**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Set this as the **Start Command** in your cloud platform dashboard.

### 4. Health Check

```
GET /health
```

Returns:
```json
{"status": "healthy", "service": "RecoverAI", "version": "0.1.0"}
```

Use this URL as the **health check path** in your cloud platform configuration.

### 5. Webhook Endpoint

```
POST /webhooks/razorpay
```

- Requires `X-Razorpay-Signature` header (HMAC-SHA256, computed by Razorpay).
- Enforces event idempotency via `x-razorpay-event-id`.
- Rejects malformed JSON with HTTP 400.
- Persists accepted events to SQLite (`recoverai.db`).

### 6. Run Tests

```bash
pytest -v
```

---

## Project Structure

```
app/
  main.py              # FastAPI application entry point
  core/
    config.py          # Settings (env-driven)
    security.py        # HMAC-SHA256 signature verification
  api/
    webhooks.py        # POST /webhooks/razorpay
  db/
    session.py         # SQLite connection management
    events.py          # WebhookEventRepository (idempotency)
  schemas/
    webhook.py         # Defensive Razorpay event parsing
tests/
  test_webhooks.py     # 10-case automated test suite
docs/                  # Project knowledge base and specifications
requirements.txt       # Production dependencies
```

---

## Important

This directory is the project's Single Source of Truth. Research and historical decisions remain preserved, but the final implementation handoff and latest explicit decisions override earlier exploratory ideas.

**Read first:** `docs/FINAL_IMPLEMENTATION_HANDOFF.md`  
**Then:** `docs/kb/00_PROJECT_MASTER.md` and onwards.
