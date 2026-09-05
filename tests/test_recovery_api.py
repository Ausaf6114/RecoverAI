"""
Integration tests for RecoverAI Recovery Opportunities and Actions API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.db.session import get_db_session
from app.db.models import (
    Merchant,
    Customer,
    Order,
    Payment,
    RecoveryOpportunity,
    RecoveryAction,
    ActionStatus,
    OpportunityStatus,
)

client = TestClient(app)


import uuid


@pytest.fixture
def setup_api_data():
    """Seeds fresh, isolated test records with unique IDs for each test."""
    uid = uuid.uuid4().hex[:8]
    merch_id = f"m_api_{uid}"
    cust_id = f"c_api_{uid}"
    order_id = f"o_api_{uid}"
    pay_id = f"p_api_{uid}"
    opp_id = f"opp_api_{uid}"
    act_id = f"act_api_{uid}"

    with get_db_session() as session:
        m = Merchant(id=merch_id, name=f"API Test Merchant {uid}")
        c = Customer(id=cust_id, merchant_id=merch_id, successful_methods="upi", total_payments=1, successful_payments=1)
        o = Order(id=order_id, merchant_id=merch_id, customer_id=cust_id, amount=200000)
        p = Payment(
            id=pay_id,
            merchant_id=merch_id,
            customer_id=cust_id,
            order_id=order_id,
            amount=200000,
            status="failed",
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            error_reason="incorrect_otp",
            attempt_number=1,
        )
        opp = RecoveryOpportunity(
            id=opp_id,
            payment_id=pay_id,
            merchant_id=merch_id,
            status=OpportunityStatus.open.value,
            amount_at_risk=200000,
            detected_at=datetime.now(timezone.utc),
        )
        act = RecoveryAction(
            id=act_id,
            opportunity_id=opp_id,
            strategy="payment_link",
            status=ActionStatus.pending.value,
            created_at=datetime.now(timezone.utc),
        )
        session.add_all([m, c, o, p, opp, act])
        session.flush()

    return opp_id, act_id


class TestOpportunitiesAPI:
    def test_list_opportunities(self, setup_api_data):
        response = client.get("/recovery/opportunities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "id" in data[0]
        assert "amount_at_risk" in data[0]

    def test_list_opportunities_with_filter(self, setup_api_data):
        response = client.get("/recovery/opportunities?status=open")
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert item["status"] == "open"

    def test_get_opportunity_by_id(self, setup_api_data):
        opp_id, _ = setup_api_data
        response = client.get(f"/recovery/opportunities/{opp_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == opp_id
        assert data["payment_id"].startswith("p_api_")
        assert data["amount_at_risk"] == 200000
        assert data["error_reason"] == "incorrect_otp"

    def test_get_opportunity_404(self):
        response = client.get("/recovery/opportunities/opp_non_existent")
        assert response.status_code == 404

    def test_decide_opportunity(self, setup_api_data):
        opp_id, _ = setup_api_data
        response = client.post(f"/recovery/opportunities/{opp_id}/decide")
        assert response.status_code == 200
        data = response.json()
        assert data["opportunity_id"] == opp_id
        assert data["selected_action"] == "payment_link"
        assert data["confidence"] > 0
        assert data["expected_recovery_value"] > 0
        assert data["diagnosis_category"] is not None


class TestActionsAPI:
    def test_get_action(self, setup_api_data):
        _, act_id = setup_api_data
        response = client.get(f"/recovery/actions/{act_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == act_id
        assert data["strategy"] == "payment_link"

    def test_get_action_404(self):
        response = client.get("/recovery/actions/act_non_existent")
        assert response.status_code == 404

    def test_list_actions(self, setup_api_data):
        opp_id, act_id = setup_api_data
        resp = client.get("/recovery/actions")
        assert resp.status_code == 200
        actions = resp.json()
        assert len(actions) >= 1
        assert any(a["id"] == act_id for a in actions)

        # Filter by status
        resp_pending = client.get("/recovery/actions?status=pending")
        assert resp_pending.status_code == 200
        pending_actions = resp_pending.json()
        assert all(a["status"] == "pending" for a in pending_actions)

    def test_cannot_execute_before_approval(self, setup_api_data):
        """Approval-gated action cannot execute before approval."""
        _, act_id = setup_api_data
        # Attempt to execute while still pending approval
        bad_exec = client.post(f"/recovery/actions/{act_id}/execute")
        assert bad_exec.status_code == 400
        assert "pending approval" in bad_exec.json()["detail"]

    def test_approve_and_execute_action_lifecycle(self, setup_api_data):
        _, act_id = setup_api_data

        # 1. Approve
        approve_resp = client.post(f"/recovery/actions/{act_id}/approve", json={"approved_by": "risk_lead"})
        assert approve_resp.status_code == 200
        appr_data = approve_resp.json()
        assert appr_data["status"] == ActionStatus.approved.value

        # 2. Re-approving non-pending action returns 400
        bad_approve = client.post(f"/recovery/actions/{act_id}/approve")
        assert bad_approve.status_code == 400

        # 3. Execute
        exec_resp = client.post(f"/recovery/actions/{act_id}/execute")
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["status"] == ActionStatus.completed.value
        assert exec_data["external_reference_id"] is not None

        # 4. Repeated execution is idempotent
        exec_resp_dup = client.post(f"/recovery/actions/{act_id}/execute")
        assert exec_resp_dup.status_code == 200
        dup_data = exec_resp_dup.json()
        assert dup_data["external_reference_id"] == exec_data["external_reference_id"]
        assert dup_data["status"] == ActionStatus.completed.value
