"""
Merchant policy and eligibility guardrails for RecoverAI.

Enforces merchant rules:
- Opt-out enforcement (strict compliance)
- Maximum recovery attempts cap
- Customer contact frequency cap (for customer-facing actions like payment links and reminders)
- Amount thresholds for automated execution vs mandatory manual approval
- Minimum recovery confidence threshold
"""
from typing import List, Optional
from app.domain.models import PaymentContext, RecoveryCandidate, MerchantPolicy, GuardrailResult

# Actions that directly contact the customer (subject to customer contact caps)
CUSTOMER_CONTACT_ACTIONS = {"payment_link", "reminder"}


def evaluate_action_guardrails(
    context: PaymentContext,
    candidate: RecoveryCandidate,
    policy: Optional[MerchantPolicy] = None,
) -> GuardrailResult:
    """
    Evaluates whether a candidate recovery action satisfies merchant guardrails.
    Returns GuardrailResult indicating pass/block and the violation reason.
    """
    effective_policy = policy or MerchantPolicy()

    # Rule 1: 'no_action' always passes guardrails
    if candidate.strategy == "no_action":
        return GuardrailResult(passed=True, rule_name="no_action_allowed")

    # Rule 2: Payment must be failed to recover
    if context.status != "failed":
        return GuardrailResult(
            passed=False,
            reason="payment_not_failed",
            rule_name="payment_status_check",
        )

    # Rule 3: Opt-out enforcement (compliance requirement)
    if context.customer_opted_out:
        return GuardrailResult(
            passed=False,
            reason="customer_opted_out",
            rule_name="opt_out_enforcement",
        )

    # Rule 4: Maximum recovery attempts cap
    if context.attempt_number > effective_policy.max_recovery_attempts:
        return GuardrailResult(
            passed=False,
            reason=f"attempt_number_{context.attempt_number}_exceeds_max_{effective_policy.max_recovery_attempts}",
            rule_name="max_attempts_cap",
        )

    # Rule 5: Customer contact frequency cap (applies to customer-facing actions only)
    if candidate.strategy in CUSTOMER_CONTACT_ACTIONS:
        if context.prior_contact_count >= effective_policy.max_customer_contacts:
            return GuardrailResult(
                passed=False,
                reason=f"prior_contacts_{context.prior_contact_count}_exceeds_max_{effective_policy.max_customer_contacts}",
                rule_name="contact_frequency_cap",
            )

    # Rule 6: Minimum confidence threshold
    if candidate.predicted_recovery_probability < effective_policy.min_confidence_threshold:
        return GuardrailResult(
            passed=False,
            reason=f"confidence_{candidate.predicted_recovery_probability:.2f}_below_min_{effective_policy.min_confidence_threshold}",
            rule_name="confidence_floor",
        )

    return GuardrailResult(passed=True, rule_name="all_checks_passed")


def check_approval_requirement(
    context: PaymentContext,
    policy: Optional[MerchantPolicy] = None,
) -> bool:
    """
    Returns True if payment amount exceeds merchant's automated execution ceiling,
    requiring human approval before action dispatch.
    """
    effective_policy = policy or MerchantPolicy()
    return context.amount > effective_policy.requires_approval_above


def apply_guardrails_to_candidates(
    context: PaymentContext,
    candidates: List[RecoveryCandidate],
    policy: Optional[MerchantPolicy] = None,
) -> List[RecoveryCandidate]:
    """
    Filters or annotates candidate actions against merchant guardrails.
    Marks ineligible actions with is_eligible=False and reasons.
    """
    effective_policy = policy or MerchantPolicy()
    processed_candidates: List[RecoveryCandidate] = []

    for cand in candidates:
        guard_res = evaluate_action_guardrails(context, cand, policy=effective_policy)
        if not guard_res.passed:
            processed_candidates.append(
                RecoveryCandidate(
                    strategy=cand.strategy,
                    predicted_recovery_probability=cand.predicted_recovery_probability,
                    expected_recovery_value=cand.expected_recovery_value,
                    estimated_cost=cand.estimated_cost,
                    is_eligible=False,
                    ineligibility_reason=guard_res.reason,
                )
            )
        else:
            processed_candidates.append(cand)

    return processed_candidates
