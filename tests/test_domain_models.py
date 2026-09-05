"""
Tests for RecoverAI domain models (SQLAlchemy ORM and pure Python dataclasses).
"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import (
    Base,
    Merchant,
    Customer,
    Order,
    Payment,
    RecoveryOpportunity,
    AgentDecision,
    RecoveryAction,
    RecoveryOutcome,
    AuditEvent,
    PaymentMethod,
    PaymentStatus,
    RecoveryStrategy,
    ActionStatus,
    OpportunityStatus,
)
from app.domain.models import (
    PaymentContext,
    RecoveryCandidate,
    MerchantPolicy,
    GuardrailResult,
)


@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session for ORM testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


class TestPureDomainModels:
    def test_payment_context_instantiation(self):
        ctx = PaymentContext(
            payment_id="pay_001",
            customer_id="cust_001",
            merchant_id="merch_001",
            amount=150000,
            currency="INR",
            method="card",
            status="failed",
            error_source="bank",
            error_step="payment_authentication",
            error_reason="incorrect_otp",
            attempt_number=1,
            customer_successful_methods=["upi"],
        )
        assert ctx.payment_id == "pay_001"
        assert ctx.amount == 150000
        assert ctx.customer_successful_methods == ["upi"]
        assert ctx.customer_opted_out is False

    def test_recovery_candidate_instantiation(self):
        candidate = RecoveryCandidate(
            strategy="payment_link",
            predicted_recovery_probability=0.75,
            expected_recovery_value=112500.0,
            estimated_cost=0.0,
            is_eligible=True,
        )
        assert candidate.strategy == "payment_link"
        assert candidate.predicted_recovery_probability == 0.75
        assert candidate.is_eligible is True

    def test_merchant_policy_defaults(self):
        policy = MerchantPolicy()
        assert policy.max_recovery_attempts == 3
        assert policy.max_customer_contacts == 2
        assert policy.min_confidence_threshold == 0.65
        assert policy.auto_execute_below_amount == 50000

    def test_guardrail_result(self):
        passed = GuardrailResult(passed=True)
        assert passed.passed is True
        assert passed.reason is None

        blocked = GuardrailResult(passed=False, reason="max_contacts_exceeded", rule_name="contact_cap")
        assert blocked.passed is False
        assert blocked.rule_name == "contact_cap"


class TestSQLAlchemyDomainORM:
    def test_merchant_and_customer_creation(self, db_session: Session):
        merchant = Merchant(
            id="m_001",
            name="Test Store",
            max_recovery_attempts=3,
        )
        db_session.add(merchant)
        db_session.flush()

        customer = Customer(
            id="c_001",
            merchant_id="m_001",
            email="cust@example.com",
            phone="+919800000001",
            successful_methods="upi,card",
        )
        db_session.add(customer)
        db_session.commit()

        retrieved_merchant = db_session.get(Merchant, "m_001")
        assert retrieved_merchant is not None
        assert len(retrieved_merchant.customers) == 1
        assert retrieved_merchant.customers[0].email == "cust@example.com"

    def test_end_to_end_recovery_lifecycle(self, db_session: Session):
        # 1. Merchant + Customer + Order
        now = datetime.now(timezone.utc)
        merchant = Merchant(id="m_abc", name="ABC Retail")
        customer = Customer(id="c_abc", merchant_id="m_abc")
        order = Order(id="o_abc", merchant_id="m_abc", customer_id="c_abc", amount=250000)
        db_session.add_all([merchant, customer, order])
        db_session.flush()

        # 2. Failed Payment
        payment = Payment(
            id="p_abc",
            order_id="o_abc",
            customer_id="c_abc",
            merchant_id="m_abc",
            amount=250000,
            method=PaymentMethod.card.value,
            status=PaymentStatus.failed.value,
            error_source="bank",
            error_step="payment_authentication",
            error_reason="incorrect_otp",
            attempt_number=1,
        )
        db_session.add(payment)
        db_session.flush()

        # 3. Recovery Opportunity
        opp = RecoveryOpportunity(
            id="opp_abc",
            payment_id="p_abc",
            merchant_id="m_abc",
            status=OpportunityStatus.open.value,
            amount_at_risk=250000,
            detected_at=now,
        )
        db_session.add(opp)
        db_session.flush()

        # 4. Agent Decision
        decision = AgentDecision(
            id="dec_abc",
            opportunity_id="opp_abc",
            selected_action=RecoveryStrategy.payment_link.value,
            confidence=0.82,
            expected_recovery_value=205000.0,
            guardrail_passed=True,
            rationale="Card auth failure with customer UPI history",
        )
        db_session.add(decision)
        db_session.flush()

        # 5. Recovery Action
        action = RecoveryAction(
            id="act_abc",
            opportunity_id="opp_abc",
            decision_id="dec_abc",
            strategy=RecoveryStrategy.payment_link.value,
            status=ActionStatus.completed.value,
            external_reference_id="plink_test123",
            idempotency_key="idemp_abc_001",
        )
        db_session.add(action)
        db_session.flush()

        # 6. Recovery Outcome
        outcome = RecoveryOutcome(
            id="out_abc",
            action_id="act_abc",
            success=True,
            recovered_amount=250000,
            confirming_payment_id="pay_recovered_999",
            time_to_recovery_seconds=120,
        )
        db_session.add(outcome)

        # 7. Audit Event
        audit = AuditEvent(
            id="aud_abc",
            entity_type="opportunity",
            entity_id="opp_abc",
            event_type="recovery.succeeded",
            detail="Payment recovered via Payment Link plink_test123",
        )
        db_session.add(audit)
        db_session.commit()

        # Verify all links
        retrieved_opp = db_session.get(RecoveryOpportunity, "opp_abc")
        assert retrieved_opp is not None
        assert retrieved_opp.payment.amount == 250000
        assert len(retrieved_opp.decisions) == 1
        assert retrieved_opp.decisions[0].selected_action == "payment_link"
        assert len(retrieved_opp.actions) == 1
        assert retrieved_opp.actions[0].outcome.success is True
        assert retrieved_opp.actions[0].outcome.recovered_amount == 250000

        retrieved_audit = db_session.get(AuditEvent, "aud_abc")
        assert retrieved_audit is not None
        assert retrieved_audit.event_type == "recovery.succeeded"
