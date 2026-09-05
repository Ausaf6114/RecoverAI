"""
Unit tests for RazorpayActionAdapter safety, idempotency, and strategy execution.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.domain.models import PaymentContext
from app.razorpay.adapter import (
    RazorpayActionAdapter,
    RazorpaySecurityError,
    ExecutionResult,
)


@pytest.fixture
def sample_context():
    return PaymentContext(
        payment_id="pay_test_rzp_01",
        customer_id="cust_rzp_01",
        merchant_id="merch_rzp_01",
        amount=150000,
        currency="INR",
        order_id="order_rzp_01",
    )


class TestRazorpayAdapter:
    def test_live_key_rejected_by_safety_guardrail(self):
        # Live keys (rzp_live_...) must be blocked immediately
        with pytest.raises(RazorpaySecurityError) as exc_info:
            RazorpayActionAdapter(key_id="rzp_live_1234567890", key_secret="secret_abc")
        assert "Live Razorpay Key detected" in str(exc_info.value)

    def test_test_mode_key_accepted(self):
        adapter = RazorpayActionAdapter(key_id="rzp_test_1234567890", key_secret="secret_abc")
        assert adapter.is_configured() is True

    def test_unconfigured_simulation_fallback(self, sample_context):
        adapter = RazorpayActionAdapter(key_id=None, key_secret=None)
        assert adapter.is_configured() is False

        # Payment link
        res = adapter.execute_action(
            strategy="payment_link",
            context=sample_context,
            idempotency_key="idemp_sim_01",
        )
        assert res.strategy == "payment_link"
        assert res.status == "completed"
        assert res.is_simulated is True
        assert res.reference_id.startswith("plink_test_")
        assert "https://rzp.io/i/" in res.reference_url

    def test_all_mvp_strategies_execution(self, sample_context):
        adapter = RazorpayActionAdapter(key_id=None, key_secret=None)

        # 1. delayed_retry
        retry_res = adapter.execute_action("delayed_retry", sample_context, "idemp_retry_01")
        assert retry_res.strategy == "delayed_retry"
        assert retry_res.status == "completed"
        assert retry_res.reference_id.startswith("retry_test_")

        # 2. reminder
        rem_res = adapter.execute_action("reminder", sample_context, "idemp_rem_01")
        assert rem_res.strategy == "reminder"
        assert rem_res.status == "completed"
        assert rem_res.reference_id.startswith("rem_test_")

        # 3. no_action
        noact_res = adapter.execute_action("no_action", sample_context, "idemp_noact_01")
        assert noact_res.strategy == "no_action"
        assert noact_res.status == "completed"

    @patch("httpx.Client.post")
    def test_mocked_live_test_mode_api_call(self, mock_post, sample_context):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "id": "plink_TYArFjWcsjC9fE",
            "short_url": "https://rzp.io/i/TYArFjWcsjC9fE",
            "status": "created",
            "amount": 150000,
        }
        mock_post.return_value = mock_resp

        adapter = RazorpayActionAdapter(key_id="rzp_test_validkey", key_secret="test_secret")
        res = adapter.execute_action(
            strategy="payment_link",
            context=sample_context,
            idempotency_key="idemp_real_01",
            customer_email="test@example.com",
            customer_phone="+919800000001",
        )
        assert res.strategy == "payment_link"
        assert res.status == "completed"
        assert res.is_simulated is False
        assert res.reference_id == "plink_TYArFjWcsjC9fE"
        assert res.reference_url == "https://rzp.io/i/TYArFjWcsjC9fE"

    def test_idempotency_consistency(self, sample_context):
        adapter = RazorpayActionAdapter(key_id=None, key_secret=None)
        res1 = adapter.execute_action("payment_link", sample_context, "idemp_consistent_key")
        res2 = adapter.execute_action("payment_link", sample_context, "idemp_consistent_key")
        # Idempotency produces identical reference ID
        assert res1.reference_id == res2.reference_id

    def test_injected_http_client_is_used(self, sample_context, fake_razorpay_http_client):
        adapter = RazorpayActionAdapter(
            key_id="rzp_test_validkey",
            key_secret="test_secret",
            http_client=fake_razorpay_http_client,
        )
        res = adapter.execute_action(
            strategy="payment_link",
            context=sample_context,
            idempotency_key="idemp_injected_01",
        )
        assert res.strategy == "payment_link"
        assert res.status == "completed"
        assert res.reference_id == "plink_test_mocked_client_01"
        fake_razorpay_http_client.post.assert_called_once()
