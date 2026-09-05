"""
Unit tests for Webhook → Recovery Outcome Attribution.
"""
import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import (
    Base,
    Merchant,
    Customer,
    Order,
    Payment,
    RecoveryOpportunity,
    RecoveryAction,
    RecoveryOutcome,
    AuditEvent,
    ActionStatus,
    OpportunityStatus,
)
from app.agent.attribution import attribute_webhook_event


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def attribution_test_data(db_session):
    uid = uuid.uuid4().hex[:8]
    m = Merchant(id=f"m_{uid}", name="Attribution Merchant")
    c = Customer(id=f"c_{uid}", merchant_id=f"m_{uid}")
    o = Order(id=f"order_{uid}", merchant_id=f"m_{uid}", customer_id=f"c_{uid}", amount=10000)
    p = Payment(
        id=f"pay_{uid}",
        merchant_id=f"m_{uid}",
        customer_id=f"c_{uid}",
        order_id=f"order_{uid}",
        amount=10000,
        status="failed",
    )
    opp = RecoveryOpportunity(
        id=f"opp_{uid}",
        payment_id=f"pay_{uid}",
        merchant_id=f"m_{uid}",
        status=OpportunityStatus.open.value,
        amount_at_risk=10000,
        detected_at=datetime.now(timezone.utc),
    )
    plink_ref = f"plink_{uid}_test"
    act = RecoveryAction(
        id=f"act_{uid}",
        opportunity_id=f"opp_{uid}",
        strategy="payment_link",
        status=ActionStatus.completed.value,
        external_reference_id=plink_ref,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([m, c, o, p, opp, act])
    db_session.commit()

    return {
        "opportunity_id": f"opp_{uid}",
        "action_id": f"act_{uid}",
        "payment_link_id": plink_ref,
        "payment_id": f"pay_{uid}",
        "order_id": f"order_{uid}",
        "amount": 10000,
    }


class TestAttribution:
    def test_attribute_payment_link_paid(self, db_session, attribution_test_data):
        data = attribution_test_data
        res = attribute_webhook_event(
            event_id="evt_paid_001",
            event_type="payment_link.paid",
            payment_id="pay_new_001",
            payment_link_id=data["payment_link_id"],
            order_id=None,
            amount=data["amount"],
            session=db_session,
        )
        assert res["attributed"] is True
        assert res["action_id"] == data["action_id"]
        assert res["recovered_amount"] == 10000

        # Verify DB outcome
        outcome = db_session.query(RecoveryOutcome).filter_by(action_id=data["action_id"]).first()
        assert outcome is not None
        assert outcome.success is True
        assert outcome.recovered_amount == 10000

        # Verify Opportunity updated
        opp = db_session.get(RecoveryOpportunity, data["opportunity_id"])
        assert opp.status == OpportunityStatus.recovered.value
        assert opp.recovered_amount == 10000

        # Verify AuditEvent
        audit = db_session.query(AuditEvent).filter_by(entity_id=data["opportunity_id"]).first()
        assert audit is not None
        assert audit.event_type == "recovery.attributed"

    def test_duplicate_attribution_is_idempotent(self, db_session, attribution_test_data):
        data = attribution_test_data
        res1 = attribute_webhook_event(
            event_id="evt_paid_002",
            event_type="payment_link.paid",
            payment_id="pay_new_002",
            payment_link_id=data["payment_link_id"],
            order_id=None,
            amount=data["amount"],
            session=db_session,
        )
        assert res1["attributed"] is True
        assert res1.get("duplicate") is not True

        # Second event for same action
        res2 = attribute_webhook_event(
            event_id="evt_paid_002_dup",
            event_type="payment_link.paid",
            payment_id="pay_new_002",
            payment_link_id=data["payment_link_id"],
            order_id=None,
            amount=data["amount"],
            session=db_session,
        )
        assert res2["attributed"] is True
        assert res2["duplicate"] is True

    def test_attribute_payment_captured_by_order_id(self, db_session, attribution_test_data):
        data = attribution_test_data
        res = attribute_webhook_event(
            event_id="evt_cap_001",
            event_type="payment.captured",
            payment_id="pay_captured_subsequent",
            payment_link_id=None,
            order_id=data["order_id"],
            amount=data["amount"],
            session=db_session,
        )
        assert res["attributed"] is True
        assert res["action_id"] == data["action_id"]

    def test_non_recovery_event_rejected(self, db_session, attribution_test_data):
        res = attribute_webhook_event(
            event_id="evt_fail_001",
            event_type="payment.failed",
            payment_id="p_fail",
            payment_link_id=None,
            order_id=None,
            amount=10000,
            session=db_session,
        )
        assert res["attributed"] is False
        assert "not a recovery-confirming event" in res["reason"]

    def test_unmatched_event_returns_false(self, db_session):
        res = attribute_webhook_event(
            event_id="evt_unmatched",
            event_type="payment_link.paid",
            payment_id="p_unmatched",
            payment_link_id="plink_unknown_99999",
            order_id="order_unknown_99999",
            amount=10000,
            session=db_session,
        )
        assert res["attributed"] is False
        assert "No matching recovery action" in res["reason"]
