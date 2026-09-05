"""
Unit tests for RecoverAI vs Baseline held-out evaluation.
"""
import pytest
from simulator.generator import generate_dataset
from simulator.baseline_eval import evaluate_baseline_on_held_out
from simulator.recoverai_eval import (
    evaluate_recoverai_on_held_out,
    compare_baseline_and_recoverai,
)
from app.ml.train import train_recovery_models
from app.ml.predictor import RecoveryPredictor
from app.agent.decision_engine import RecoveryDecisionEngine


@pytest.fixture(scope="module")
def eval_dataset():
    """Generates 3,000 synthetic payments for fast evaluation test."""
    return generate_dataset(seed=42, n_payments=3000)


@pytest.fixture(scope="module")
def eval_engine(eval_dataset):
    models = train_recovery_models(
        payments_df=eval_dataset["payments"],
        customers_df=eval_dataset["customers"],
        outcomes_df=eval_dataset["ground_truth_outcomes"],
    )
    predictor = RecoveryPredictor(models=models)
    return RecoveryDecisionEngine(predictor=predictor)


class TestEvaluation:
    def test_baseline_eval_metrics(self, eval_dataset):
        metrics = evaluate_baseline_on_held_out(eval_dataset)
        assert metrics["total_failed_payments"] > 0
        assert metrics["actions_taken"] > 0
        assert metrics["recovered_count"] > 0
        assert metrics["recovered_gmv_paise"] > 0
        assert 0 < metrics["recovery_rate"] < 1.0

    def test_recoverai_eval_metrics(self, eval_dataset, eval_engine):
        metrics = evaluate_recoverai_on_held_out(eval_dataset, engine=eval_engine)
        assert metrics["total_failed_payments"] > 0
        assert metrics["recovered_count"] > 0
        assert metrics["recovered_gmv_paise"] > 0
        # Check diverse action distribution
        dist = metrics["action_distribution"]
        assert dist["payment_link"] > 0
        assert dist["delayed_retry"] > 0
        assert dist["no_action"] > 0

    def test_recoverai_outperforms_baseline_on_held_out(self, eval_dataset, eval_engine):
        base_res = evaluate_baseline_on_held_out(eval_dataset)
        rec_res = evaluate_recoverai_on_held_out(eval_dataset, engine=eval_engine)

        incremental_gmv = rec_res["recovered_gmv_paise"] - base_res["recovered_gmv_paise"]
        # RecoverAI should achieve substantial positive incremental recovered GMV
        assert incremental_gmv > 0
        assert rec_res["recovery_rate"] > base_res["recovery_rate"]
        assert rec_res["net_recovered_paise"] > base_res["net_recovered_paise"]
