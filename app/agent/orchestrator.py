"""
RecoverAI Agent Orchestrator.

State machine implementing the 8-stage revenue recovery lifecycle:
Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Replan
"""
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.domain.models import PaymentContext, MerchantPolicy
from app.agent.state import AgentState, AgentStage
from app.agent.context_builder import build_payment_context_from_db
from app.agent.diagnosis import GeminiDiagnostician, DiagnosisResult
from app.agent.decision_engine import RecoveryDecisionEngine, DecisionResult
from app.razorpay.adapter import RazorpayActionAdapter, ExecutionResult
from app.db.models import (
    RecoveryOpportunity,
    AgentDecision,
    RecoveryAction,
    RecoveryOutcome,
    AuditEvent,
    ActionStatus,
    OpportunityStatus,
)


class RecoverAIOrchestrator:
    """
    Plain Python state machine orchestrating contextual recovery without external framework bloat.
    """

    def __init__(
        self,
        diagnostician: Optional[GeminiDiagnostician] = None,
        decision_engine: Optional[RecoveryDecisionEngine] = None,
        razorpay_adapter: Optional[RazorpayActionAdapter] = None,
    ):
        self.diagnostician = diagnostician or GeminiDiagnostician()
        self.decision_engine = decision_engine or RecoveryDecisionEngine()
        self.razorpay_adapter = razorpay_adapter or RazorpayActionAdapter()

    def run_pipeline(
        self,
        payment_id: str,
        context: Optional[PaymentContext] = None,
        policy: Optional[MerchantPolicy] = None,
        session: Optional[Session] = None,
    ) -> AgentState:
        """
        Executes the full Detect → Diagnose → Decide → Guardrail → Execute → Learn pipeline.
        """
        effective_policy = policy or MerchantPolicy()

        # 1. Detect
        state = self.detect(payment_id, context=context, session=session)
        if state.stage == AgentStage.COMPLETED:
            return state

        # 2. Diagnose
        self.diagnose(state)

        # 3. Decide
        self.decide(state, policy=effective_policy)

        # 4. Guardrail
        self.guardrail(state, policy=effective_policy)

        # 5. Execute
        self.execute(state, session=session)

        # 6. Learn & Audit
        self.learn(state, session=session)

        return state

    def detect(
        self,
        payment_id: str,
        context: Optional[PaymentContext] = None,
        session: Optional[Session] = None,
    ) -> AgentState:
        """Stage 1: Detect payment failure and establish opportunity context."""
        state = AgentState(payment_id=payment_id)

        # Context resolution
        if context is not None:
            state.context = context
        elif session is not None:
            state.context = build_payment_context_from_db(payment_id, session)

        if not state.context:
            state.transition(AgentStage.FAILED, f"Payment {payment_id} not found in database or input.")
            return state

        # Check failure status
        if state.context.status != "failed":
            state.transition(AgentStage.COMPLETED, f"Payment {payment_id} is '{state.context.status}'; no recovery needed.")
            return state

        # Establish RecoveryOpportunity in DB if session is active
        opp_id = f"opp_{uuid.uuid4().hex[:12]}"
        if session is not None:
            existing_opp = session.query(RecoveryOpportunity).filter_by(payment_id=payment_id).first()
            if existing_opp:
                opp_id = existing_opp.id
            else:
                new_opp = RecoveryOpportunity(
                    id=opp_id,
                    payment_id=payment_id,
                    merchant_id=state.context.merchant_id,
                    status=OpportunityStatus.open.value,
                    amount_at_risk=state.context.amount,
                    detected_at=datetime.now(timezone.utc),
                    dataset_split=state.context.dataset_split,
                )
                session.add(new_opp)
                session.flush()

        state.opportunity_id = opp_id
        state.transition(AgentStage.DETECTED, f"Detected opportunity {opp_id} for failed payment {payment_id}.")
        return state

    def diagnose(self, state: AgentState) -> None:
        """Stage 2: Contextual failure diagnosis using Google Gemini structured JSON."""
        if not state.context:
            return

        diag = self.diagnostician.diagnose(state.context)
        state.diagnosis = diag
        state.transition(
            AgentStage.DIAGNOSED,
            f"Diagnosis: category='{diag.failure_category}', confidence='{diag.confidence}' via {diag.provider}."
        )

    def decide(self, state: AgentState, policy: Optional[MerchantPolicy] = None) -> None:
        """Stage 3: Expected-value scoring across recovery candidate strategies."""
        if not state.context:
            return

        decision = self.decision_engine.evaluate(state.context, policy=policy)
        state.decision = decision
        state.transition(
            AgentStage.DECIDED,
            f"Decided action '{decision.selected_action}' with expected value ₹{decision.expected_recovery_value/100:.2f}."
        )

    def guardrail(self, state: AgentState, policy: Optional[MerchantPolicy] = None) -> None:
        """Stage 4: Merchant policy and approval guardrail evaluation."""
        if not state.decision:
            return

        action = state.decision.selected_action
        if state.decision.requires_approval:
            state.execution_status = "pending"
            detail = f"Action '{action}' requires merchant manual approval (amount exceeds ceiling)."
        elif action == "no_action":
            state.execution_status = "completed"
            detail = "Action 'no_action' passed guardrails; opportunity closed."
        else:
            state.execution_status = "approved"
            detail = f"Action '{action}' approved for automated execution."

        state.transition(AgentStage.GUARDRAILED, detail)

    def execute(self, state: AgentState, session: Optional[Session] = None) -> None:
        """Stage 5: Dispatch or stage the selected recovery intervention."""
        if not state.decision:
            return

        action_name = state.decision.selected_action
        action_id = f"act_{uuid.uuid4().hex[:12]}"
        state.action_id = action_id

        # Check approval requirement before external dispatch
        idempotency_key = f"idemp_{state.opportunity_id}_{action_name}"
        ext_ref = None
        ext_url = None

        if action_name == "no_action":
            state.execution_status = "completed"
            if session is not None and state.opportunity_id:
                opp = session.get(RecoveryOpportunity, state.opportunity_id)
                if opp:
                    opp.status = OpportunityStatus.no_action.value
            ext_ref = f"noop_{idempotency_key}"
        elif not state.decision.requires_approval:
            # Auto-execute via Razorpay adapter
            exec_res = self.razorpay_adapter.execute_action(
                strategy=action_name,
                context=state.context,
                idempotency_key=idempotency_key,
            )
            ext_ref = exec_res.reference_id
            ext_url = exec_res.reference_url
            state.external_reference_id = ext_ref

        # Persist action record if DB session is active
        if session is not None and state.opportunity_id:
            # 1. Persist AgentDecision record
            db_decision = AgentDecision(
                id=f"dec_{uuid.uuid4().hex[:12]}",
                opportunity_id=state.opportunity_id,
                candidate_actions_json=json.dumps([
                    {"strategy": c.strategy, "p": c.predicted_recovery_probability, "ev": c.expected_recovery_value}
                    for c in state.decision.candidates
                ]),
                selected_action=action_name,
                confidence=state.decision.confidence,
                expected_recovery_value=state.decision.expected_recovery_value,
                guardrail_passed=state.decision.guardrail_passed,
                requires_approval=state.decision.requires_approval,
                approval_status="pending" if state.decision.requires_approval else "auto_approved",
                diagnosis_summary=state.diagnosis.hypothesis if state.diagnosis else None,
                diagnosis_failure_category=state.diagnosis.failure_category if state.diagnosis else None,
                diagnosis_confidence=state.diagnosis.confidence if state.diagnosis else None,
                rationale=state.decision.rationale,
                decided_at=datetime.now(timezone.utc),
            )
            session.add(db_decision)
            session.flush()

            # 2. Persist RecoveryAction record
            db_status = ActionStatus.pending.value if state.decision.requires_approval else ActionStatus.completed.value
            db_action = RecoveryAction(
                id=action_id,
                opportunity_id=state.opportunity_id,
                decision_id=db_decision.id,
                strategy=action_name,
                status=db_status,
                external_reference_id=ext_ref,
                external_reference_url=ext_url,
                idempotency_key=idempotency_key,
                created_at=datetime.now(timezone.utc),
                executed_at=datetime.now(timezone.utc) if db_status == ActionStatus.completed.value else None,
            )
            session.add(db_action)

            # 3. Action Audit Record
            act_audit = AuditEvent(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                entity_type="action",
                entity_id=action_id,
                event_type="action.dispatched" if db_status == ActionStatus.completed.value else "action.held_for_approval",
                detail=f"Action '{action_name}' staged with reference '{ext_ref}' (idempotency: '{idempotency_key}').",
                created_at=datetime.now(timezone.utc),
            )
            session.add(act_audit)
            session.flush()

        status_label = "pending_approval" if state.decision.requires_approval else "executed"
        state.transition(AgentStage.EXECUTED, f"Action '{action_name}' status: {status_label} (ID: {action_id}, Ref: {ext_ref}).")

    def measure(
        self,
        state: AgentState,
        recovered: bool,
        recovered_amount: Optional[int] = None,
        confirming_payment_id: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> None:
        """Stage 6: Attribution and recovery outcome measurement."""
        state.recovered = recovered
        state.recovered_amount = recovered_amount or (state.context.amount if recovered else 0)

        if session is not None and state.action_id:
            outcome = RecoveryOutcome(
                id=f"out_{uuid.uuid4().hex[:12]}",
                action_id=state.action_id,
                success=recovered,
                recovered_amount=state.recovered_amount,
                confirming_payment_id=confirming_payment_id,
                observed_at=datetime.now(timezone.utc),
            )
            session.add(outcome)

            if state.opportunity_id:
                opp = session.get(RecoveryOpportunity, state.opportunity_id)
                if opp:
                    opp.status = OpportunityStatus.recovered.value if recovered else OpportunityStatus.failed.value
                    opp.recovered_amount = state.recovered_amount
                    opp.resolved_at = datetime.now(timezone.utc)
            session.flush()

        detail = f"Measurement: success={recovered}, recovered_amount={state.recovered_amount}."
        state.transition(AgentStage.MEASURED, detail)

    def learn(self, state: AgentState, session: Optional[Session] = None) -> None:
        """Stage 7: Commit immutable audit events and feedback signals."""
        if session is not None and state.opportunity_id:
            audit = AuditEvent(
                id=f"aud_{uuid.uuid4().hex[:12]}",
                entity_type="opportunity",
                entity_id=state.opportunity_id,
                event_type="agent.pipeline_completed",
                detail=json.dumps({
                    "stage": state.stage,
                    "selected_action": state.decision.selected_action if state.decision else "none",
                    "confidence": state.decision.confidence if state.decision else 0.0,
                    "execution_status": state.execution_status,
                }),
                created_at=datetime.now(timezone.utc),
            )
            session.add(audit)
            session.flush()

        state.transition(AgentStage.LEARNED, "Pipeline audit log recorded.")

    def replan(
        self,
        state: AgentState,
        reason: str,
        policy: Optional[MerchantPolicy] = None,
    ) -> bool:
        """
        Stage 8: Re-planning after action rejection or failure.
        Selects next highest viable action or escalates to human review.
        """
        if state.replan_count >= state.max_replans:
            state.transition(AgentStage.FAILED, f"Replan limit {state.max_replans} reached; escalating to human review.")
            return False

        state.replan_count += 1
        state.log_event("replan.initiated", f"Attempt {state.replan_count} due to: {reason}")

        # Invalidate current choice and select next candidate
        if state.decision and state.decision.candidates:
            remaining = [
                c for c in state.decision.candidates
                if c.strategy != state.decision.selected_action and c.is_eligible and c.expected_recovery_value > 0
            ]
            if remaining:
                next_cand = max(remaining, key=lambda c: c.expected_recovery_value)
                state.decision.selected_action = next_cand.strategy
                state.decision.confidence = next_cand.predicted_recovery_probability
                state.decision.expected_recovery_value = next_cand.expected_recovery_value
                state.decision.estimated_cost = next_cand.estimated_cost
                state.transition(AgentStage.REPLANNED, f"Replanned to alternate strategy: '{next_cand.strategy}'.")
                return True

        state.transition(AgentStage.REPLANNED, "No viable alternate strategies remaining; transitioning to no_action.")
        state.decision.selected_action = "no_action"
        return True
