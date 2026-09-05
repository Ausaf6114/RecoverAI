"""
API routes for recovery opportunities.

Per docs/kb/22_API_SPECIFICATION.md:
- GET /recovery/opportunities: list revenue-at-risk opportunities
- GET /recovery/opportunities/{id}: opportunity decision detail and timeline
- POST /recovery/opportunities/{id}/decide: run agent decision pipeline
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict

from app.db.session import get_db_session
from app.db.models import RecoveryOpportunity, Payment, AgentDecision, RecoveryAction, ActionStatus
from app.agent.orchestrator import RecoverAIOrchestrator

router = APIRouter(prefix="/recovery/opportunities", tags=["opportunities"])


def get_db():
    with get_db_session() as session:
        yield session


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OpportunitySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    payment_id: str
    merchant_id: str
    status: str
    amount_at_risk: int
    recovered_amount: Optional[int] = None
    detected_at: Optional[str] = None
    dataset_split: str
    action_id: Optional[str] = None
    action_status: Optional[str] = None
    selected_action: Optional[str] = None
    requires_approval: bool = False


class OpportunityDetail(OpportunitySummary):
    payment_method: Optional[str] = None
    error_reason: Optional[str] = None
    error_source: Optional[str] = None
    attempt_number: int = 1
    selected_action: Optional[str] = None
    requires_approval: bool = False
    diagnosis_summary: Optional[str] = None
    external_reference_id: Optional[str] = None
    external_reference_url: Optional[str] = None


class DecideResponse(BaseModel):
    opportunity_id: str
    payment_id: str
    selected_action: str
    confidence: float
    expected_recovery_value: float
    requires_approval: bool
    execution_status: Optional[str] = None
    action_id: Optional[str] = None
    external_reference_id: Optional[str] = None
    external_reference_url: Optional[str] = None
    diagnosis_category: Optional[str] = None
    diagnosis_hypothesis: Optional[str] = None
    rationale: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[OpportunitySummary])
def list_opportunities(
    status: Optional[str] = Query(None, description="Filter by opportunity status or 'pending' for pending actions"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lists recovery opportunities with optional status filter."""
    query = db.query(RecoveryOpportunity)
    if status == "pending":
        query = query.join(RecoveryAction).filter(RecoveryAction.status == ActionStatus.pending.value)
    elif status:
        query = query.filter(RecoveryOpportunity.status == status)

    opps = query.order_by(RecoveryOpportunity.detected_at.desc()).offset(offset).limit(limit).all()

    results = []
    for o in opps:
        latest_act = (
            db.query(RecoveryAction)
            .filter(RecoveryAction.opportunity_id == o.id)
            .order_by(RecoveryAction.created_at.desc())
            .first()
        )
        latest_dec = (
            db.query(AgentDecision)
            .filter(AgentDecision.opportunity_id == o.id)
            .order_by(AgentDecision.decided_at.desc())
            .first()
        )
        results.append(
            OpportunitySummary(
                id=o.id,
                payment_id=o.payment_id,
                merchant_id=o.merchant_id,
                status=o.status,
                amount_at_risk=o.amount_at_risk,
                recovered_amount=o.recovered_amount,
                detected_at=o.detected_at.isoformat() if o.detected_at else None,
                dataset_split=o.dataset_split,
                action_id=latest_act.id if latest_act else None,
                action_status=latest_act.status if latest_act else None,
                selected_action=latest_dec.selected_action if latest_dec else (latest_act.strategy if latest_act else None),
                requires_approval=latest_dec.requires_approval if latest_dec else (latest_act.status == ActionStatus.pending.value if latest_act else False),
            )
        )
    return results


@router.get("/{id}", response_model=OpportunityDetail)
def get_opportunity(
    id: str,
    db: Session = Depends(get_db),
):
    """Fetches opportunity details, linked payment info, and latest decision/action."""
    opp = db.get(RecoveryOpportunity, id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Recovery opportunity '{id}' not found.")

    payment = opp.payment
    latest_decision = (
        db.query(AgentDecision)
        .filter(AgentDecision.opportunity_id == id)
        .order_by(AgentDecision.decided_at.desc())
        .first()
    )
    latest_action = (
        db.query(RecoveryAction)
        .filter(RecoveryAction.opportunity_id == id)
        .order_by(RecoveryAction.created_at.desc())
        .first()
    )

    return OpportunityDetail(
        id=opp.id,
        payment_id=opp.payment_id,
        merchant_id=opp.merchant_id,
        status=opp.status,
        amount_at_risk=opp.amount_at_risk,
        recovered_amount=opp.recovered_amount,
        detected_at=opp.detected_at.isoformat() if opp.detected_at else None,
        dataset_split=opp.dataset_split,
        payment_method=payment.method if payment else None,
        error_reason=payment.error_reason if payment else None,
        error_source=payment.error_source if payment else None,
        attempt_number=payment.attempt_number if payment else 1,
        selected_action=latest_decision.selected_action if latest_decision else (latest_action.strategy if latest_action else None),
        requires_approval=latest_decision.requires_approval if latest_decision else (latest_action.status == ActionStatus.pending.value if latest_action else False),
        diagnosis_summary=latest_decision.diagnosis_summary if latest_decision else None,
        action_id=latest_action.id if latest_action else None,
        action_status=latest_action.status if latest_action else None,
        external_reference_id=latest_action.external_reference_id if latest_action else None,
        external_reference_url=latest_action.external_reference_url if latest_action else None,
    )


@router.post("/{id}/decide", response_model=DecideResponse)
def decide_opportunity(
    id: str,
    db: Session = Depends(get_db),
):
    """
    Triggers the RecoverAI agent decision pipeline for a specific opportunity.
    Runs Detect → Diagnose → Decide → Guardrail → Execute → Learn.
    """
    opp = db.get(RecoveryOpportunity, id)
    if not opp:
        raise HTTPException(status_code=404, detail=f"Recovery opportunity '{id}' not found.")

    orchestrator = RecoverAIOrchestrator()
    state = orchestrator.run_pipeline(payment_id=opp.payment_id, session=db)

    if not state.decision:
        raise HTTPException(status_code=500, detail="Decision engine failed to produce candidate scoring.")

    # Retrieve generated action for external reference details
    ext_url = None
    if state.action_id:
        act = db.get(RecoveryAction, state.action_id)
        if act:
            ext_url = act.external_reference_url

    return DecideResponse(
        opportunity_id=opp.id,
        payment_id=opp.payment_id,
        selected_action=state.decision.selected_action,
        confidence=state.decision.confidence,
        expected_recovery_value=state.decision.expected_recovery_value,
        requires_approval=state.decision.requires_approval,
        execution_status=state.execution_status,
        action_id=state.action_id,
        external_reference_id=state.external_reference_id,
        external_reference_url=ext_url,
        diagnosis_category=state.diagnosis.failure_category if state.diagnosis else None,
        diagnosis_hypothesis=state.diagnosis.hypothesis if state.diagnosis else None,
        rationale=state.decision.rationale,
    )
