"""
Tests for RecoverAI synthetic dataset generator.
"""
import pytest
import os
import shutil
import tempfile
import pandas as pd
from simulator.generator import generate_dataset


class TestDatasetGenerator:
    @pytest.fixture(scope="class")
    def dataset(self):
        """Generates a smaller dataset (3,000 payments) for fast test execution."""
        return generate_dataset(seed=42, n_payments=3000)

    def test_required_tables_present(self, dataset):
        expected_tables = {
            "merchants",
            "customers",
            "orders",
            "payments",
            "opportunities",
            "ground_truth_outcomes",
        }
        assert set(dataset.keys()) == expected_tables

    def test_payment_counts_and_statuses(self, dataset):
        payments = dataset["payments"]
        assert len(payments) == 3000
        # Check failed vs captured ratio (~2/3 failed, ~1/3 captured)
        failed_count = (payments["status"] == "failed").sum()
        captured_count = (payments["status"] == "captured").sum()
        assert failed_count == 2000
        assert captured_count == 1000

    def test_opportunities_match_failed_payments(self, dataset):
        payments = dataset["payments"]
        opps = dataset["opportunities"]
        failed_count = (payments["status"] == "failed").sum()
        assert len(opps) == failed_count
        assert set(opps["payment_id"]).issubset(set(payments[payments["status"] == "failed"]["id"]))

    def test_train_held_out_split_proportions(self, dataset):
        payments = dataset["payments"]
        split_counts = payments["dataset_split"].value_counts(normalize=True)
        # Should be approximately 80% train and 20% held_out
        assert 0.75 <= split_counts.get("train", 0) <= 0.85
        assert 0.15 <= split_counts.get("held_out", 0) <= 0.25

    def test_controlled_patterns_encoded(self, dataset):
        payments = dataset["payments"]
        failed = payments[payments["status"] == "failed"]

        # Pattern A: card auth failures
        pattern_a = failed[failed["pattern_label"] == "pattern_a_card_auth"]
        assert len(pattern_a) > 0
        assert (pattern_a["method"] == "card").all()
        assert (pattern_a["error_source"] == "bank").all()
        assert (pattern_a["error_step"] == "payment_authentication").all()

        # Pattern B: network failures
        pattern_b = failed[failed["pattern_label"] == "pattern_b_transient_network"]
        assert len(pattern_b) > 0
        assert (pattern_b["error_source"] == "network").all()

        # Pattern C: repeated failures
        pattern_c = failed[failed["pattern_label"] == "pattern_c_repeated_failure"]
        assert len(pattern_c) > 0
        assert (pattern_c["attempt_number"] >= 3).all()

        # Pattern D: general failures
        pattern_d = failed[failed["pattern_label"] == "pattern_d_general"]
        assert len(pattern_d) > 0

    def test_ground_truth_outcomes_probabilities(self, dataset):
        outcomes = dataset["ground_truth_outcomes"]
        assert len(outcomes) == 2000  # only for failed payments

        # Pattern A should have high latent recovery for payment link
        p_a = outcomes[outcomes["pattern_label"] == "pattern_a_card_auth"]
        assert (p_a["latent_prob_payment_link"] >= 0.70).all()

        # Pattern B should have high latent recovery for delayed retry
        p_b = outcomes[outcomes["pattern_label"] == "pattern_b_transient_network"]
        assert (p_b["latent_prob_delayed_retry"] >= 0.70).all()

        # Pattern C should have low latent recovery across actions
        p_c = outcomes[outcomes["pattern_label"] == "pattern_c_repeated_failure"]
        assert (p_c["latent_prob_payment_link"] < 0.10).all()

    def test_reproducibility_with_same_seed(self):
        ds1 = generate_dataset(seed=123, n_payments=500)
        ds2 = generate_dataset(seed=123, n_payments=500)
        pd.testing.assert_frame_equal(ds1["payments"], ds2["payments"])

    def test_csv_export(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            generate_dataset(seed=42, n_payments=100, output_dir=tmp_dir)
            files = os.listdir(tmp_dir)
            assert "payments.csv" in files
            assert "customers.csv" in files
            assert "orders.csv" in files
            assert "opportunities.csv" in files
            assert "ground_truth_outcomes.csv" in files
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
