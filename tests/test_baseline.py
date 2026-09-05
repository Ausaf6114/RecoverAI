"""
Tests for RecoverAI deterministic baseline recovery policy.
"""
import pytest
from app.domain.models import PaymentContext, MerchantPolicy
from app.domain.baseline import (
    evaluate_baseline_policy,
    batch_evaluate_baseline,
    BASELINE_PAYMENT_LINK_PROBABILITY,
)


@pytest.fixture
def base_context():
    return PaymentContext(
        payment_id="pay_fail_001",
        customer_id="cust_001",
        merchant_id="merch_001",
        amount=100000,  # ₹1,000 in paise
        currency="INR",
        method="card",
        status="failed",
        error_source="bank",
        error_step="payment_authentication",
        error_reason="incorrect_otp",
        attempt_number=1,
        prior_contact_count=0,
        customer_opted_out=False,
    )


class TestBaselinePolicy:
    def test_eligible_failed_payment_selects_payment_link(self, base_context):
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.strategy == "payment_link"
        assert candidate.predicted_recovery_probability == BASELINE_PAYMENT_LINK_PROBABILITY
        assert candidate.expected_recovery_value == 35000.0  # 0.35 * 100000
        assert candidate.is_eligible is True
        assert candidate.ineligibility_reason is None

    def test_captured_payment_is_ineligible(self, base_context):
        base_context.status = "captured"
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.strategy == "no_action"
        assert candidate.predicted_recovery_probability == 0.0
        assert candidate.is_eligible is False
        assert candidate.ineligibility_reason == "payment_not_failed"

    def test_opted_out_customer_is_blocked(self, base_context):
        base_context.customer_opted_out = True
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.strategy == "no_action"
        assert candidate.is_eligible is False
        assert candidate.ineligibility_reason == "customer_opted_out"

    def test_attempt_number_limit(self, base_context):
        # Attempt 2 is allowed
        base_context.attempt_number = 2
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.is_eligible is True

        # Attempt 3 exceeds baseline limit
        base_context.attempt_number = 3
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.strategy == "no_action"
        assert candidate.is_eligible is False
        assert candidate.ineligibility_reason == "max_attempts_exceeded"

    def test_contact_cap_limit(self, base_context):
        # 1 prior contact is allowed under default max_customer_contacts=2
        base_context.prior_contact_count = 1
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.is_eligible is True

        # 2 prior contacts exceeds limit
        base_context.prior_contact_count = 2
        candidate = evaluate_baseline_policy(base_context)
        assert candidate.strategy == "no_action"
        assert candidate.is_eligible is False
        assert candidate.ineligibility_reason == "max_contacts_exceeded"

    def test_custom_merchant_policy_overrides(self, base_context):
        policy = MerchantPolicy(max_customer_contacts=1)
        base_context.prior_contact_count = 1
        candidate = evaluate_baseline_policy(base_context, policy=policy)
        assert candidate.is_eligible is False
        assert candidate.ineligibility_reason == "max_contacts_exceeded"

    def test_batch_evaluate_baseline(self, base_context):
        ctx2 = PaymentContext(
            payment_id="pay_fail_002",
            customer_id="cust_002",
            merchant_id="merch_001",
            amount=200000,
            status="failed",
            attempt_number=4,  # will be blocked
        )
        candidates = batch_evaluate_baseline([base_context, ctx2])
        assert len(candidates) == 2
        assert candidates[0].strategy == "payment_link"
        assert candidates[0].is_eligible is True
        assert candidates[1].strategy == "no_action"
        assert candidates[1].is_eligible is False
