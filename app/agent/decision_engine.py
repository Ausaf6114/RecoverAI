"""
Recovery decision engine for RecoverAI.

Selects optimal recovery interventions using expected-value optimization:
Expected Value = P(recovery | context, action) × amount − action_cost
subject to merchant guardrails.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from app.domain.models import PaymentContext, RecoveryCandidate, MerchantPolicy
from app.domain.guardrails import apply_guardrails_to_candidates, check_approval_requirement
from app.ml.predictor import RecoveryPredictor

# Cost structure per intervention in paise (INR)
DEFAULT_ACTION_COSTS: Dict[str, float] = {
    "payment_link": 500.0,    # ₹5.00 SMS / WhatsApp link dispatch
    "delayed_retry": 50.0,    # ₹0.50 backend API / scheduled retry
    "reminder": 100.0,        # ₹1.00 reminder push notification
    "no_action": 0.0,         # ₹0.00
}


@dataclass
class DecisionResult:
    """Audit-ready decision output generated for a payment recovery opportunity."""
    payment_id: str
    selected_action: str
    confidence: float
    expected_recovery_value: float   # in paise
    estimated_cost: float            # in paise
    requires_approval: bool
    guardrail_passed: bool
    candidates: List[RecoveryCandidate] = field(default_factory=list)
    rationale: str = ""


class RecoveryDecisionEngine:
    """
    Deterministic expected-value decision engine with merchant guardrails.
    """

    def __init__(
        self,
        predictor: Optional[RecoveryPredictor] = None,
        action_costs: Optional[Dict[str, float]] = None,
    ):
        self.predictor = predictor or RecoveryPredictor()
        self.action_costs = action_costs or DEFAULT_ACTION_COSTS

    def evaluate(
        self,
        context: PaymentContext,
        policy: Optional[MerchantPolicy] = None,
    ) -> DecisionResult:
        """
        Evaluates all candidate actions for a PaymentContext and returns the optimal decision.
        """
        effective_policy = policy or MerchantPolicy()

        # Non-failed payment guardrail
        if context.status != "failed":
            no_act = RecoveryCandidate(
                strategy="no_action",
                predicted_recovery_probability=0.0,
                expected_recovery_value=0.0,
                estimated_cost=0.0,
                is_eligible=False,
                ineligibility_reason="payment_not_failed",
            )
            return DecisionResult(
                payment_id=context.payment_id,
                selected_action="no_action",
                confidence=0.0,
                expected_recovery_value=0.0,
                estimated_cost=0.0,
                requires_approval=False,
                guardrail_passed=True,
                candidates=[no_act],
                rationale="Payment status is not failed; no recovery action taken.",
            )

        # 1. Predict recovery probabilities across candidate strategies
        probs = self.predictor.predict_all_probabilities(context)

        # 2. Build raw candidate objects with Expected Value: P(rec) * amount - cost
        raw_candidates: List[RecoveryCandidate] = []
        for strategy, prob in probs.items():
            cost = self.action_costs.get(strategy, 0.0)
            if strategy == "no_action":
                ev = 0.0
            else:
                ev = round((prob * float(context.amount)) - cost, 2)

            raw_candidates.append(
                RecoveryCandidate(
                    strategy=strategy,
                    predicted_recovery_probability=prob,
                    expected_recovery_value=ev,
                    estimated_cost=cost,
                    is_eligible=True,
                )
            )

        # 3. Apply merchant guardrails (opt-out, contact cap, attempt cap, confidence floor)
        vetted_candidates = apply_guardrails_to_candidates(
            context,
            raw_candidates,
            policy=effective_policy,
        )

        # 4. Filter to eligible candidates with positive expected value
        eligible_candidates = [
            c for c in vetted_candidates
            if c.is_eligible and c.strategy != "no_action" and c.expected_recovery_value > 0
        ]

        # 5. Select action maximizing Expected Value
        if eligible_candidates:
            # Sort by expected_recovery_value descending
            best_candidate = max(eligible_candidates, key=lambda c: c.expected_recovery_value)
            selected_action = best_candidate.strategy
            confidence = best_candidate.predicted_recovery_probability
            ev = best_candidate.expected_recovery_value
            cost = best_candidate.estimated_cost
            rationale = (
                f"Selected '{selected_action}' with expected value ₹{ev/100:.2f} "
                f"(P={confidence:.1%}, cost=₹{cost/100:.2f})."
            )
        else:
            # Fall back to no_action
            no_act_cand = next((c for c in vetted_candidates if c.strategy == "no_action"), None)
            selected_action = "no_action"
            confidence = no_act_cand.predicted_recovery_probability if no_act_cand else 0.01
            ev = 0.0
            cost = 0.0
            rationale = "No eligible action produced positive expected value under guardrails; no_action chosen."

        # 6. Check manual approval threshold requirement
        requires_approval = (
            selected_action != "no_action" and
            check_approval_requirement(context, effective_policy)
        )

        return DecisionResult(
            payment_id=context.payment_id,
            selected_action=selected_action,
            confidence=confidence,
            expected_recovery_value=ev,
            estimated_cost=cost,
            requires_approval=requires_approval,
            guardrail_passed=True,
            candidates=vetted_candidates,
            rationale=rationale,
        )
