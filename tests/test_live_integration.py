"""
Live integration tests for real external APIs (Razorpay Test Mode & Google Gemini).

These tests make REAL external network calls.
They are tagged with `@pytest.mark.live` and excluded by default from the standard test suite.
To execute live integration tests:
    pytest -m live
"""
import uuid
import pytest

from app.core.config import get_settings
from app.domain.models import PaymentContext
from app.agent.diagnosis import GeminiDiagnostician
from app.razorpay.adapter import RazorpayActionAdapter


@pytest.mark.live
class TestLiveExternalAPIs:
    """Tests executing actual network requests to Razorpay Test Mode and Gemini APIs."""

    def test_live_gemini_diagnosis_call(self):
        """Exercises real Gemini API generateContent endpoint with gemini-3.5-flash."""
        settings = get_settings()
        if not settings.GEMINI_API_KEY:
            pytest.skip("GOOGLE_API_KEY / GEMINI_API_KEY not set in environment.")

        diagnostician = GeminiDiagnostician(
            api_key=settings.GEMINI_API_KEY,
            model="gemini-3.5-flash",
        )
        context = PaymentContext(
            payment_id="pay_live_test_001",
            customer_id="cust_live_test_001",
            merchant_id="merch_live_test_001",
            amount=250000,
            currency="INR",
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            error_reason="incorrect_otp",
            error_code="BAD_REQUEST_ERROR",
            attempt_number=1,
            customer_successful_methods=["upi"],
        )

        result = diagnostician.diagnose(context)
        assert result.provider == "gemini"
        assert result.failure_category in (
            "authentication_failure",
            "network_timeout",
            "insufficient_funds",
            "general_failure",
        )
        assert result.confidence in ("high", "medium", "low")
        assert len(result.hypothesis) > 5

    def test_live_razorpay_payment_link_creation(self):
        """Exercises real Razorpay Test Mode API to create a payment link."""
        settings = get_settings()
        if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
            pytest.skip("Razorpay test credentials not configured in environment.")

        adapter = RazorpayActionAdapter(
            key_id=settings.RAZORPAY_KEY_ID,
            key_secret=settings.RAZORPAY_KEY_SECRET,
        )
        if not adapter.is_configured():
            pytest.skip("Razorpay adapter not configured with valid rzp_test_ key.")

        uid = uuid.uuid4().hex[:8]
        context = PaymentContext(
            payment_id=f"pay_live_{uid}",
            customer_id=f"cust_live_{uid}",
            merchant_id="merch_live_demo",
            amount=100000,
            currency="INR",
            order_id=f"order_live_{uid}",
        )
        idempotency_key = f"idemp_live_{uid}"

        result = adapter.execute_action(
            strategy="payment_link",
            context=context,
            idempotency_key=idempotency_key,
        )

        # Check if Razorpay's Test Mode sandbox quota (max 30 payment links) was reached
        if result.status == "failed" and result.raw_response:
            err = result.raw_response.get("error", {})
            err_code = err.get("code")
            err_desc = err.get("description", "")
            if err_code == "RATE_LIMIT_EXCEEDED" or "limit of 30 reached" in err_desc:
                pytest.skip(f"Razorpay Test Mode quota limit reached: {err_desc}")

        assert result.status == "completed"
        assert result.is_simulated is False
        assert result.reference_id is not None
        assert result.reference_id.startswith("plink_")
        assert result.reference_url is not None
