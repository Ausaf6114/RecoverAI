"""
Unit tests for RecoverAI ML feature engineering, model training, and prediction.
"""
import pytest
import os
import shutil
import tempfile
import pandas as pd
from app.domain.models import PaymentContext
from app.ml.features import (
    extract_features_from_context,
    extract_features_df,
    FEATURE_COLUMNS,
)
from app.ml.train import train_recovery_models
from app.ml.predictor import RecoveryPredictor
from simulator.generator import generate_dataset


@pytest.fixture(scope="module")
def small_dataset():
    """Generates 2,000 synthetic payments for fast test execution."""
    return generate_dataset(seed=42, n_payments=2000)


@pytest.fixture(scope="module")
def trained_predictor(small_dataset):
    models = train_recovery_models(
        payments_df=small_dataset["payments"],
        customers_df=small_dataset["customers"],
        outcomes_df=small_dataset["ground_truth_outcomes"],
    )
    return RecoveryPredictor(models=models)


class TestMLPipeline:
    def test_feature_extraction_from_context(self):
        ctx = PaymentContext(
            payment_id="p1",
            customer_id="c1",
            merchant_id="m1",
            amount=150000,
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            attempt_number=1,
            customer_successful_methods=["upi"],
            customer_successful_payments=3,
            customer_total_payments=4,
        )
        df = extract_features_from_context(ctx)
        assert list(df.columns) == FEATURE_COLUMNS
        assert df.shape == (1, len(FEATURE_COLUMNS))
        assert df["is_method_card"].iloc[0] == 1
        assert df["is_method_upi"].iloc[0] == 0
        assert df["is_source_bank"].iloc[0] == 1
        assert df["is_step_authentication"].iloc[0] == 1
        assert df["customer_has_upi"].iloc[0] == 1
        assert df["attempt_number"].iloc[0] == 1

    def test_feature_extraction_from_df(self, small_dataset):
        payments = small_dataset["payments"]
        customers = small_dataset["customers"]
        feat_df = extract_features_df(payments, customers)
        assert list(feat_df.columns) == FEATURE_COLUMNS
        assert len(feat_df) == len(payments)
        assert not feat_df.isnull().any().any()

    def test_training_and_serialization(self, small_dataset):
        tmp_dir = tempfile.mkdtemp()
        try:
            models = train_recovery_models(
                payments_df=small_dataset["payments"],
                customers_df=small_dataset["customers"],
                outcomes_df=small_dataset["ground_truth_outcomes"],
                model_dir=tmp_dir,
            )
            assert "payment_link" in models
            assert "delayed_retry" in models
            assert "reminder" in models
            assert os.path.exists(os.path.join(tmp_dir, "payment_link_model.pkl"))
            assert os.path.exists(os.path.join(tmp_dir, "delayed_retry_model.pkl"))
            assert os.path.exists(os.path.join(tmp_dir, "reminder_model.pkl"))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_predictor_pattern_a_card_auth(self, trained_predictor):
        # Pattern A: Card auth failure + customer has UPI history -> high payment_link probability
        ctx = PaymentContext(
            payment_id="p_a",
            customer_id="c_a",
            merchant_id="m1",
            amount=200000,
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            error_reason="incorrect_otp",
            attempt_number=1,
            customer_successful_methods=["upi"],
        )
        probs = trained_predictor.predict_all_probabilities(ctx)
        assert probs["payment_link"] > 0.60
        assert probs["payment_link"] > probs["delayed_retry"]

    def test_predictor_pattern_b_transient_network(self, trained_predictor):
        # Pattern B: Network failure -> high delayed_retry probability
        ctx = PaymentContext(
            payment_id="p_b",
            customer_id="c_b",
            merchant_id="m1",
            amount=200000,
            method="upi",
            error_source="network",
            error_step="payment_authorization",
            error_reason="gateway_timeout",
            attempt_number=1,
        )
        probs = trained_predictor.predict_all_probabilities(ctx)
        assert probs["delayed_retry"] > 0.60
        assert probs["delayed_retry"] > probs["payment_link"]

    def test_predictor_pattern_c_repeated_failures(self, trained_predictor):
        # Pattern C: Repeated failures (attempt 4, insufficient funds) -> low probabilities
        ctx = PaymentContext(
            payment_id="p_c",
            customer_id="c_c",
            merchant_id="m1",
            amount=200000,
            method="card",
            error_source="customer",
            error_step="payment_authorization",
            error_reason="insufficient_funds",
            attempt_number=4,
            customer_failed_payments=5,
        )
        probs = trained_predictor.predict_all_probabilities(ctx)
        assert probs["payment_link"] < 0.20
        assert probs["delayed_retry"] < 0.20

    def test_predictor_batch_dataframe(self, trained_predictor, small_dataset):
        payments = small_dataset["payments"].head(50)
        customers = small_dataset["customers"]
        preds = trained_predictor.predict_df(payments, customers)
        assert len(preds) == 50
        assert "prob_payment_link" in preds.columns
        assert "prob_delayed_retry" in preds.columns
        assert "prob_reminder" in preds.columns
        assert (preds["prob_payment_link"] >= 0).all()
        assert (preds["prob_payment_link"] <= 1).all()
