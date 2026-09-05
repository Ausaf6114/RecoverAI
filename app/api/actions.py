"""
API routes for recovery actions.

Per docs/kb/22_API_SPECIFICATION.md:
- GET /recovery/actions/{id}: fetch action status and audit info
- POST /recovery/actions/{id}/approve: approve a gated recovery action
- POST /recovery/actions/{id}/execute: execute an approved recovery action
"""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models import RecoveryAction, AgentDecision, ActionStatus

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
    Transitions status from 'approved' (or 'pending') to 'completed'
    and stages the execution reference.
    """
    action = db.get(RecoveryAction, id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Recovery action '{id}' not found.")

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

    # In Phase 3, mock-execute and set reference
    action.status = ActionStatus.completed.value
    action.executed_at = datetime.now(timezone.utc)
    if not action.external_reference_id:
        action.external_reference_id = f"exec_{action.strategy}_{action.id}"

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
