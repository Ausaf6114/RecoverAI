"""
API routes for recovery analytics.

Per docs/kb/22_API_SPECIFICATION.md:
- GET /analytics/recovery: baseline vs RecoverAI metrics, recovered GMV, uplift, and action breakdown
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel

from app.db.session import get_db_session
from app.db.models import (
    RecoveryOpportunity,
    RecoveryAction,
    RecoveryOutcome,
    OpportunityStatus,
    ActionStatus,
)
from app.agent.decision_engine import DEFAULT_ACTION_COSTS

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_db():
    with get_db_session() as session:
        yield session


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AnalyticsResponse(BaseModel):
    total_opportunities: int
    open_opportunities: int
    recovered_opportunities: int
    recovery_rate: float
    total_at_risk_gmv_inr: float
    total_recovered_gmv_inr: float
    total_action_cost_inr: float
    net_revenue_inr: float
    action_breakdown: Dict[str, int]
    pending_approvals_count: int
    baseline_benchmark: Dict[str, Any]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/recovery", response_model=AnalyticsResponse)
def get_recovery_analytics(
    db: Session = Depends(get_db),
):
    """
    Returns live recovery performance metrics, GMV attribution,
    and comparative baseline uplift metrics.
    """
    # 1. Opportunity counts
    total_opps = db.query(func.count(RecoveryOpportunity.id)).scalar() or 0
    open_opps = (
        db.query(func.count(RecoveryOpportunity.id))
        .filter(RecoveryOpportunity.status == OpportunityStatus.open.value)
        .scalar() or 0
    )
    recovered_opps = (
        db.query(func.count(RecoveryOpportunity.id))
        .filter(RecoveryOpportunity.status == OpportunityStatus.recovered.value)
        .scalar() or 0
    )

    # 2. GMV aggregations (paise)
    total_at_risk_paise = (
        db.query(func.sum(RecoveryOpportunity.amount_at_risk)).scalar() or 0
    )
    total_recovered_paise = (
        db.query(func.sum(RecoveryOutcome.recovered_amount))
        .filter(RecoveryOutcome.success == True)
        .scalar() or 0
    )

    # 3. Action breakdown and costs
    actions = db.query(RecoveryAction.strategy, func.count(RecoveryAction.id)).group_by(RecoveryAction.strategy).all()
    action_counts: Dict[str, int] = {s: count for s, count in actions}

    total_cost_paise = sum(
        count * DEFAULT_ACTION_COSTS.get(strategy, 0.0)
        for strategy, count in action_counts.items()
    )

    # 4. Pending approvals
    pending_approvals = (
        db.query(func.count(RecoveryAction.id))
        .filter(RecoveryAction.status == ActionStatus.pending.value)
        .scalar() or 0
    )

    # 5. Baseline benchmark comparison (35% fixed heuristic recovery)
    baseline_rate = 0.35
    baseline_gmv_paise = int(baseline_rate * total_recovered_paise) if total_recovered_paise > 0 else 0
    incremental_paise = total_recovered_paise - baseline_gmv_paise
    uplift_pct = (incremental_paise / max(1, baseline_gmv_paise)) * 100.0 if baseline_gmv_paise > 0 else 0.0

    recovery_rate = (recovered_opps / max(1, total_opps)) if total_opps > 0 else 0.0
    net_revenue_paise = total_recovered_paise - int(total_cost_paise)

    return AnalyticsResponse(
        total_opportunities=total_opps,
        open_opportunities=open_opps,
        recovered_opportunities=recovered_opps,
        recovery_rate=round(recovery_rate, 4),
        total_at_risk_gmv_inr=round(total_at_risk_paise / 100.0, 2),
        total_recovered_gmv_inr=round(total_recovered_paise / 100.0, 2),
        total_action_cost_inr=round(total_cost_paise / 100.0, 2),
        net_revenue_inr=round(net_revenue_paise / 100.0, 2),
        action_breakdown=action_counts,
        pending_approvals_count=pending_approvals,
        baseline_benchmark={
            "baseline_recovery_rate": baseline_rate,
            "baseline_recovered_gmv_inr": round(baseline_gmv_paise / 100.0, 2),
            "incremental_recovered_gmv_inr": round(incremental_paise / 100.0, 2),
            "uplift_percentage": round(uplift_pct, 2),
        },
    )
