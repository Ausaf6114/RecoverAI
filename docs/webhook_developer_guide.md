# Razorpay Webhook Receiver Developer Guide

Phase 0 Task `P0-04` introduces the webhook infrastructure for handling asynchronous Razorpay payment and recovery link events.

---

## 1. Webhook Endpoint

* **Route:** `POST /webhooks/razorpay`
* **Content-Type:** `application/json`
* **Key Headers:**
  * `X-Razorpay-Signature`: Hex-encoded HMAC-SHA256 digest of the raw request body. *(Required)*
  * `x-razorpay-event-id`: Razorpay unique event identifier. *(Recommended for idempotency)*

---

## 2. Environment Variables

Add to `.env` (kept out of version control):
```bash
RAZORPAY_WEBHOOK_SECRET="your_webhook_secret_from_razorpay_dashboard"
```
> [!IMPORTANT]
> `RAZORPAY_WEBHOOK_SECRET` is completely distinct from the API Key Secret (`TEST_KEY_SECRET`). Never conflate the two or commit secrets into Git.

---

## 3. Signature Verification Architecture

1. The raw, unparsed request body (`bytes`) is read directly before parsing JSON.
2. The expected signature is computed:
   $$\text{HMAC-SHA256}(\text{RAZORPAY\_WEBHOOK\_SECRET}, \text{raw\_body})$$
3. Verification is performed using Python's `hmac.compare_digest` to prevent timing attacks.
4. If missing or invalid, the endpoint immediately responds with `400 Bad Request` without parsing or persisting any data.
5. If the JSON payload is malformed, it is safely rejected with `400 Bad Request` without crashing.

---

## 4. Race-Safe Idempotency Behavior

* **Primary Key:** `x-razorpay-event-id` (falling back to `payload.id` or deterministic SHA-256 hash of payload).
* **Database Constraint:** `webhook_events.event_id` is defined as `PRIMARY KEY` in SQLite.
* **Concurrency Protection:** Concurrent requests with identical event IDs trigger an atomic SQLite unique constraint catch (`sqlite3.IntegrityError`), ensuring exactly one execution and returning:
  ```json
  {
    "status": "duplicate",
    "event_id": "evt_...",
    "message": "Event already processed"
  }
  ```
  with HTTP `200 OK` so the webhook sender does not retry unnecessarily.

---

## 5. Supported Event Types

The receiver defensively parses:
* **`payment.captured`**: Extracts `payment_id`, `order_id`, `amount`, `currency`, `status`.
* **`payment.failed`**: Extracts `payment_id`, `order_id`, `amount`, `error_code`, `error_description`.
* **`payment_link.paid`**: Extracts `payment_link_id`, `payment_id`, `order_id`, `amount`, `status`.

---

## 6. Running Automated Tests

Run the test suite using `pytest`:
```bash
pytest -v tests/test_webhooks.py
```
*(All tests run in isolated temporary SQLite databases with synthetic secrets).*
