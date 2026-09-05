"""
Unit tests for RecoverAI expected-value decision engine.
"""
import pytest
from app.domain.models import PaymentContext, MerchantPolicy
from app.ml.train import train_recovery_models
from app.ml.predictor import RecoveryPredictor
from app.agent.decision_engine import RecoveryDecisionEngine, DEFAULT_ACTION_COSTS
from simulator.generator import generate_dataset


@pytest.fixture(scope="module")
def engine():
    dataset = generate_dataset(seed=42, n_payments=2000)
    models = train_recovery_models(
        payments_df=dataset["payments"],
        customers_df=dataset["customers"],
        outcomes_df=dataset["ground_truth_outcomes"],
    )
    predictor = RecoveryPredictor(models=models)
    return RecoveryDecisionEngine(predictor=predictor)


class TestDecisionEngine:
    def test_pattern_a_selects_payment_link(self, engine):
        ctx = PaymentContext(
            payment_id="pay_a",
            customer_id="cust_a",
            merchant_id="merch_1",
            amount=150000,  # ₹1,500
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            error_reason="incorrect_otp",
            attempt_number=1,
            customer_successful_methods=["upi"],
        )
        res = engine.evaluate(ctx)
        assert res.selected_action == "payment_link"
        assert res.confidence > 0.60
        assert res.expected_recovery_value > 0
        assert res.estimated_cost == DEFAULT_ACTION_COSTS["payment_link"]

    def test_pattern_b_selects_delayed_retry(self, engine):
        ctx = PaymentContext(
            payment_id="pay_b",
            customer_id="cust_b",
            merchant_id="merch_1",
            amount=150000,
            method="upi",
            error_source="network",
            error_step="payment_authorization",
            error_reason="gateway_timeout",
            attempt_number=1,
        )
        res = engine.evaluate(ctx)
        assert res.selected_action == "delayed_retry"
        assert res.confidence > 0.60
        assert res.estimated_cost == DEFAULT_ACTION_COSTS["delayed_retry"]

    def test_pattern_c_selects_no_action(self, engine):
        ctx = PaymentContext(
            payment_id="pay_c",
            customer_id="cust_c",
            merchant_id="merch_1",
            amount=150000,
            method="card",
            error_source="customer",
            error_step="payment_authorization",
            error_reason="insufficient_funds",
            attempt_number=4,
            customer_failed_payments=4,
        )
        res = engine.evaluate(ctx)
        assert res.selected_action == "no_action"
        assert res.expected_recovery_value == 0.0

    def test_opted_out_customer_forces_no_action(self, engine):
        # Even with Pattern A, opted out customer must receive no_action
        ctx = PaymentContext(
            payment_id="pay_opt",
            customer_id="cust_opt",
            merchant_id="merch_1",
            amount=150000,
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            attempt_number=1,
            customer_successful_methods=["upi"],
            customer_opted_out=True,
        )
        res = engine.evaluate(ctx)
        assert res.selected_action == "no_action"

    def test_high_amount_triggers_approval(self, engine):
        policy = MerchantPolicy(requires_approval_above=500000)  # ₹5,000

        # ₹10,000 (1,000,000 paise)
        ctx = PaymentContext(
            payment_id="pay_high",
            customer_id="cust_high",
            merchant_id="merch_1",
            amount=1000000,
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            attempt_number=1,
            customer_successful_methods=["upi"],
        )
        res = engine.evaluate(ctx, policy=policy)
        assert res.selected_action == "payment_link"
        assert res.requires_approval is True

    def test_contact_cap_forces_delayed_retry_over_payment_link(self, engine):
        # When customer contact cap is hit (prior_contact_count >= 2),
        # payment_link is barred, but delayed_retry (no customer contact) is eligible!
        policy = MerchantPolicy(max_customer_contacts=2, min_confidence_threshold=0.10)
        ctx = PaymentContext(
            payment_id="pay_capped",
            customer_id="cust_capped",
            merchant_id="merch_1",
            amount=150000,
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            attempt_number=1,
            prior_contact_count=2,
            customer_successful_methods=["upi"],
        )
        res = engine.evaluate(ctx, policy=policy)
        # Payment link must be blocked
        assert res.selected_action != "payment_link"
