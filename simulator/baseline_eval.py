"""
Baseline policy evaluation on held-out evaluation split.

Evaluates the deterministic baseline recovery policy per
docs/kb/21_MEASUREMENT_AND_EXPERIMENTATION.md.
"""
from typing import Dict, Any, Optional
import pandas as pd
from app.domain.models import PaymentContext, MerchantPolicy
from app.domain.baseline import evaluate_baseline_policy
from simulator.generator import generate_dataset


def evaluate_baseline_on_held_out(
    dataset: Optional[Dict[str, pd.DataFrame]] = None,
    policy: Optional[MerchantPolicy] = None,
) -> Dict[str, Any]:
    """
    Runs baseline policy across held-out failed payments and evaluates realized recovery.

    Args:
        dataset: Dict of DataFrames from generate_dataset. If None, generates standard dataset.
        policy: MerchantPolicy guardrails.

    Returns:
        Dict containing baseline metrics:
        - total_failed_payments
        - actions_taken
        - recovered_count
        - recovery_rate
        - recovered_gmv_paise
        - total_cost_paise
        - net_recovered_paise
        - action_distribution
    """
    if dataset is None:
        dataset = generate_dataset(seed=42, n_payments=30000)

    effective_policy = policy or MerchantPolicy()
    payments = dataset["payments"]
    customers = dataset["customers"]
    outcomes = dataset["ground_truth_outcomes"]

    # Filter held-out failed payments
    mask = (payments["status"] == "failed") & (payments["dataset_split"] == "held_out")
    held_out_payments = payments[mask].copy().reset_index(drop=True)

    # Merge customer info
    merged = held_out_payments.merge(
        customers[["id", "opted_out", "successful_methods", "total_payments", "successful_payments", "failed_payments"]],
        left_on="customer_id",
        right_on="id",
        how="left",
        suffixes=("", "_cust"),
    )

    # Merge ground truth realized outcomes
    merged = merged.merge(
        outcomes[["payment_id", "realized_payment_link_recovered", "realized_delayed_retry_recovered", "realized_reminder_recovered", "realized_no_action_recovered"]],
        left_on="id",
        right_on="payment_id",
        how="inner",
        suffixes=("", "_gt"),
    )

    total_failed = len(merged)
    recovered_count = 0
    recovered_gmv = 0
    total_cost = 0.0
    action_counts = {"payment_link": 0, "no_action": 0}

    # Action costs (paise): payment_link = 500 (₹5), no_action = 0
    COST_MAP = {"payment_link": 500.0, "no_action": 0.0}

    for _, row in merged.iterrows():
        succ_methods = [m.strip() for m in str(row.get("successful_methods", "")).split(",") if m.strip()]
        ctx = PaymentContext(
            payment_id=row["id"],
            customer_id=row["customer_id"],
            merchant_id=row["merchant_id"],
            amount=int(row["amount"]),
            currency=row["currency"],
            method=row.get("method"),
            status=row["status"],
            error_source=row.get("error_source"),
            error_step=row.get("error_step"),
            error_reason=row.get("error_reason"),
            attempt_number=int(row.get("attempt_number", 1)),
            customer_opted_out=bool(row.get("opted_out", False)),
            customer_total_payments=int(row.get("total_payments", 1)),
            customer_successful_payments=int(row.get("successful_payments", 0)),
            customer_failed_payments=int(row.get("failed_payments", 0)),
            customer_successful_methods=succ_methods,
            prior_contact_count=0,
            dataset_split="held_out",
        )

        cand = evaluate_baseline_policy(ctx, policy=effective_policy)
        chosen_strategy = cand.strategy if cand.is_eligible else "no_action"
        action_counts[chosen_strategy] = action_counts.get(chosen_strategy, 0) + 1
        total_cost += COST_MAP.get(chosen_strategy, 0.0)

        # Look up realized outcome from simulator
        is_recovered = False
        if chosen_strategy == "payment_link":
            is_recovered = bool(row["realized_payment_link_recovered"])
        elif chosen_strategy == "no_action":
            is_recovered = bool(row["realized_no_action_recovered"])

        if is_recovered:
            recovered_count += 1
            recovered_gmv += int(row["amount"])

    recovery_rate = recovered_count / max(1, total_failed)
    net_recovered = recovered_gmv - int(total_cost)

    return {
        "model_name": "Baseline (Fixed Heuristic)",
        "total_failed_payments": total_failed,
        "actions_taken": action_counts.get("payment_link", 0),
        "recovered_count": recovered_count,
        "recovery_rate": round(recovery_rate, 4),
        "recovered_gmv_paise": recovered_gmv,
        "recovered_gmv_inr": round(recovered_gmv / 100.0, 2),
        "total_cost_paise": int(total_cost),
        "total_cost_inr": round(total_cost / 100.0, 2),
        "net_recovered_paise": net_recovered,
        "net_recovered_inr": round(net_recovered / 100.0, 2),
        "action_distribution": action_counts,
    }


if __name__ == "__main__":
    res = evaluate_baseline_on_held_out()
    print("Baseline Evaluation Results:")
    for k, v in res.items():
        print(f"  {k}: {v}")
