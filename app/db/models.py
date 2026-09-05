"""
SQLAlchemy ORM models for RecoverAI domain tables.

These models cover the full domain from 16_DATA_MODEL.md and 25_DATABASE_SPECIFICATION.md.
The existing webhook_events table (Phase 0, raw sqlite3) is intentionally NOT managed here
to preserve backward compatibility with the working webhook receiver.
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    String, Integer, BigInteger, Float, Boolean, Text, DateTime,
    ForeignKey, Index, UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PaymentMethod(str, enum.Enum):
    card = "card"
    upi = "upi"
    netbanking = "netbanking"
    wallet = "wallet"
    emi = "emi"
    cod = "cod"


class PaymentStatus(str, enum.Enum):
    created = "created"
    authorized = "authorized"
    captured = "captured"
    failed = "failed"
    refunded = "refunded"


class FailureSource(str, enum.Enum):
    customer = "customer"
    business = "business"
    bank = "bank"
    internal = "internal"
    network = "network"
    unknown = "unknown"


class RecoveryStrategy(str, enum.Enum):
    payment_link = "payment_link"      # S-01
    delayed_retry = "delayed_retry"    # S-02
    reminder = "reminder"              # S-03
    no_action = "no_action"            # S-04
    human_review = "human_review"      # S-05


class ActionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    executing = "executing"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"    # stopped by guardrail


class OpportunityStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    recovered = "recovered"
    failed = "failed"
    no_action = "no_action"
    expired = "expired"


class DatasetSplit(str, enum.Enum):
    train = "train"
    held_out = "held_out"


# ---------------------------------------------------------------------------
# Merchant
# ---------------------------------------------------------------------------

class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Policy defaults (overridden by MerchantPolicy if present)
    max_recovery_attempts: Mapped[int] = mapped_column(Integer, default=3)
    max_customer_contacts: Mapped[int] = mapped_column(Integer, default=2)
    min_confidence_threshold: Mapped[float] = mapped_column(Float, default=0.65)
    auto_execute_below_amount: Mapped[int] = mapped_column(BigInteger, default=50000)  # paise
    requires_approval_above: Mapped[int] = mapped_column(BigInteger, default=500000)  # paise

    customers: Mapped[list["Customer"]] = relationship("Customer", back_populates="merchant")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="merchant")


# ---------------------------------------------------------------------------
# Customer
# ---------------------------------------------------------------------------

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.id"), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(32))
    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)

    # Aggregate stats (updated via batch job or event stream)
    total_payments: Mapped[int] = mapped_column(Integer, default=0)
    successful_payments: Mapped[int] = mapped_column(Integer, default=0)
    failed_payments: Mapped[int] = mapped_column(Integer, default=0)
    average_order_value: Mapped[Optional[float]] = mapped_column(Float)
    last_payment_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Comma-separated successful payment methods, e.g. "upi,card"
    successful_methods: Mapped[Optional[str]] = mapped_column(String(255))
    # Dataset split for synthetic evaluation
    dataset_split: Mapped[str] = mapped_column(String(16), default="train")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="customers")
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="customer")

    __table_args__ = (
        Index("idx_customers_merchant_id", "merchant_id"),
    )


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), ForeignKey("merchants.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(String(64), ForeignKey("customers.id"), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # paise
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    category: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # Razorpay order ID if synced
    razorpay_order_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    dataset_split: Mapped[str] = mapped_column(String(16), default="train")

    merchant: Mapped["Merchant"] = relationship("Merchant", back_populates="orders")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="order")

    __table_args__ = (
        Index("idx_orders_merchant_id", "merchant_id"),
        Index("idx_orders_customer_id", "customer_id"),
        Index("idx_orders_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("orders.id"))
    customer_id: Mapped[str] = mapped_column(String(64), ForeignKey("customers.id"), nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)  # paise
    currency: Mapped[str] = mapped_column(String(8), default="INR")
    method: Mapped[Optional[str]] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    # Failure fields
    error_source: Mapped[Optional[str]] = mapped_column(String(64))
    error_step: Mapped[Optional[str]] = mapped_column(String(64))
    error_reason: Mapped[Optional[str]] = mapped_column(String(128))
    error_code: Mapped[Optional[str]] = mapped_column(String(64))
    error_description: Mapped[Optional[str]] = mapped_column(Text)
    # Razorpay IDs
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    # Timing
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Attempt tracking
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    dataset_split: Mapped[str] = mapped_column(String(16), default="train")

    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="payments")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="payments")
    opportunity: Mapped[Optional["RecoveryOpportunity"]] = relationship("RecoveryOpportunity", back_populates="payment", uselist=False)

    __table_args__ = (
        Index("idx_payments_customer_id", "customer_id"),
        Index("idx_payments_order_id", "order_id"),
        Index("idx_payments_merchant_id", "merchant_id"),
        Index("idx_payments_status", "status"),
        Index("idx_payments_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Recovery Opportunity
# ---------------------------------------------------------------------------

class RecoveryOpportunity(Base):
    """One failed payment eligible for recovery consideration."""
    __tablename__ = "recovery_opportunities"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    payment_id: Mapped[str] = mapped_column(String(64), ForeignKey("payments.id"), unique=True, nullable=False)
    merchant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="open")
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    # Amount at risk in paise
    amount_at_risk: Mapped[int] = mapped_column(BigInteger, nullable=False)
    recovered_amount: Mapped[Optional[int]] = mapped_column(BigInteger)
    dataset_split: Mapped[str] = mapped_column(String(16), default="train")

    payment: Mapped["Payment"] = relationship("Payment", back_populates="opportunity")
    decisions: Mapped[list["AgentDecision"]] = relationship("AgentDecision", back_populates="opportunity")
    actions: Mapped[list["RecoveryAction"]] = relationship("RecoveryAction", back_populates="opportunity")

    __table_args__ = (
        Index("idx_opportunities_merchant_id", "merchant_id"),
        Index("idx_opportunities_status", "status"),
        Index("idx_opportunities_detected_at", "detected_at"),
    )


# ---------------------------------------------------------------------------
# Agent Decision
# ---------------------------------------------------------------------------

class AgentDecision(Base):
    """Audit record of the agent's decision for one opportunity."""
    __tablename__ = "agent_decisions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), ForeignKey("recovery_opportunities.id"), nullable=False)
    # What the agent considered
    candidate_actions_json: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of candidates + scores
    selected_action: Mapped[Optional[str]] = mapped_column(String(64))   # RecoveryStrategy value
    confidence: Mapped[Optional[float]] = mapped_column(Float)
    expected_recovery_value: Mapped[Optional[float]] = mapped_column(Float)
    # Guardrail outcome
    guardrail_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    guardrail_block_reason: Mapped[Optional[str]] = mapped_column(Text)
    # Approval
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_status: Mapped[Optional[str]] = mapped_column(String(32))
    approved_by: Mapped[Optional[str]] = mapped_column(String(128))
    # LLM diagnosis summary (no raw LLM output stored — only structured fields)
    diagnosis_summary: Mapped[Optional[str]] = mapped_column(Text)
    diagnosis_failure_category: Mapped[Optional[str]] = mapped_column(String(64))
    diagnosis_confidence: Mapped[Optional[str]] = mapped_column(String(32))
    # Rationale for audit
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    opportunity: Mapped["RecoveryOpportunity"] = relationship("RecoveryOpportunity", back_populates="decisions")

    __table_args__ = (
        Index("idx_decisions_opportunity_id", "opportunity_id"),
    )


