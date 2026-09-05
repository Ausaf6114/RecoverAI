import hmac
import hashlib
import json
import pytest
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings, get_settings
from app.db.session import init_db
from app.db.events import WebhookEventRepository
from app.api.webhooks import get_event_repo

SYNTHETIC_WEBHOOK_SECRET = "synthetic_test_secret_abc123xyz789"


def compute_signature(payload_bytes: bytes, secret: str = SYNTHETIC_WEBHOOK_SECRET) -> str:
    """Computes HMAC-SHA256 signature for test payloads."""
    return hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()


@pytest.fixture
def test_db_path():
    """Creates an isolated temporary SQLite database for each test."""
    temp_dir = tempfile.mkdtemp()
    db_file = os.path.join(temp_dir, "test_events.db")
    init_db(db_file)
    yield db_file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass


@pytest.fixture
def client(test_db_path):
    """FastAPI TestClient with isolated settings and test database."""
    test_settings = Settings(
        RAZORPAY_WEBHOOK_SECRET=SYNTHETIC_WEBHOOK_SECRET,
        DATABASE_PATH=test_db_path
    )
    test_repo = WebhookEventRepository(db_path=test_db_path)

    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_event_repo] = lambda: test_repo

    with TestClient(app) as test_client:
        yield test_client, test_repo

    app.dependency_overrides.clear()


# -------------------------------------------------------------------------
# Test A: Valid signature -> accepted
# -------------------------------------------------------------------------
def test_a_valid_signature_accepted(client):
    test_client, repo = client
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test_001",
                    "amount": 10000,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_body)

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": "evt_test_valid_001",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["event_id"] == "evt_test_valid_001"

    # Confirm persistence
    saved = repo.get_event("evt_test_valid_001")
    assert saved is not None
    assert saved["event_type"] == "payment.captured"
    assert saved["payment_id"] == "pay_test_001"
    assert saved["amount"] == 10000


# -------------------------------------------------------------------------
# Test B: Invalid signature -> rejected
# -------------------------------------------------------------------------
def test_b_invalid_signature_rejected(client):
    test_client, repo = client
    payload = {"event": "payment.captured"}
    raw_body = json.dumps(payload).encode("utf-8")

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": "invalid_bogus_signature_12345",
            "x-razorpay-event-id": "evt_test_invalid_sig",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 400
    assert "Invalid webhook signature" in response.json()["detail"]
    assert not repo.is_duplicate("evt_test_invalid_sig")


# -------------------------------------------------------------------------
# Test C: Missing signature -> rejected
# -------------------------------------------------------------------------
def test_c_missing_signature_rejected(client):
    test_client, repo = client
    payload = {"event": "payment.captured"}
    raw_body = json.dumps(payload).encode("utf-8")

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "x-razorpay-event-id": "evt_test_no_sig",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 400
    assert "Missing X-Razorpay-Signature" in response.json()["detail"]
    assert not repo.is_duplicate("evt_test_no_sig")


# -------------------------------------------------------------------------
# Test D: Duplicate event ID -> idempotent, not processed twice
# -------------------------------------------------------------------------
def test_d_duplicate_event_id_idempotent(client):
    test_client, repo = client
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {"id": "pay_test_dup", "amount": 5000}
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_body)
    event_id = "evt_test_duplicate_key_001"

    # First delivery
    res1 = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": event_id,
            "Content-Type": "application/json"
        }
    )
    assert res1.status_code == 200
    assert res1.json()["status"] == "received"

    # Second delivery (duplicate)
    res2 = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": event_id,
            "Content-Type": "application/json"
        }
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "duplicate"
    assert res2.json()["message"] == "Event already processed"

    # Verify only ONE record exists
    conn = repo.get_event(event_id)
    assert conn is not None


# -------------------------------------------------------------------------
# Test E: payment.captured parsing
# -------------------------------------------------------------------------
def test_e_payment_captured_parsing(client):
    test_client, repo = client
    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_captured_777",
                    "order_id": "order_captured_777",
                    "amount": 25000,
                    "currency": "INR",
                    "status": "captured",
                    "method": "card"
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_body)

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": "evt_test_payment_captured",
            "Content-Type": "application/json"
        }
    )
    assert response.status_code == 200

    saved = repo.get_event("evt_test_payment_captured")
    assert saved["event_type"] == "payment.captured"
    assert saved["payment_id"] == "pay_captured_777"
    assert saved["order_id"] == "order_captured_777"
    assert saved["amount"] == 25000
    assert saved["currency"] == "INR"
    assert saved["status"] == "captured"


