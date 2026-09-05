"""
Model training for RecoverAI recovery-probability estimation.

Trains calibrated LogisticRegression models on the synthetic training split
to estimate P(recovery | context, action) for candidate recovery strategies.
"""
import os
import pickle
from typing import Dict, Optional, Any
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

from app.ml.features import extract_features_df, FEATURE_COLUMNS
from simulator.generator import generate_dataset

RECOVERY_STRATEGIES = ["payment_link", "delayed_retry", "reminder"]
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


def train_recovery_models(
    payments_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    outcomes_df: pd.DataFrame,
    model_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Trains an individual calibrated LogisticRegression pipeline for each recovery strategy
    using the training split of failed payments.

    Args:
        payments_df: Payments DataFrame containing status and dataset_split.
        customers_df: Customers DataFrame with profile history.
        outcomes_df: Ground truth outcomes DataFrame with realized success columns.
        model_dir: Optional directory to persist pickled model artifacts.

    Returns:
        Dict mapping strategy name to trained Pipeline/Classifier.
    """
    # Filter to failed payments in the training split
    failed_train_mask = (payments_df["status"] == "failed") & (payments_df["dataset_split"] == "train")
    train_payments = payments_df[failed_train_mask].copy().reset_index(drop=True)

    if len(train_payments) == 0:
        raise ValueError("No training failed payments found to train models.")

    # Merge with ground truth outcomes to get target labels
    merged_train = train_payments.merge(
        outcomes_df,
        left_on="id",
        right_on="payment_id",
        how="inner",
        suffixes=("", "_out"),
    )

    X_train = extract_features_df(merged_train, customers_df)

    trained_models: Dict[str, Any] = {}

    for strategy in RECOVERY_STRATEGIES:
        target_col = f"realized_{strategy}_recovered"
        if target_col not in merged_train.columns:
            raise KeyError(f"Target column '{target_col}' not found in outcomes data.")

        y_train = merged_train[target_col].astype(int).values

        # Base classifier pipeline
        base_pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42, C=1.0)),
        ])

        # Calibrated classifier for reliable probability estimates
        calibrated_model = CalibratedClassifierCV(
            estimator=base_pipeline,
            method="sigmoid",
            cv=3,
        )
        calibrated_model.fit(X_train, y_train)
        trained_models[strategy] = calibrated_model

    # Persist artifacts if model_dir is provided
    if model_dir:
        os.makedirs(model_dir, exist_ok=True)
        for strategy, model in trained_models.items():
            model_path = os.path.join(model_dir, f"{strategy}_model.pkl")
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

    return trained_models


def train_and_save_default_models(model_dir: str = DEFAULT_MODEL_DIR) -> Dict[str, Any]:
    """Generates standard 30k synthetic dataset and trains default models."""
    dataset = generate_dataset(seed=42, n_payments=30000)
    return train_recovery_models(
        payments_df=dataset["payments"],
        customers_df=dataset["customers"],
        outcomes_df=dataset["ground_truth_outcomes"],
        model_dir=model_dir,
    )


if __name__ == "__main__":
    train_and_save_default_models()
