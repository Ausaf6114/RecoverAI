"""
Deterministic baseline recovery policy for RecoverAI.

Serves as the fixed-policy comparison group per docs/kb/21_MEASUREMENT_AND_EXPERIMENTATION.md:
"Use a fixed/simple recovery policy as the comparison group."
"Incremental Revenue Recovered = RecoverAI recovered GMV - baseline recovered GMV"
"""
from typing import Optional, List
from app.domain.models import PaymentContext, RecoveryCandidate, MerchantPolicy

# Standard baseline success rate (illustrative benchmark rate)
BASELINE_PAYMENT_LINK_PROBABILITY = 0.35
BASELINE_DELAYED_RETRY_PROBABILITY = 0.25


def evaluate_baseline_policy(
    context: PaymentContext,
    policy: Optional[MerchantPolicy] = None,
) -> RecoveryCandidate:
    """
    Evaluates the fixed deterministic baseline recovery policy for a payment context.

    Rules:
    1. If status != 'failed', no action needed.
    2. If customer has opted out, no action (guardrail).
    3. If payment attempt > 2 (or policy max_recovery_attempts), no action.
    4. If prior customer contacts >= policy max_customer_contacts (default 2), no action.
    5. Otherwise: select standard 'payment_link' intervention with fixed baseline recovery rate.
    """
    effective_policy = policy or MerchantPolicy()

    # Rule 1: Non-failed payments
    if context.status != "failed":
        return RecoveryCandidate(
            strategy="no_action",
            predicted_recovery_probability=0.0,
            expected_recovery_value=0.0,
            is_eligible=False,
            ineligibility_reason="payment_not_failed",
        )

    # Rule 2: Customer opted out
    if context.customer_opted_out:
        return RecoveryCandidate(
            strategy="no_action",
            predicted_recovery_probability=0.0,
            expected_recovery_value=0.0,
            is_eligible=False,
            ineligibility_reason="customer_opted_out",
        )

    # Rule 3: Max attempts exceeded
    if context.attempt_number > effective_policy.max_recovery_attempts or context.attempt_number > 2:
        return RecoveryCandidate(
            strategy="no_action",
            predicted_recovery_probability=0.0,
            expected_recovery_value=0.0,
            is_eligible=False,
            ineligibility_reason="max_attempts_exceeded",
        )

    # Rule 4: Max customer contacts exceeded
    if context.prior_contact_count >= effective_policy.max_customer_contacts:
        return RecoveryCandidate(
            strategy="no_action",
            predicted_recovery_probability=0.0,
            expected_recovery_value=0.0,
            is_eligible=False,
            ineligibility_reason="max_contacts_exceeded",
        )

    # Standard eligible baseline action: Payment Link
    prob = BASELINE_PAYMENT_LINK_PROBABILITY
    expected_value = round(prob * context.amount, 2)

    return RecoveryCandidate(
        strategy="payment_link",
        predicted_recovery_probability=prob,
        expected_recovery_value=expected_value,
        estimated_cost=0.0,
        is_eligible=True,
        ineligibility_reason=None,
    )


def batch_evaluate_baseline(
    contexts: List[PaymentContext],
    policy: Optional[MerchantPolicy] = None,
) -> List[RecoveryCandidate]:
    """Evaluates the baseline policy across a list of payment contexts."""
    return [evaluate_baseline_policy(ctx, policy=policy) for ctx in contexts]
