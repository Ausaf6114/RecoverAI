"""
Context builder for RecoverAI agent.

Retrieves and constructs a rich PaymentContext from the database
or raw payment events, combining payment, customer profile, order,
and opportunity history.
"""
from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.models import PaymentContext
from app.db.models import Payment, Customer, Order, RecoveryOpportunity, RecoveryAction


def build_payment_context_from_db(
    payment_id: str,
    session: Session,
) -> Optional[PaymentContext]:
    """
    Builds a complete PaymentContext dataclass by querying domain models.
    """
    payment = session.get(Payment, payment_id)
    if not payment:
        return None

    customer = session.get(Customer, payment.customer_id) if payment.customer_id else None
    order = session.get(Order, payment.order_id) if payment.order_id else None
    opp = session.query(RecoveryOpportunity).filter(RecoveryOpportunity.payment_id == payment_id).first()

    # Calculate prior contacts across customer recovery actions
    prior_contact_count = 0
    if customer:
        prior_actions = (
            session.query(RecoveryAction)
            .join(RecoveryOpportunity, RecoveryAction.opportunity_id == RecoveryOpportunity.id)
            .join(Payment, RecoveryOpportunity.payment_id == Payment.id)
            .filter(
                Payment.customer_id == customer.id,
                RecoveryAction.strategy.in_(["payment_link", "reminder"]),
            )
            .count()
        )
        prior_contact_count = prior_actions

    # Parse customer successful methods
    succ_methods: List[str] = []
    if customer and customer.successful_methods:
        succ_methods = [m.strip() for m in customer.successful_methods.split(",") if m.strip()]

    return PaymentContext(
        payment_id=payment.id,
        customer_id=payment.customer_id,
        merchant_id=payment.merchant_id,
        amount=payment.amount,
        currency=payment.currency,
        method=payment.method,
        status=payment.status,
        error_source=payment.error_source,
        error_step=payment.error_step,
        error_reason=payment.error_reason,
        error_code=payment.error_code,
        error_description=payment.error_description,
        attempt_number=payment.attempt_number,
        customer_opted_out=customer.opted_out if customer else False,
        customer_total_payments=customer.total_payments if customer else 0,
        customer_successful_payments=customer.successful_payments if customer else 0,
        customer_failed_payments=customer.failed_payments if customer else 0,
        customer_successful_methods=succ_methods,
        customer_aov=customer.average_order_value if customer else None,
        order_id=order.id if order else None,
        order_category=order.category if order else None,
        prior_contact_count=prior_contact_count,
        has_open_opportunity=opp is not None and opp.status == "open",
        created_at=payment.created_at,
        dataset_split=payment.dataset_split,
    )


def build_payment_context_from_dict(data: dict) -> PaymentContext:
    """Helper to construct PaymentContext directly from dictionary (used in tests or simulation)."""
    succ_methods = data.get("customer_successful_methods", [])
    if isinstance(succ_methods, str):
        succ_methods = [m.strip() for m in succ_methods.split(",") if m.strip()]

    return PaymentContext(
        payment_id=data["payment_id"],
        customer_id=data.get("customer_id", "cust_unknown"),
        merchant_id=data.get("merchant_id", "merch_unknown"),
        amount=int(data["amount"]),
        currency=data.get("currency", "INR"),
        method=data.get("method"),
        status=data.get("status", "failed"),
        error_source=data.get("error_source"),
        error_step=data.get("error_step"),
        error_reason=data.get("error_reason"),
        error_code=data.get("error_code"),
        error_description=data.get("error_description"),
        attempt_number=int(data.get("attempt_number", 1)),
        customer_opted_out=bool(data.get("customer_opted_out", False)),
        customer_total_payments=int(data.get("customer_total_payments", 0)),
        customer_successful_payments=int(data.get("customer_successful_payments", 0)),
        customer_failed_payments=int(data.get("customer_failed_payments", 0)),
        customer_successful_methods=succ_methods,
        customer_aov=data.get("customer_aov"),
        order_id=data.get("order_id"),
        order_category=data.get("order_category"),
        prior_contact_count=int(data.get("prior_contact_count", 0)),
        has_open_opportunity=bool(data.get("has_open_opportunity", False)),
        dataset_split=data.get("dataset_split", "train"),
    )
