"""
Synthetic payment dataset generator for RecoverAI.

Generates a reproducible 30,000 payment dataset with controlled failure
and recovery patterns per docs/kb/27_MOCK_DATA_SPECIFICATION.md and
docs/kb/21_MEASUREMENT_AND_EXPERIMENTATION.md.

Controlled patterns encoded:
- Pattern A (35% of failures): Card authentication failure where customer has UPI history.
  Payment Link (S-01) recovery probability is high (~80%).
- Pattern B (25% of failures): Network / gateway timeout error.
  Delayed Retry (S-02) recovery probability is high (~75%).
- Pattern C (20% of failures): Repeated failures (3+ attempts, multiple customer failures).
  No Action (S-04) is optimal; recovery probability is low (<5%).
- Pattern D (20% of failures): General / miscellaneous failures.
  Moderate recovery probability (~25%).

All data includes 80% train / 20% held-out evaluation split.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import numpy as np
import pandas as pd


def generate_dataset(
    seed: int = 42,
    n_payments: int = 30000,
    output_dir: Optional[str] = None,
) -> Dict[str, pd.DataFrame]:
    """
    Generates synthetic merchants, customers, orders, payments, opportunities,
    and simulated true outcomes for offline evaluation.

    Args:
        seed: Random seed for exact reproducibility.
        n_payments: Total number of payments (default 30,000).
        output_dir: Optional directory path to save CSV files.

    Returns:
        Dict mapping table name to DataFrame.
    """
    rng = np.random.default_rng(seed)

    # 1. Merchant
    merchant_id = "merch_recoverai_test"
    merchants_df = pd.DataFrame([
        {
            "id": merchant_id,
            "name": "RecoverAI Enterprise Demo",
            "max_recovery_attempts": 3,
            "max_customer_contacts": 2,
            "min_confidence_threshold": 0.65,
            "auto_execute_below_amount": 50000,     # ₹500
            "requires_approval_above": 500000,      # ₹5,000
            "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
        }
    ])

    # 2. Customers (~7,000 customers)
    n_customers = 7000
    customer_ids = [f"cust_{i+1:05d}" for i in range(n_customers)]

    # 80/20 train/held_out split assigned at customer level for clean separation
    cust_split_is_train = rng.random(n_customers) < 0.8
    cust_splits = np.where(cust_split_is_train, "train", "held_out")

    # Opted-out rate ~2%
    opted_out = rng.random(n_customers) < 0.02

    # Customer methods preference history:
    # 0: upi only, 1: card only, 2: upi+card, 3: netbanking+upi
    method_combos = ["upi", "card", "upi,card", "netbanking,upi"]
    assigned_methods = rng.choice(method_combos, size=n_customers, p=[0.45, 0.25, 0.25, 0.05])

    customers_df = pd.DataFrame({
        "id": customer_ids,
        "merchant_id": merchant_id,
        "email": [f"user_{i+1}@example.com" for i in range(n_customers)],
        "phone": [f"+9198{rng.integers(10000000, 99999999)}" for _ in range(n_customers)],
        "opted_out": opted_out,
        "successful_methods": assigned_methods,
        "dataset_split": cust_splits,
        "created_at": [
            datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=int(d))
            for d in rng.integers(0, 180, size=n_customers)
        ],
    })
    cust_split_map = dict(zip(customer_ids, cust_splits))
    cust_method_map = dict(zip(customer_ids, assigned_methods))

    # 3. Orders (~15,000 orders)
    n_orders = 15000
    order_ids = [f"order_{i+1:06d}" for i in range(n_orders)]
    order_customer_indices = rng.integers(0, n_customers, size=n_orders)
    order_customers = [customer_ids[idx] for idx in order_customer_indices]
    order_splits = [cust_split_map[c] for c in order_customers]

    categories = ["electronics", "apparel", "grocery", "saas_subscription", "travel", "fitness"]
    order_categories = rng.choice(categories, size=n_orders, p=[0.25, 0.30, 0.20, 0.10, 0.10, 0.05])

    # Log-normal order amounts: median ~₹1,200 (120,000 paise), min ₹100, max ₹50,000
    base_amounts = np.exp(rng.normal(11.5, 0.8, size=n_orders)).astype(int)
    base_amounts = np.clip(base_amounts, 10000, 5000000)  # in paise

    start_date = datetime(2025, 2, 1, tzinfo=timezone.utc)
    order_offsets_sec = rng.integers(0, 120 * 86400, size=n_orders)
    order_dates = [start_date + timedelta(seconds=int(s)) for s in order_offsets_sec]

    orders_df = pd.DataFrame({
        "id": order_ids,
        "merchant_id": merchant_id,
        "customer_id": order_customers,
        "amount": base_amounts,
        "currency": "INR",
        "category": order_categories,
        "dataset_split": order_splits,
        "created_at": order_dates,
        "razorpay_order_id": [f"order_rp_{i+1:06d}" for i in range(n_orders)],
    })
    order_amount_map = dict(zip(order_ids, base_amounts))
    order_date_map = dict(zip(order_ids, order_dates))

    # 4. Payments (30,000 payments: ~10,000 captured, ~20,000 failed)
    # Failed ratio ~2/3 (20,000) to ensure substantial recovery evaluation volume
    n_failed = int(n_payments * (2 / 3))
    n_captured = n_payments - n_failed

    payment_ids = [f"pay_{i+1:07d}" for i in range(n_payments)]
    # Link payments to orders
    pay_order_indices = rng.integers(0, n_orders, size=n_payments)
    pay_orders = [order_ids[idx] for idx in pay_order_indices]
    pay_customers = [order_customers[idx] for idx in pay_order_indices]
    pay_splits = [cust_split_map[c] for c in pay_customers]
    pay_amounts = [order_amount_map[oid] for oid in pay_orders]

    # Assign captured vs failed
    status_array = np.array(["captured"] * n_captured + ["failed"] * n_failed)
    rng.shuffle(status_array)

    # Initialize payment attribute arrays
    methods = ["upi", "card", "netbanking", "wallet"]
    pay_methods = [None] * n_payments
    error_sources = [None] * n_payments
    error_steps = [None] * n_payments
    error_reasons = [None] * n_payments
    error_codes = [None] * n_payments
    error_descriptions = [None] * n_payments
    attempt_numbers = np.ones(n_payments, dtype=int)
    pattern_labels = ["none"] * n_payments

    # Ground-truth recovery probabilities under different strategies:
    # Used to simulate realistic recovery outcomes for evaluation
    latent_prob_payment_link = np.zeros(n_payments)
    latent_prob_delayed_retry = np.zeros(n_payments)
    latent_prob_reminder = np.zeros(n_payments)
    latent_prob_no_action = np.zeros(n_payments)

    # For captured payments:
    captured_indices = np.where(status_array == "captured")[0]
    for idx in captured_indices:
        pay_methods[idx] = rng.choice(methods, p=[0.60, 0.30, 0.08, 0.02])

    # For failed payments: distribute into controlled patterns
    failed_indices = np.where(status_array == "failed")[0]
    n_actual_failed = len(failed_indices)

    # Split failed indices:
    # 35% Pattern A, 25% Pattern B, 20% Pattern C, 20% Pattern D
    p_a_count = int(0.35 * n_actual_failed)
    p_b_count = int(0.25 * n_actual_failed)
    p_c_count = int(0.20 * n_actual_failed)
    p_d_count = n_actual_failed - (p_a_count + p_b_count + p_c_count)

    rng.shuffle(failed_indices)
    idx_pattern_a = failed_indices[:p_a_count]
    idx_pattern_b = failed_indices[p_a_count:p_a_count + p_b_count]
    idx_pattern_c = failed_indices[p_a_count + p_b_count:p_a_count + p_b_count + p_c_count]
    idx_pattern_d = failed_indices[p_a_count + p_b_count + p_c_count:]

    # Pattern A: Card authentication failure + customer has UPI history -> Payment Link high recovery
    for idx in idx_pattern_a:
        cid = pay_customers[idx]
        # Ensure customer has upi history
        cust_method_map[cid] = "upi,card" if "card" in cust_method_map[cid] else "upi"
        pay_methods[idx] = "card"
        error_sources[idx] = "bank"
        error_steps[idx] = "payment_authentication"
        error_reasons[idx] = "incorrect_otp"
        error_codes[idx] = "BAD_REQUEST_AUTHENTICATION_FAILED"
        error_descriptions[idx] = "Payment failed at bank 3D-Secure authentication stage."
        attempt_numbers[idx] = rng.choice([1, 2], p=[0.85, 0.15])
        pattern_labels[idx] = "pattern_a_card_auth"
        
        # Payment link gives customer alternate method (UPI) -> 80% recovery!
        latent_prob_payment_link[idx] = 0.80
        latent_prob_delayed_retry[idx] = 0.15
        latent_prob_reminder[idx] = 0.35
        latent_prob_no_action[idx] = 0.02

    # Pattern B: Network / timeout failure -> Delayed retry high recovery
    for idx in idx_pattern_b:
        pay_methods[idx] = rng.choice(["upi", "netbanking", "card"], p=[0.60, 0.25, 0.15])
        error_sources[idx] = "network"
        error_steps[idx] = "payment_authorization"
        error_reasons[idx] = "gateway_timeout"
        error_codes[idx] = "GATEWAY_ERROR_TIMED_OUT"
        error_descriptions[idx] = "Bank gateway did not respond within timeout window."
        attempt_numbers[idx] = 1
        pattern_labels[idx] = "pattern_b_transient_network"
        
        # Delayed retry allows bank network to recover -> 75% recovery!
        latent_prob_payment_link[idx] = 0.35
        latent_prob_delayed_retry[idx] = 0.75
        latent_prob_reminder[idx] = 0.20
        latent_prob_no_action[idx] = 0.03

    # Pattern C: Repeated failures -> No action optimal
    for idx in idx_pattern_c:
        pay_methods[idx] = rng.choice(["card", "upi"], p=[0.70, 0.30])
        error_sources[idx] = "customer"
        error_steps[idx] = "payment_authorization"
        error_reasons[idx] = "insufficient_funds"
        error_codes[idx] = "BAD_REQUEST_PAYMENT_DECLINED"
        error_descriptions[idx] = "Payment declined due to insufficient customer balance."
        attempt_numbers[idx] = rng.choice([3, 4, 5], p=[0.70, 0.20, 0.10])
        pattern_labels[idx] = "pattern_c_repeated_failure"
        
        # Repeated decline / exhaustion -> low recovery across all interventions
        latent_prob_payment_link[idx] = 0.04
        latent_prob_delayed_retry[idx] = 0.02
        latent_prob_reminder[idx] = 0.03
        latent_prob_no_action[idx] = 0.01

    # Pattern D: General / miscellaneous failures
    for idx in idx_pattern_d:
        pay_methods[idx] = rng.choice(methods, p=[0.50, 0.30, 0.15, 0.05])
        error_sources[idx] = rng.choice(["bank", "customer", "business"], p=[0.40, 0.40, 0.20])
        error_steps[idx] = rng.choice(["payment_authorization", "payment_initiation"])
        error_reasons[idx] = rng.choice(["payment_cancelled", "invalid_cvv", "transaction_limit_exceeded"])
        error_codes[idx] = "PAYMENT_FAILED_GENERAL"
        error_descriptions[idx] = "Payment attempt was unsuccessful."
        attempt_numbers[idx] = rng.choice([1, 2], p=[0.75, 0.25])
        pattern_labels[idx] = "pattern_d_general"
        
        latent_prob_payment_link[idx] = 0.25
        latent_prob_delayed_retry[idx] = 0.20
        latent_prob_reminder[idx] = 0.15
        latent_prob_no_action[idx] = 0.02

    # Payment timestamps: shortly after order date
    pay_dates = [
        order_date_map[oid] + timedelta(minutes=int(rng.integers(1, 45)))
        for oid in pay_orders
    ]
    captured_dates = [
        d + timedelta(seconds=int(rng.integers(5, 60))) if s == "captured" else None
        for d, s in zip(pay_dates, status_array)
    ]

    payments_df = pd.DataFrame({
        "id": payment_ids,
        "order_id": pay_orders,
        "customer_id": pay_customers,
        "merchant_id": merchant_id,
        "amount": pay_amounts,
        "currency": "INR",
        "method": pay_methods,
        "status": status_array,
        "error_source": error_sources,
        "error_step": error_steps,
        "error_reason": error_reasons,
        "error_code": error_codes,
        "error_description": error_descriptions,
        "attempt_number": attempt_numbers,
        "pattern_label": pattern_labels,
        "dataset_split": pay_splits,
        "created_at": pay_dates,
        "captured_at": captured_dates,
        "razorpay_payment_id": [f"pay_rp_{i+1:07d}" for i in range(n_payments)],
    })

    # Update customer aggregate metrics in customers_df
    # Group payments by customer to compute real aggregates
    agg_df = payments_df.groupby("customer_id").agg(
        total_payments=("id", "count"),
        successful_payments=("status", lambda s: (s == "captured").sum()),
        failed_payments=("status", lambda s: (s == "failed").sum()),
        aov=("amount", "mean"),
        last_payment=("created_at", "max"),
    ).reset_index()

    customers_df = customers_df.merge(agg_df, left_on="id", right_on="customer_id", how="left")
    customers_df["total_payments"] = customers_df["total_payments"].fillna(0).astype(int)
    customers_df["successful_payments"] = customers_df["successful_payments"].fillna(0).astype(int)
    customers_df["failed_payments"] = customers_df["failed_payments"].fillna(0).astype(int)
    customers_df["average_order_value"] = customers_df["aov"].fillna(0.0)
    customers_df["last_payment_at"] = customers_df["last_payment"]
    customers_df["successful_methods"] = customers_df["id"].map(cust_method_map)
    customers_df = customers_df.drop(columns=["customer_id", "aov", "last_payment"])

    # 5. Recovery Opportunities (one for each failed payment)
    opp_ids = [f"opp_{i+1:06d}" for i in range(n_actual_failed)]
    failed_payments = payments_df[payments_df["status"] == "failed"].copy()
    failed_payments["opp_id"] = opp_ids

    opportunities_df = pd.DataFrame({
        "id": opp_ids,
        "payment_id": failed_payments["id"].values,
        "merchant_id": merchant_id,
        "status": "open",
        "amount_at_risk": failed_payments["amount"].values,
        "dataset_split": failed_payments["dataset_split"].values,
        "detected_at": failed_payments["created_at"].values,
        "resolved_at": [None] * n_actual_failed,
        "recovered_amount": [None] * n_actual_failed,
    })

    # 6. Simulated Ground Truth Outcomes
    # Generates realistic true recovery outcomes for each intervention strategy
    # (used for counterfactual evaluation and test validation)
    outcomes_df = pd.DataFrame({
        "payment_id": payment_ids,
        "dataset_split": pay_splits,
        "pattern_label": pattern_labels,
        "latent_prob_payment_link": latent_prob_payment_link,
        "latent_prob_delayed_retry": latent_prob_delayed_retry,
        "latent_prob_reminder": latent_prob_reminder,
        "latent_prob_no_action": latent_prob_no_action,
        # Actual realization under each intervention using RNG draws:
        "realized_payment_link_recovered": rng.random(n_payments) < latent_prob_payment_link,
        "realized_delayed_retry_recovered": rng.random(n_payments) < latent_prob_delayed_retry,
        "realized_reminder_recovered": rng.random(n_payments) < latent_prob_reminder,
        "realized_no_action_recovered": rng.random(n_payments) < latent_prob_no_action,
    })
    # Filter ground truth outcomes to only failed payments
    outcomes_df = outcomes_df[outcomes_df["pattern_label"] != "none"].copy().reset_index(drop=True)

    result = {
        "merchants": merchants_df,
        "customers": customers_df,
        "orders": orders_df,
        "payments": payments_df,
        "opportunities": opportunities_df,
        "ground_truth_outcomes": outcomes_df,
    }

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        for name, df in result.items():
            df.to_csv(os.path.join(output_dir, f"{name}.csv"), index=False)

    return result
