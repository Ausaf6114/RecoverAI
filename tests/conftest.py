"""
Pytest configuration and fixtures for RecoverAI test suite.

Enforces zero-network policy for unit/integration tests:
- Automatically mocks RazorpayActionAdapter.create_payment_link to return fake plink_test_* response objects.
- Automatically mocks GeminiDiagnostician to return fake structured DiagnosisResult objects.
- Excludes real network calls unless explicitly opted into via @pytest.mark.live.
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
import httpx

from app.domain.models import PaymentContext
from app.agent.diagnosis import GeminiDiagnostician, DiagnosisResult, set_default_gemini_client
from app.razorpay.adapter import RazorpayActionAdapter, ExecutionResult, set_default_razorpay_client


@pytest.fixture
def fake_razorpay_http_client():
    """Mocked httpx.Client specifically simulating Razorpay API responses."""
    client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "plink_test_mocked_client_01",
        "short_url": "https://rzp.io/i/plink_test_mocked_client_01",
        "status": "created",
        "amount": 150000,
        "currency": "INR",
    }
    mock_resp.raise_for_status.return_value = None
    client.post.return_value = mock_resp
    return client


@pytest.fixture
def fake_gemini_http_client():
    """Mocked httpx.Client specifically simulating Gemini GenerateContent responses."""
    client = MagicMock(spec=httpx.Client)
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{
                    "text": (
                        '{"failure_category": "authentication_failure", '
                        '"hypothesis": "Card 3D-Secure authentication failed (injected client mock).", '
                        '"confidence": "high", "key_signals": ["card_3ds_step_failed"], '
                        '"recommended_strategy_hint": "payment_link"}'
                    )
                }]
            }
        }]
    }
    mock_resp.raise_for_status.return_value = None
    client.post.return_value = mock_resp
    return client


@pytest.fixture(autouse=True)
def mock_razorpay_adapter(request):
    """
    Autouse fixture that prevents tests from making real HTTP calls to Razorpay.
    Returns a fake plink_test_* response object.
    Preserves tests that explicitly mock httpx.Client.post or are marked with @pytest.mark.live.
    """
    if "live" in request.keywords:
        yield
        return

    # Preserve explicit unit tests in test_razorpay_adapter.py which test the adapter directly
    if request.node.path.name == "test_razorpay_adapter.py":
        yield
        return

    def fake_create_payment_link(self, context: PaymentContext, idempotency_key: str, customer_email=None, customer_phone=None):
        ref_id = f"plink_test_{uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_key).hex[:14]}"
        return ExecutionResult(
            strategy="payment_link",
            status="completed",
            reference_id=ref_id,
            reference_url=f"https://rzp.io/i/{ref_id}",
            raw_response={
                "id": ref_id,
                "entity": "payment_link",
                "status": "created",
                "short_url": f"https://rzp.io/i/{ref_id}",
                "amount": context.amount,
                "currency": context.currency,
            },
            is_simulated=False,
        )

    with patch.object(RazorpayActionAdapter, "create_payment_link", new=fake_create_payment_link) as mock_link:
        yield mock_link


@pytest.fixture(autouse=True)
def mock_gemini_diagnostician(request):
    """
    Autouse fixture that prevents tests from making real HTTP calls to Google Gemini.
    Returns a fake structured diagnosis.
    Preserves tests that test fallback or explicitly mock httpx.Client.post.
    """
    if "live" in request.keywords:
        yield
        return

    # Preserve specific unit tests for deterministic fallback or custom httpx mocks
    if request.node.name in (
        "test_mock_gemini_api_call",
        "test_deterministic_fallback_pattern_a",
        "test_deterministic_fallback_pattern_b",
        "test_injected_gemini_http_client_is_used",
    ):
        yield
        return

    def fake_diagnose(self, context: PaymentContext):
        return DiagnosisResult(
            failure_category="authentication_failure",
            hypothesis="Card 3D-Secure authentication failed at issuing bank (mocked diagnosis).",
            confidence="high",
            key_signals=["card_3ds_step_failed", "mocked_signal"],
            recommended_strategy_hint="payment_link",
            provider="gemini",
        )

    with patch.object(GeminiDiagnostician, "diagnose", new=fake_diagnose) as mock_diag:
        yield mock_diag


@pytest.fixture(autouse=True)
def block_external_network_calls(request, monkeypatch):
    """Guarantees that no non-live unit/integration test makes external network calls."""
    if "live" in request.keywords:
        yield
        return

    orig_send = httpx.Client.send

    def guarded_send(self, request_obj, *args, **kwargs):
        host = request_obj.url.host
        if host in ("api.razorpay.com", "generativelanguage.googleapis.com"):
            raise RuntimeError(
                f"FATAL: Attempted live external network call to '{host}' during non-live test suite! "
                f"URL: {request_obj.url}"
            )
        return orig_send(self, request_obj, *args, **kwargs)

    monkeypatch.setattr(httpx.Client, "send", guarded_send)
    yield
