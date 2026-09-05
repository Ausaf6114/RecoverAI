"""
RecoverAI held-out evaluation vs baseline policy.

Computes primary and secondary metrics from docs/kb/21_MEASUREMENT_AND_EXPERIMENTATION.md:
- Incremental Revenue Recovered = RecoverAI recovered GMV − baseline recovered GMV
- Recovery Rate uplift
- Net ROI accounting for operational action costs
- Action distribution and guardrail compliance
"""
from typing import Dict, Any, Optional
import pandas as pd
from app.domain.models import PaymentContext, MerchantPolicy
from app.agent.decision_engine import RecoveryDecisionEngine, DEFAULT_ACTION_COSTS
from app.ml.predictor import RecoveryPredictor
from simulator.generator import generate_dataset
from simulator.baseline_eval import evaluate_baseline_on_held_out


def evaluate_recoverai_on_held_out(
    dataset: Optional[Dict[str, pd.DataFrame]] = None,
    engine: Optional[RecoveryDecisionEngine] = None,
    policy: Optional[MerchantPolicy] = None,
) -> Dict[str, Any]:
    """
    Evaluates RecoverAI expected-value decision engine on held-out failed payments.
    """
    if dataset is None:
        dataset = generate_dataset(seed=42, n_payments=30000)

    effective_policy = policy or MerchantPolicy()
    decision_engine = engine or RecoveryDecisionEngine()

    payments = dataset["payments"]
    customers = dataset["customers"]
    outcomes = dataset["ground_truth_outcomes"]

    mask = (payments["status"] == "failed") & (payments["dataset_split"] == "held_out")
    held_out_payments = payments[mask].copy().reset_index(drop=True)

    merged = held_out_payments.merge(
        customers[["id", "opted_out", "successful_methods", "total_payments", "successful_payments", "failed_payments"]],
        left_on="customer_id",
        right_on="id",
        how="left",
        suffixes=("", "_cust"),
    )

    merged = merged.merge(
        outcomes[[
            "payment_id",
            "realized_payment_link_recovered",
            "realized_delayed_retry_recovered",
            "realized_reminder_recovered",
            "realized_no_action_recovered"
        ]],
        left_on="id",
        right_on="payment_id",
        how="inner",
        suffixes=("", "_gt"),
    )

    total_failed = len(merged)
    recovered_count = 0
    recovered_gmv = 0
    total_cost = 0.0
    requires_approval_count = 0
    action_counts = {
        "payment_link": 0,
        "delayed_retry": 0,
        "reminder": 0,
        "no_action": 0,
    }

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

        decision = decision_engine.evaluate(ctx, policy=effective_policy)
        selected_strategy = decision.selected_action
        action_counts[selected_strategy] = action_counts.get(selected_strategy, 0) + 1
        total_cost += decision.estimated_cost

        if decision.requires_approval:
            requires_approval_count += 1

        # Realized outcome under the selected intervention
        is_recovered = False
        if selected_strategy == "payment_link":
            is_recovered = bool(row["realized_payment_link_recovered"])
        elif selected_strategy == "delayed_retry":
            is_recovered = bool(row["realized_delayed_retry_recovered"])
        elif selected_strategy == "reminder":
            is_recovered = bool(row["realized_reminder_recovered"])
        elif selected_strategy == "no_action":
            is_recovered = bool(row["realized_no_action_recovered"])

        if is_recovered:
            recovered_count += 1
            recovered_gmv += int(row["amount"])

    recovery_rate = recovered_count / max(1, total_failed)
    net_recovered = recovered_gmv - int(total_cost)

    return {
        "model_name": "RecoverAI (Expected-Value Engine)",
        "total_failed_payments": total_failed,
        "actions_taken": sum(v for k, v in action_counts.items() if k != "no_action"),
        "recovered_count": recovered_count,
        "recovery_rate": round(recovery_rate, 4),
        "recovered_gmv_paise": recovered_gmv,
        "recovered_gmv_inr": round(recovered_gmv / 100.0, 2),
        "total_cost_paise": int(total_cost),
        "total_cost_inr": round(total_cost / 100.0, 2),
        "net_recovered_paise": net_recovered,
        "net_recovered_inr": round(net_recovered / 100.0, 2),
        "action_distribution": action_counts,
        "requires_approval_count": requires_approval_count,
    }


def compare_baseline_and_recoverai(
    dataset: Optional[Dict[str, pd.DataFrame]] = None,
    policy: Optional[MerchantPolicy] = None,
) -> Dict[str, Any]:
    """
    Runs both baseline and RecoverAI on the same held-out split and computes
    uplift, incremental GMV, and cost efficiency.
    """
    if dataset is None:
        dataset = generate_dataset(seed=42, n_payments=30000)

    effective_policy = policy or MerchantPolicy()

    # Pre-train / load predictor using the shared dataset
    predictor = RecoveryPredictor()
    engine = RecoveryDecisionEngine(predictor=predictor)

    baseline_metrics = evaluate_baseline_on_held_out(dataset, policy=effective_policy)
    recoverai_metrics = evaluate_recoverai_on_held_out(dataset, engine=engine, policy=effective_policy)

    incremental_gmv_paise = recoverai_metrics["recovered_gmv_paise"] - baseline_metrics["recovered_gmv_paise"]
    incremental_net_paise = recoverai_metrics["net_recovered_paise"] - baseline_metrics["net_recovered_paise"]
    
    base_gmv = max(1, baseline_metrics["recovered_gmv_paise"])
    uplift_pct = (incremental_gmv_paise / base_gmv) * 100.0

    return {
        "baseline": baseline_metrics,
        "recoverai": recoverai_metrics,
        "comparison": {
            "incremental_recovered_gmv_paise": incremental_gmv_paise,
            "incremental_recovered_gmv_inr": round(incremental_gmv_paise / 100.0, 2),
            "uplift_percentage": round(uplift_pct, 2),
            "incremental_net_profit_inr": round(incremental_net_paise / 100.0, 2),
            "recovery_rate_difference": round(
                recoverai_metrics["recovery_rate"] - baseline_metrics["recovery_rate"], 4
            ),
        }
    }


if __name__ == "__main__":
    report = compare_baseline_and_recoverai()
    print("==================================================")
    print("      RECOVERAI HELD-OUT EVALUATION REPORT        ")
    print("==================================================")
    print(f"Total Held-Out Failed Payments: {report['baseline']['total_failed_payments']}")
    print(f"Baseline Recovered GMV:         INR {report['baseline']['recovered_gmv_inr']:,.2f} ({report['baseline']['recovery_rate']:.1%})")
    print(f"RecoverAI Recovered GMV:        INR {report['recoverai']['recovered_gmv_inr']:,.2f} ({report['recoverai']['recovery_rate']:.1%})")
    print(f"Incremental Revenue Recovered:  INR {report['comparison']['incremental_recovered_gmv_inr']:,.2f}")
    print(f"Uplift:                         +{report['comparison']['uplift_percentage']:.2f}%")
    print(f"Incremental Net Profit:         INR {report['comparison']['incremental_net_profit_inr']:,.2f}")
    print(f"Action Distribution:            {report['recoverai']['action_distribution']}")
    print("==================================================")
