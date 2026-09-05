"""
API routes for recovery actions.

Per docs/kb/22_API_SPECIFICATION.md:
- GET /recovery/actions/{id}: fetch action status and audit info
- POST /recovery/actions/{id}/approve: approve a gated recovery action
- POST /recovery/actions/{id}/execute: execute an approved recovery action
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models import RecoveryAction, AgentDecision, ActionStatus, OpportunityStatus

router = APIRouter(prefix="/recovery/actions", tags=["actions"])


def get_db():
    with get_db_session() as session:
        yield session


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ActionResponse(BaseModel):
    id: str
    opportunity_id: str
    strategy: str
    status: str
    external_reference_id: Optional[str] = None
    external_reference_url: Optional[str] = None
    created_at: str
    executed_at: Optional[str] = None


class ApproveRequest(BaseModel):
    approved_by: str = "merchant_admin"
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ActionResponse])
def list_actions(
    status: Optional[str] = Query(None, description="Filter by action status"),
    opportunity_id: Optional[str] = Query(None, description="Filter by opportunity ID"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Lists recovery actions with optional status or opportunity filters."""
    query = db.query(RecoveryAction)
    if status:
        query = query.filter(RecoveryAction.status == status)
    if opportunity_id:
        query = query.filter(RecoveryAction.opportunity_id == opportunity_id)

    actions = query.order_by(RecoveryAction.created_at.desc()).offset(offset).limit(limit).all()
    return [
        ActionResponse(
            id=a.id,
            opportunity_id=a.opportunity_id,
            strategy=a.strategy,
            status=a.status,
            external_reference_id=a.external_reference_id,
            external_reference_url=a.external_reference_url,
            created_at=a.created_at.isoformat(),
            executed_at=a.executed_at.isoformat() if a.executed_at else None,
        )
        for a in actions
    ]


@router.get("/{id}", response_model=ActionResponse)
def get_action(
    id: str,
    db: Session = Depends(get_db),
):
    """Fetches details for a specific recovery action."""
    action = db.get(RecoveryAction, id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Recovery action '{id}' not found.")

    return ActionResponse(
        id=action.id,
        opportunity_id=action.opportunity_id,
        strategy=action.strategy,
        status=action.status,
        external_reference_id=action.external_reference_id,
        external_reference_url=action.external_reference_url,
        created_at=action.created_at.isoformat(),
        executed_at=action.executed_at.isoformat() if action.executed_at else None,
    )


@router.post("/{id}/approve", response_model=ActionResponse)
def approve_action(
    id: str,
    req: ApproveRequest = ApproveRequest(),
    db: Session = Depends(get_db),
):
    """
    Approves a gated recovery action held for manual review.
    Transitions status from 'pending' to 'approved'.
    """
    action = db.get(RecoveryAction, id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Recovery action '{id}' not found.")

    if action.status not in (ActionStatus.pending.value, "blocked"):
        raise HTTPException(
            status_code=400,
            detail=f"Action '{id}' is already in status '{action.status}' and cannot be approved."
        )

    action.status = ActionStatus.approved.value

    # Update associated AgentDecision if present
    if action.decision_id:
        decision = db.get(AgentDecision, action.decision_id)
        if decision:
            decision.approval_status = "approved"
            decision.approved_by = req.approved_by

    db.flush()

    return ActionResponse(
        id=action.id,
        opportunity_id=action.opportunity_id,
        strategy=action.strategy,
        status=action.status,
        external_reference_id=action.external_reference_id,
        external_reference_url=action.external_reference_url,
        created_at=action.created_at.isoformat(),
        executed_at=action.executed_at.isoformat() if action.executed_at else None,
    )


@router.post("/{id}/execute", response_model=ActionResponse)
def execute_action(
    id: str,
    db: Session = Depends(get_db),
):
    """
    Executes an approved recovery action.
    Transitions status from 'approved' to 'completed'
    and stages the execution reference.
    Enforces that approval-gated actions cannot execute before approval.
    """
    action = db.get(RecoveryAction, id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Recovery action '{id}' not found.")

    # Idempotent return if already completed
    if action.status == ActionStatus.completed.value:
        return ActionResponse(
            id=action.id,
            opportunity_id=action.opportunity_id,
            strategy=action.strategy,
            status=action.status,
            external_reference_id=action.external_reference_id,
            external_reference_url=action.external_reference_url,
            created_at=action.created_at.isoformat(),
            executed_at=action.executed_at.isoformat() if action.executed_at else None,
        )

    # Reject unapproved pending actions
    if action.status == ActionStatus.pending.value:
        raise HTTPException(
            status_code=400,
            detail=f"Action '{id}' is pending approval and cannot be executed until approved."
        )

    # Reject blocked actions
    if action.status == ActionStatus.blocked.value:
        raise HTTPException(
            status_code=400,
            detail=f"Action '{id}' was blocked by guardrails and cannot be executed."
        )

    # Must be in approved status (or retryable failed)
    if action.status not in (ActionStatus.approved.value, ActionStatus.failed.value):
        raise HTTPException(
            status_code=400,
            detail=f"Action '{id}' in status '{action.status}' is not eligible for execution."
        )

    from app.agent.context_builder import build_payment_context_from_db
    from app.razorpay.adapter import RazorpayActionAdapter
    from app.db.models import RecoveryOpportunity, AuditEvent

    opp = db.get(RecoveryOpportunity, action.opportunity_id)
    adapter = RazorpayActionAdapter()
    idempotency_key = action.idempotency_key or f"idemp_{action.id}"

    if opp:
        context = build_payment_context_from_db(opp.payment_id, db)
        if context:
            exec_res = adapter.execute_action(
                strategy=action.strategy,
                context=context,
                idempotency_key=idempotency_key,
            )
            action.external_reference_id = exec_res.reference_id
            action.external_reference_url = exec_res.reference_url

            # Handle execution failure cleanly
            if exec_res.status == "failed":
                action.status = ActionStatus.failed.value
                db.flush()

                audit_fail = AuditEvent(
                    id=f"aud_{action.id[:12]}",
                    entity_type="action",
                    entity_id=action.id,
                    event_type="action.execution_failed",
                    detail=f"Action '{action.strategy}' execution failed: {exec_res.error_message}",
                    created_at=datetime.now(timezone.utc),
                )
                db.add(audit_fail)
                db.flush()

                raise HTTPException(
                    status_code=502,
                    detail=f"Action execution failed: {exec_res.error_message or 'Provider execution error'}"
                )

    action.status = ActionStatus.completed.value
    action.executed_at = datetime.now(timezone.utc)
    if not action.external_reference_id:
        action.external_reference_id = f"exec_{action.strategy}_{action.id}"

    # Update opportunity to in_progress if still open
    if opp and opp.status == OpportunityStatus.open.value:
        opp.status = OpportunityStatus.in_progress.value

    # Audit log
    audit = AuditEvent(
        id=f"aud_{action.id[:12]}",
        entity_type="action",
        entity_id=action.id,
        event_type="action.manually_executed",
        detail=f"Action '{action.strategy}' executed via API with reference '{action.external_reference_id}'.",
        created_at=datetime.now(timezone.utc),
    )
    db.add(audit)
    db.flush()

    return ActionResponse(
        id=action.id,
        opportunity_id=action.opportunity_id,
        strategy=action.strategy,
        status=action.status,
        external_reference_id=action.external_reference_id,
        external_reference_url=action.external_reference_url,
        created_at=action.created_at.isoformat(),
        executed_at=action.executed_at.isoformat() if action.executed_at else None,
    )