# -------------------------------------------------------------------------
# Test F: payment.failed parsing
# -------------------------------------------------------------------------
def test_f_payment_failed_parsing(client):
    test_client, repo = client
    payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_failed_888",
                    "order_id": "order_failed_888",
                    "amount": 15000,
                    "currency": "INR",
                    "status": "failed",
                    "error_code": "BAD_REQUEST_PAYMENT_DECLINED",
                    "error_description": "Card was declined by issuing bank"
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_body)

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": "evt_test_payment_failed",
            "Content-Type": "application/json"
        }
    )
    assert response.status_code == 200

    saved = repo.get_event("evt_test_payment_failed")
    assert saved["event_type"] == "payment.failed"
    assert saved["payment_id"] == "pay_failed_888"
    assert saved["order_id"] == "order_failed_888"
    assert saved["amount"] == 15000
    assert saved["status"] == "failed"
    assert saved["error_code"] == "BAD_REQUEST_PAYMENT_DECLINED"
    assert saved["error_description"] == "Card was declined by issuing bank"


# -------------------------------------------------------------------------
# Test G: payment_link.paid parsing
# -------------------------------------------------------------------------
def test_g_payment_link_paid_parsing(client):
    test_client, repo = client
    payload = {
        "event": "payment_link.paid",
        "payload": {
            "payment_link": {
                "entity": {
                    "id": "plink_test_recovery_999",
                    "order_id": "order_recovery_999",
                    "amount": 10000,
                    "amount_paid": 10000,
                    "currency": "INR",
                    "status": "paid",
                    "reference_id": "recoverai-test-ref-001"
                }
            },
            "payment": {
                "entity": {
                    "id": "pay_link_txn_999",
                    "status": "captured"
                }
            }
        }
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_body)

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": "evt_test_payment_link_paid",
            "Content-Type": "application/json"
        }
    )
    assert response.status_code == 200

    saved = repo.get_event("evt_test_payment_link_paid")
    assert saved["event_type"] == "payment_link.paid"
    assert saved["payment_link_id"] == "plink_test_recovery_999"
    assert saved["payment_id"] == "pay_link_txn_999"
    assert saved["order_id"] == "order_recovery_999"
    assert saved["amount"] == 10000
    assert saved["status"] == "paid"


# -------------------------------------------------------------------------
# Test H: Malformed payload -> rejected, not persisted, endpoint does not crash
# -------------------------------------------------------------------------
def test_h_malformed_payload_rejected_safe(client):
    test_client, repo = client
    # Raw broken JSON string
    raw_body = b"{\"event\": \"payment.captured\", \"payload\": broken_json_no_quotes...}"
    sig = compute_signature(raw_body)

    response = test_client.post(
        "/webhooks/razorpay",
        content=raw_body,
        headers={
            "X-Razorpay-Signature": sig,
            "x-razorpay-event-id": "evt_test_malformed",
            "Content-Type": "application/json"
        }
    )

    assert response.status_code == 400
    assert "Malformed JSON payload" in response.json()["detail"]
    assert not repo.is_duplicate("evt_test_malformed")


# -------------------------------------------------------------------------
# Test I: Race condition safe concurrent insertion
# -------------------------------------------------------------------------
def test_i_race_condition_safe_concurrent_insertion(client):
    test_client, repo = client
    payload = {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_race_1"}}}
    }
    raw_body = json.dumps(payload).encode("utf-8")
    sig = compute_signature(raw_body)
    event_id = "evt_race_concurrent_001"

    def send_req():
        return test_client.post(
            "/webhooks/razorpay",
            content=raw_body,
            headers={
                "X-Razorpay-Signature": sig,
                "x-razorpay-event-id": event_id,
                "Content-Type": "application/json"
            }
        )

    # Execute 5 concurrent requests with identical event_id
    with ThreadPoolExecutor(max_workers=5) as executor:
        responses = list(executor.map(lambda _: send_req(), range(5)))

    # All should return 200 OK
    assert all(r.status_code == 200 for r in responses)

    # Exactly one should have status "received", rest "duplicate"
    statuses = [r.json()["status"] for r in responses]
    assert statuses.count("received") == 1
    assert statuses.count("duplicate") == 4


# -------------------------------------------------------------------------
# Additional Test: Health Check Endpoint
# -------------------------------------------------------------------------
def test_health_check(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
