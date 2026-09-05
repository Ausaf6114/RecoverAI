"""
Recovery probability predictor for RecoverAI.

Provides calibrated probability estimation P(recovery | context, action)
for candidate recovery strategies.
"""
import os
import pickle
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd

from app.domain.models import PaymentContext
from app.ml.features import extract_features_from_context, extract_features_df
from app.ml.train import RECOVERY_STRATEGIES, DEFAULT_MODEL_DIR, train_and_save_default_models


class RecoveryPredictor:
    """Predicts recovery probabilities for candidate interventions."""

    def __init__(
        self,
        models: Optional[Dict[str, Any]] = None,
        model_dir: str = DEFAULT_MODEL_DIR,
    ):
        self.model_dir = model_dir
        self.models: Dict[str, Any] = {}

        if models is not None:
            self.models = models
        else:
            self._load_or_train_models()

    def _load_or_train_models(self) -> None:
        """Loads models from disk or trains default models if absent."""
        loaded = {}
        all_exist = True

        for strategy in RECOVERY_STRATEGIES:
            path = os.path.join(self.model_dir, f"{strategy}_model.pkl")
            if os.path.exists(path):
                with open(path, "rb") as f:
                    loaded[strategy] = pickle.load(f)
            else:
                all_exist = False
                break

        if all_exist and len(loaded) == len(RECOVERY_STRATEGIES):
            self.models = loaded
        else:
            # Train and cache
            self.models = train_and_save_default_models(model_dir=self.model_dir)

    def predict_all_probabilities(self, context: PaymentContext) -> Dict[str, float]:
        """
        Predicts recovery probability for all known strategies given a PaymentContext.
        Returns dict mapping strategy name to calibrated probability float.
        """
        X = extract_features_from_context(context)
        probs: Dict[str, float] = {}

        for strategy in RECOVERY_STRATEGIES:
            if strategy in self.models:
                # predict_proba returns [P(0), P(1)]
                proba = float(self.models[strategy].predict_proba(X)[0][1])
                probs[strategy] = round(float(np.clip(proba, 0.001, 0.999)), 4)
            else:
                probs[strategy] = 0.05

        # No action has minimal spontaneous baseline recovery
        probs["no_action"] = 0.01

        return probs

    def predict_df(
        self,
        payments_df: pd.DataFrame,
        customers_df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Batch prediction for a DataFrame of payments.
        Returns DataFrame with predicted probabilities per strategy.
        """
        X = extract_features_df(payments_df, customers_df)
        preds = pd.DataFrame(index=payments_df.index)

        for strategy in RECOVERY_STRATEGIES:
            if strategy in self.models:
                preds[f"prob_{strategy}"] = self.models[strategy].predict_proba(X)[:, 1]
            else:
                preds[f"prob_{strategy}"] = 0.05

        preds["prob_no_action"] = 0.01
        return preds