# ---------------------------------------------------------------------------
# Recovery Action
# ---------------------------------------------------------------------------

class RecoveryAction(Base):
    """A concrete recovery intervention for one opportunity."""
    __tablename__ = "recovery_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(String(64), ForeignKey("recovery_opportunities.id"), nullable=False)
    decision_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("agent_decisions.id"))
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)   # RecoveryStrategy value
    status: Mapped[str] = mapped_column(String(32), default="pending")  # ActionStatus value
    # External execution reference (e.g. Razorpay payment link ID)
    external_reference_id: Mapped[Optional[str]] = mapped_column(String(128))
    external_reference_url: Mapped[Optional[str]] = mapped_column(Text)
    # Parameters used for execution (JSON)
    parameters_json: Mapped[Optional[str]] = mapped_column(Text)
    # Idempotency key
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    opportunity: Mapped["RecoveryOpportunity"] = relationship("RecoveryOpportunity", back_populates="actions")
    outcome: Mapped[Optional["RecoveryOutcome"]] = relationship("RecoveryOutcome", back_populates="action", uselist=False)

    __table_args__ = (
        Index("idx_actions_opportunity_id", "opportunity_id"),
    )


# ---------------------------------------------------------------------------
# Recovery Outcome
# ---------------------------------------------------------------------------

class RecoveryOutcome(Base):
    """Result of a recovery action — tied to webhook or payment state confirmation."""
    __tablename__ = "recovery_outcomes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_id: Mapped[str] = mapped_column(String(64), ForeignKey("recovery_actions.id"), unique=True, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recovered_amount: Mapped[Optional[int]] = mapped_column(BigInteger)  # paise; None if failed
    time_to_recovery_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    # Confirming webhook event
    confirming_event_id: Mapped[Optional[str]] = mapped_column(String(128))
    confirming_payment_id: Mapped[Optional[str]] = mapped_column(String(64))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    action: Mapped["RecoveryAction"] = relationship("RecoveryAction", back_populates="outcome")

    __table_args__ = (
        Index("idx_outcomes_action_id", "action_id"),
    )


# ---------------------------------------------------------------------------
# Audit Event
# ---------------------------------------------------------------------------

class AuditEvent(Base):
    """Immutable audit log for all material decisions and actions."""
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)   # "opportunity" | "decision" | "action"
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)   # e.g. "guardrail.blocked"
    detail: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_audit_entity_id", "entity_id"),
        Index("idx_audit_created_at", "created_at"),
    )
