"""
Unit tests for RecoverAI merchant policy guardrails.
"""
import pytest
from app.domain.models import PaymentContext, RecoveryCandidate, MerchantPolicy
from app.domain.guardrails import (
    evaluate_action_guardrails,
    check_approval_requirement,
    apply_guardrails_to_candidates,
)


@pytest.fixture
def sample_context():
    return PaymentContext(
        payment_id="pay_001",
        customer_id="cust_001",
        merchant_id="merch_001",
        amount=100000,
        status="failed",
        attempt_number=1,
        prior_contact_count=0,
        customer_opted_out=False,
    )


class TestGuardrails:
    def test_no_action_always_passes(self, sample_context):
        sample_context.customer_opted_out = True
        sample_context.attempt_number = 10
        cand = RecoveryCandidate(strategy="no_action", predicted_recovery_probability=0.0, expected_recovery_value=0.0)
        res = evaluate_action_guardrails(sample_context, cand)
        assert res.passed is True

    def test_non_failed_payment_rejected(self, sample_context):
        sample_context.status = "captured"
        cand = RecoveryCandidate(strategy="payment_link", predicted_recovery_probability=0.8, expected_recovery_value=80000.0)
        res = evaluate_action_guardrails(sample_context, cand)
        assert res.passed is False
        assert res.reason == "payment_not_failed"

    def test_opted_out_customer_rejected(self, sample_context):
        sample_context.customer_opted_out = True
        cand = RecoveryCandidate(strategy="payment_link", predicted_recovery_probability=0.85, expected_recovery_value=85000.0)
        res = evaluate_action_guardrails(sample_context, cand)
        assert res.passed is False
        assert res.reason == "customer_opted_out"

    def test_max_attempts_cap(self, sample_context):
        policy = MerchantPolicy(max_recovery_attempts=3)
        sample_context.attempt_number = 4
        cand = RecoveryCandidate(strategy="delayed_retry", predicted_recovery_probability=0.75, expected_recovery_value=75000.0)
        res = evaluate_action_guardrails(sample_context, cand, policy=policy)
        assert res.passed is False
        assert "exceeds_max_3" in res.reason

    def test_contact_cap_blocks_customer_facing_actions_only(self, sample_context):
        policy = MerchantPolicy(max_customer_contacts=2, min_confidence_threshold=0.60)
        sample_context.prior_contact_count = 2

        # Customer-facing payment_link must be blocked
        cand_link = RecoveryCandidate(strategy="payment_link", predicted_recovery_probability=0.80, expected_recovery_value=80000.0)
        res_link = evaluate_action_guardrails(sample_context, cand_link, policy=policy)
        assert res_link.passed is False
        assert "prior_contacts_2_exceeds_max_2" in res_link.reason

        # Backend delayed_retry does NOT contact the customer, so it passes!
        cand_retry = RecoveryCandidate(strategy="delayed_retry", predicted_recovery_probability=0.75, expected_recovery_value=75000.0)
        res_retry = evaluate_action_guardrails(sample_context, cand_retry, policy=policy)
        assert res_retry.passed is True

    def test_confidence_floor_enforcement(self, sample_context):
        policy = MerchantPolicy(min_confidence_threshold=0.65)
        cand = RecoveryCandidate(strategy="payment_link", predicted_recovery_probability=0.40, expected_recovery_value=40000.0)
        res = evaluate_action_guardrails(sample_context, cand, policy=policy)
        assert res.passed is False
        assert "below_min_0.65" in res.reason

    def test_approval_requirement_threshold(self, sample_context):
        policy = MerchantPolicy(requires_approval_above=500000)  # ₹5,000

        sample_context.amount = 400000  # ₹4,000
        assert check_approval_requirement(sample_context, policy) is False

        sample_context.amount = 600000  # ₹6,000
        assert check_approval_requirement(sample_context, policy) is True

    def test_apply_guardrails_to_candidates_list(self, sample_context):
        policy = MerchantPolicy(min_confidence_threshold=0.65)
        candidates = [
            RecoveryCandidate(strategy="payment_link", predicted_recovery_probability=0.80, expected_recovery_value=80000.0),
            RecoveryCandidate(strategy="reminder", predicted_recovery_probability=0.50, expected_recovery_value=50000.0),
            RecoveryCandidate(strategy="no_action", predicted_recovery_probability=0.01, expected_recovery_value=0.0),
        ]
        vetted = apply_guardrails_to_candidates(sample_context, candidates, policy=policy)
        assert len(vetted) == 3
        assert vetted[0].is_eligible is True
        assert vetted[1].is_eligible is False
        assert "below_min_0.65" in vetted[1].ineligibility_reason
        assert vetted[2].is_eligible is True
