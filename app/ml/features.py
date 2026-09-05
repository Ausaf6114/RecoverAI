"""
Feature engineering for RecoverAI recovery-probability models.

Extracts tabular features from PaymentContext (for online inference)
or DataFrames (for offline batch training and evaluation).
"""
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from app.domain.models import PaymentContext

FEATURE_COLUMNS = [
    "log_amount",
    "is_method_card",
    "is_method_upi",
    "is_method_netbanking",
    "is_source_bank",
    "is_source_network",
    "is_source_customer",
    "is_step_authentication",
    "is_step_authorization",
    "attempt_number",
    "customer_has_upi",
    "customer_has_card",
    "customer_failed_payments",
    "customer_successful_payments",
    "customer_success_ratio",
    "prior_contact_count",
]


def extract_features_from_context(context: PaymentContext) -> pd.DataFrame:
    """Extracts a single-row feature DataFrame from a PaymentContext dataclass."""
    tot = max(1, context.customer_total_payments)
    ratio = float(context.customer_successful_payments) / tot
    
    succ_methods = context.customer_successful_methods or []
    has_upi = 1 if any("upi" in m.lower() for m in succ_methods) else 0
    has_card = 1 if any("card" in m.lower() for m in succ_methods) else 0

    data: Dict[str, Any] = {
        "log_amount": np.log1p(float(context.amount)),
        "is_method_card": 1 if context.method == "card" else 0,
        "is_method_upi": 1 if context.method == "upi" else 0,
        "is_method_netbanking": 1 if context.method == "netbanking" else 0,
        "is_source_bank": 1 if context.error_source == "bank" else 0,
        "is_source_network": 1 if context.error_source == "network" else 0,
        "is_source_customer": 1 if context.error_source == "customer" else 0,
        "is_step_authentication": 1 if context.error_step == "payment_authentication" else 0,
        "is_step_authorization": 1 if context.error_step == "payment_authorization" else 0,
        "attempt_number": int(context.attempt_number),
        "customer_has_upi": has_upi,
        "customer_has_card": has_card,
        "customer_failed_payments": int(context.customer_failed_payments),
        "customer_successful_payments": int(context.customer_successful_payments),
        "customer_success_ratio": ratio,
        "prior_contact_count": int(context.prior_contact_count),
    }

    return pd.DataFrame([data], columns=FEATURE_COLUMNS)


def extract_features_df(
    payments_df: pd.DataFrame,
    customers_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Extracts a multi-row feature DataFrame from payments and customers DataFrames."""
    df = payments_df.copy()

    if customers_df is not None and "successful_methods" not in df.columns:
        cust_cols = [
            "id", "successful_methods", "total_payments",
            "successful_payments", "failed_payments"
        ]
        available_cust_cols = [c for c in cust_cols if c in customers_df.columns]
        df = df.merge(
            customers_df[available_cust_cols],
            left_on="customer_id",
            right_on="id",
            how="left",
            suffixes=("", "_cust")
        )

    # Defaults for missing columns
    method_col = df["method"].fillna("").astype(str).str.lower()
    source_col = df["error_source"].fillna("").astype(str).str.lower()
    step_col = df["error_step"].fillna("").astype(str).str.lower()
    succ_methods_col = df.get("successful_methods", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()

    tot_pay = df.get("total_payments", pd.Series(1, index=df.index)).fillna(1).clip(lower=1)
    succ_pay = df.get("successful_payments", pd.Series(0, index=df.index)).fillna(0)
    fail_pay = df.get("failed_payments", pd.Series(0, index=df.index)).fillna(0)
    contacts = df.get("prior_contact_count", pd.Series(0, index=df.index)).fillna(0)
    attempts = df.get("attempt_number", pd.Series(1, index=df.index)).fillna(1)

    features = pd.DataFrame(index=df.index)
    features["log_amount"] = np.log1p(df["amount"].astype(float))
    features["is_method_card"] = (method_col == "card").astype(int)
    features["is_method_upi"] = (method_col == "upi").astype(int)
    features["is_method_netbanking"] = (method_col == "netbanking").astype(int)
    features["is_source_bank"] = (source_col == "bank").astype(int)
    features["is_source_network"] = (source_col == "network").astype(int)
    features["is_source_customer"] = (source_col == "customer").astype(int)
    features["is_step_authentication"] = (step_col == "payment_authentication").astype(int)
    features["is_step_authorization"] = (step_col == "payment_authorization").astype(int)
    features["attempt_number"] = attempts.astype(int)
    features["customer_has_upi"] = succ_methods_col.str.contains("upi").astype(int)
    features["customer_has_card"] = succ_methods_col.str.contains("card").astype(int)
    features["customer_failed_payments"] = fail_pay.astype(int)
    features["customer_successful_payments"] = succ_pay.astype(int)
    features["customer_success_ratio"] = (succ_pay / tot_pay).astype(float)
    features["prior_contact_count"] = contacts.astype(int)

    return features[FEATURE_COLUMNS]
