"""
Webhook → Recovery Outcome Attribution.

Attributes captured payments and paid payment links to open RecoveryActions,
measuring realized recovery value, time-to-recovery, and updating opportunities.
"""
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.db.models import (
    RecoveryOpportunity,
    RecoveryAction,
    RecoveryOutcome,
    AuditEvent,
    Payment,
    ActionStatus,
    OpportunityStatus,
)

logger = logging.getLogger(__name__)


def attribute_webhook_event(
    event_id: str,
    event_type: str,
    payment_id: Optional[str],
    payment_link_id: Optional[str],
    order_id: Optional[str],
    amount: Optional[int],
    session: Session,
) -> Dict[str, Any]:
    """
    Attempts to attribute an incoming webhook payment event to an open recovery action.

    Matches on:
    1. external_reference_id == payment_link_id (for payment_link.paid)
    2. payment_id or order_id correlation (for payment.captured)

    Returns:
        Dict indicating whether attribution succeeded and linked entities.
    """
    now = datetime.now(timezone.utc)
    matched_action: Optional[RecoveryAction] = None

    # Only recovery-confirming events are attributed
    if event_type not in ("payment_link.paid", "payment.captured"):
        return {"attributed": False, "reason": f"Event type '{event_type}' is not a recovery-confirming event."}

    # Match Attempt 1: Payment Link ID matching external_reference_id
    if payment_link_id:
        matched_action = (
            session.query(RecoveryAction)
            .filter(RecoveryAction.external_reference_id == payment_link_id)
            .first()
        )

    # Match Attempt 2: Order ID correlation to Opportunity
    if not matched_action and order_id:
        opp = (
            session.query(RecoveryOpportunity)
            .join(Payment, RecoveryOpportunity.payment_id == Payment.id)
            .filter(Payment.order_id == order_id)
            .first()
        )
        if opp and opp.actions:
            # Pick latest action
            matched_action = sorted(opp.actions, key=lambda a: a.created_at, reverse=True)[0]

    # Match Attempt 3: Direct Payment ID correlation
    if not matched_action and payment_id:
        opp = (
            session.query(RecoveryOpportunity)
            .filter(RecoveryOpportunity.payment_id == payment_id)
            .first()
        )
        if opp and opp.actions:
            matched_action = sorted(opp.actions, key=lambda a: a.created_at, reverse=True)[0]

    if not matched_action:
        return {
            "attributed": False,
            "reason": "No matching recovery action found for payment / payment link.",
            "payment_link_id": payment_link_id,
            "payment_id": payment_id,
        }

    # Check for existing outcome (idempotent)
    existing_outcome = session.query(RecoveryOutcome).filter_by(action_id=matched_action.id).first()
    if existing_outcome:
        return {
            "attributed": True,
            "duplicate": True,
            "action_id": matched_action.id,
            "opportunity_id": matched_action.opportunity_id,
            "recovered_amount": existing_outcome.recovered_amount,
        }

    # Calculate time to recovery (handling both SQLite naive and Postgres aware datetimes)
    time_to_recovery = None
    if matched_action.created_at:
        created_at = matched_action.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        diff = (now - created_at).total_seconds()
        time_to_recovery = max(1, int(diff))

    recovered_amount = amount or 0

    # 1. Create RecoveryOutcome record
    outcome = RecoveryOutcome(
        id=f"out_{uuid.uuid4().hex[:12]}",
        action_id=matched_action.id,
        success=True,
        recovered_amount=recovered_amount,
        time_to_recovery_seconds=time_to_recovery,
        confirming_event_id=event_id,
        confirming_payment_id=payment_id,
        observed_at=now,
    )
    session.add(outcome)

    # 2. Update Action Status
    matched_action.status = ActionStatus.completed.value

    # 3. Update Opportunity Status
    opp = session.get(RecoveryOpportunity, matched_action.opportunity_id)
    if opp:
        opp.status = OpportunityStatus.recovered.value
        opp.recovered_amount = recovered_amount
        opp.resolved_at = now

    # 4. Audit Trail
    audit = AuditEvent(
        id=f"aud_{uuid.uuid4().hex[:12]}",
        entity_type="opportunity",
        entity_id=matched_action.opportunity_id,
        event_type="recovery.attributed",
        detail=f"Successfully attributed {event_type} (amount: ₹{recovered_amount/100:.2f}) to action {matched_action.id}.",
        created_at=now,
    )
    session.add(audit)
    session.flush()

    logger.info(
        f"Attribution success: event {event_id} ({event_type}) -> "
        f"action {matched_action.id}, recovered ₹{recovered_amount/100:.2f}"
    )

    return {
        "attributed": True,
        "action_id": matched_action.id,
        "opportunity_id": matched_action.opportunity_id,
        "recovered_amount": recovered_amount,
        "time_to_recovery_seconds": time_to_recovery,
    }
