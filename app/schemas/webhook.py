from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ParsedWebhookEvent(BaseModel):
    """Defensive representation of a parsed Razorpay webhook event."""

    event_id: str
    event_type: str
    payment_id: Optional[str] = None
    payment_link_id: Optional[str] = None
    order_id: Optional[str] = None
    amount: Optional[int] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    raw_payload: Dict[str, Any] = Field(default_factory=dict)


def parse_razorpay_event(data: Dict[str, Any], fallback_event_id: str) -> ParsedWebhookEvent:
    """
    Defensively parses a Razorpay webhook JSON payload.
    
    Does not assume rigid presence of any nested object.
    Safely navigates payload -> payment/payment_link/order -> entity.
    """
    event_type = str(data.get("event") or "unknown")

    # Resolve event_id (prefers header, falls back to payload event_id or uuid)
    event_id = fallback_event_id

    # Defensive extraction helpers
    payload_section = data.get("payload") if isinstance(data.get("payload"), dict) else {}

    # Extract payment entity
    payment_data = payload_section.get("payment", {}) if isinstance(payload_section.get("payment"), dict) else {}
    payment_entity = payment_data.get("entity", {}) if isinstance(payment_data.get("entity"), dict) else {}

    # Extract payment_link entity
    plink_data = payload_section.get("payment_link", {}) if isinstance(payload_section.get("payment_link"), dict) else {}
    plink_entity = plink_data.get("entity", {}) if isinstance(plink_data.get("entity"), dict) else {}

    # Extract order entity
    order_data = payload_section.get("order", {}) if isinstance(payload_section.get("order"), dict) else {}
    order_entity = order_data.get("entity", {}) if isinstance(order_data.get("entity"), dict) else {}

    # Candidate extraction
    payment_id = payment_entity.get("id") or data.get("payment_id")
    payment_link_id = plink_entity.get("id") or payment_entity.get("payment_link_id")
    order_id = (
        order_entity.get("id")
        or payment_entity.get("order_id")
        or plink_entity.get("order_id")
    )

    amount = (
        plink_entity.get("amount") if event_type.startswith("payment_link") else None
    ) or (
        payment_entity.get("amount")
        or plink_entity.get("amount")
        or order_entity.get("amount")
    )
    if amount is not None:
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            amount = None

    currency = (
        plink_entity.get("currency") if event_type.startswith("payment_link") else None
    ) or (
        payment_entity.get("currency")
        or plink_entity.get("currency")
        or order_entity.get("currency")
    )

    # Respect primary entity status based on event type
    if event_type.startswith("payment_link") and plink_entity.get("status"):
        status = plink_entity.get("status")
    elif event_type.startswith("order") and order_entity.get("status"):
        status = order_entity.get("status")
    else:
        status = (
            payment_entity.get("status")
            or plink_entity.get("status")
            or order_entity.get("status")
        )

    error_code = payment_entity.get("error_code")
    error_description = payment_entity.get("error_description")

    return ParsedWebhookEvent(
        event_id=event_id,
        event_type=event_type,
        payment_id=str(payment_id) if payment_id else None,
        payment_link_id=str(payment_link_id) if payment_link_id else None,
        order_id=str(order_id) if order_id else None,
        amount=amount,
        currency=str(currency) if currency else None,
        status=str(status) if status else None,
        error_code=str(error_code) if error_code else None,
        error_description=str(error_description) if error_description else None,
        raw_payload=data
    )
