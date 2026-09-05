import json
import hashlib
import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, status, Header, Depends
from app.core.config import get_settings, Settings
from app.core.security import verify_razorpay_signature
from app.db.events import WebhookEventRepository
from app.schemas.webhook import parse_razorpay_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def get_event_repo() -> WebhookEventRepository:
    """Dependency injecting the webhook event repository."""
    return WebhookEventRepository()


@router.post("/razorpay", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: Optional[str] = Header(None, alias="x-razorpay-event-id"),
    settings: Settings = Depends(get_settings),
    repo: WebhookEventRepository = Depends(get_event_repo)
):
    """
    Razorpay Webhook receiver endpoint.
    
    - Validates HMAC-SHA256 signature against raw request body using constant-time check.
    - Prevents duplicate event processing using x-razorpay-event-id.
    - Defensively parses supported payment and payment-link events.
    - Stores minimal event metadata in SQLite repository.
    """
    # 1. Require signature header
    if not x_razorpay_signature:
        logger.warning("Webhook rejection [400]: Missing X-Razorpay-Signature header")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Razorpay-Signature header"
        )

    # 2. Require configured webhook secret
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured on server"
        )

    # 3. Read raw request body
    raw_body = await request.body()

    # 4. Verify signature BEFORE parsing or processing
    if not verify_razorpay_signature(raw_body, x_razorpay_signature, secret):
        logger.warning("Webhook rejection [400]: Invalid webhook signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature"
        )

    # 5. Parse JSON defensively - reject malformed JSON without persisting
    try:
        payload = json.loads(raw_body.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a JSON object")
    except Exception:
        logger.warning("Webhook rejection [400]: Malformed JSON payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload"
        )

    # 6. Determine event idempotency key
    # Prefer x-razorpay-event-id header, then payload id/event_id, fallback to deterministic body hash
    event_id = (
        x_razorpay_event_id
        or payload.get("id")
        or payload.get("event_id")
        or f"evt_hash_{hashlib.sha256(raw_body).hexdigest()[:24]}"
    )

    # 7. Check for duplicate event (pre-check)
    if repo.is_duplicate(event_id):
        return {
            "status": "duplicate",
            "event_id": event_id,
            "message": "Event already processed"
        }

    # 8. Defensively extract event properties
    parsed = parse_razorpay_event(payload, fallback_event_id=event_id)

    # 9. Persist event race-safely (unique primary key constraint)
    inserted = repo.record_event(
        event_id=parsed.event_id,
        event_type=parsed.event_type,
        payload=payload,
        payment_id=parsed.payment_id,
        payment_link_id=parsed.payment_link_id,
        order_id=parsed.order_id,
        amount=parsed.amount,
        currency=parsed.currency,
        status=parsed.status,
        error_code=parsed.error_code,
        error_description=parsed.error_description,
        processing_status="received"
    )

    if not inserted:
        # Caught concurrent race duplicate
        return {
            "status": "duplicate",
            "event_id": event_id,
            "message": "Event already processed"
        }

    return {
        "status": "received",
        "event_id": event_id,
        "event_type": parsed.event_type
    }
