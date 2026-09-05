"""
End-to-end integration tests verifying the complete RecoverAI lifecycle:
Dashboard → Opportunity → Diagnose/Decide → Guardrail → Approval → Execution → Webhook → Attribution → Analytics
"""
import json
import uuid
import hmac
import hashlib
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import get_settings, Settings
from app.db.models import (
    Merchant,
    Customer,
    Order,
    Payment,
    RecoveryOpportunity,
    OpportunityStatus,
)
from app.db.session import get_db_session

client = TestClient(app)


def compute_signature(payload: str, secret: str) -> str:
    """Computes valid Razorpay HMAC-SHA256 signature."""
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=payload.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


class TestEndToEndLifecycle:
    @pytest.fixture(autouse=True)
    def setup_e2e_environment(self):
        """Prepares an isolated test opportunity with card payment failure."""
        uid = uuid.uuid4().hex[:8]
        merchant_id = f"m_e2e_{uid}"
        customer_id = f"c_e2e_{uid}"
        order_id = f"order_e2e_{uid}"
        payment_id = f"pay_e2e_{uid}"
        opp_id = f"opp_e2e_{uid}"

        with get_db_session() as session:
            # Seed Merchant
            merchant = Merchant(id=merchant_id, name="E2E Demo Merchant")
            session.add(merchant)

            # Seed Customer
            customer = Customer(
                id=customer_id,
                merchant_id=merchant_id,
                email=f"shopper_{uid}@example.com",
                phone="+919876543210",
                opted_out=False,
            )
            session.add(customer)

            # Seed Order (high-value: ₹6000, which is 600000 paise > approval threshold ₹5000)
            order = Order(
                id=order_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                amount=600000,
                currency="INR",
            )
            session.add(order)

            # Seed Failed Payment (Pattern A: card authentication error, triggers payment_link)
            payment = Payment(
                id=payment_id,
                merchant_id=merchant_id,
                customer_id=customer_id,
                order_id=order_id,
                amount=600000,
                currency="INR",
                method="card",
                status="failed",
                error_code="BAD_REQUEST_ERROR",
                error_description="Card authentication failed at issuing bank",
                error_source="bank",
                error_step="payment_authentication",
                error_reason="incorrect_otp",
                attempt_number=1,
            )
            session.add(payment)

            # Seed Opportunity
            opp = RecoveryOpportunity(
                id=opp_id,
                payment_id=payment_id,
                merchant_id=merchant_id,
                status=OpportunityStatus.open.value,
                amount_at_risk=600000,
                detected_at=datetime.now(timezone.utc),
                dataset_split="train",
            )
            session.add(opp)

        return {
            "merchant_id": merchant_id,
            "customer_id": customer_id,
            "order_id": order_id,
            "payment_id": payment_id,
            "opportunity_id": opp_id,
            "amount_paise": 600000,
        }

    def test_complete_demo_lifecycle(self, setup_e2e_environment):
        data = setup_e2e_environment
        opp_id = data["opportunity_id"]
        payment_id = data["payment_id"]
        amount = data["amount_paise"]

        # -------------------------------------------------------------------
        # Step 1: Initial Analytics State
        # -------------------------------------------------------------------
        init_analytics = client.get("/analytics/recovery")
        assert init_analytics.status_code == 200
        init_data = init_analytics.json()
        assert "total_opportunities" in init_data

        # -------------------------------------------------------------------
        # Step 2: Query Opportunity Detail
        # -------------------------------------------------------------------
        opp_resp = client.get(f"/recovery/opportunities/{opp_id}")
        assert opp_resp.status_code == 200
        opp_data = opp_resp.json()
        assert opp_data["id"] == opp_id
        assert opp_data["status"] == "open"
        assert opp_data["amount_at_risk"] == amount

        # -------------------------------------------------------------------
        # Step 3: Run AI Decision Pipeline (Diagnose → Decide → Guardrail)
        # -------------------------------------------------------------------
        decide_resp = client.post(f"/recovery/opportunities/{opp_id}/decide")
        assert decide_resp.status_code == 200
        decision = decide_resp.json()
        assert decision["opportunity_id"] == opp_id
        assert decision["selected_action"] in ("payment_link", "delayed_retry", "reminder")
        # Amount ₹2,500 exceeds default ₹1,000 threshold, so approval must be required
        assert decision["requires_approval"] is True
        assert decision["execution_status"] == "pending"
        act_id = decision.get("action_id")
        assert act_id is not None

        # -------------------------------------------------------------------
        # Step 4: Guardrail Enforcement — Cannot Execute Before Approval
        # -------------------------------------------------------------------
        premature_exec = client.post(f"/recovery/actions/{act_id}/execute")
        assert premature_exec.status_code == 400
        assert "pending approval" in premature_exec.json()["detail"]

        # -------------------------------------------------------------------
        # Step 5: Merchant Action Approval
        # -------------------------------------------------------------------
        approve_resp = client.post(
            f"/recovery/actions/{act_id}/approve",
            json={"approved_by": "lead_merchant_admin", "notes": "Approved for demo recovery link"},
        )
        assert approve_resp.status_code == 200
        approved_data = approve_resp.json()
        assert approved_data["status"] == "approved"

        # -------------------------------------------------------------------
        # Step 6: Execute Approved Action in Test Mode
        # -------------------------------------------------------------------
        exec_resp = client.post(f"/recovery/actions/{act_id}/execute")
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["status"] == "completed"
        assert exec_data["external_reference_id"] is not None
        external_ref = exec_data["external_reference_id"]

        # Verify idempotency: repeated execution returns identical result
        exec_dup = client.post(f"/recovery/actions/{act_id}/execute")
        assert exec_dup.status_code == 200
        assert exec_dup.json()["external_reference_id"] == external_ref

        # Verify opportunity status is now in_progress
        updated_opp = client.get(f"/recovery/opportunities/{opp_id}").json()
        assert updated_opp["status"] in ("in_progress", "open")

        # -------------------------------------------------------------------
        # Step 7: Webhook Ingestion & Attribution (payment_link.paid)
        # -------------------------------------------------------------------
        settings = get_settings()
        secret = settings.RAZORPAY_WEBHOOK_SECRET or "local_synthetic_test_secret_p0_05"
        test_settings = Settings(RAZORPAY_WEBHOOK_SECRET=secret)
        app.dependency_overrides[get_settings] = lambda: test_settings

        evt_id = f"evt_test_paid_{uuid.uuid4().hex[:8]}"
        webhook_payload = {
            "entity": "event",
            "account_id": "acc_test_demo",
            "event": "payment_link.paid",
            "contains": ["payment_link", "payment"],
            "payload": {
                "payment_link": {
                    "entity": {
                        "id": external_ref,
                        "amount": amount,
                        "currency": "INR",
                        "status": "paid",
                        "order_id": data["order_id"],
                    }
                },
                "payment": {
                    "entity": {
                        "id": f"pay_confirm_{uuid.uuid4().hex[:8]}",
                        "amount": amount,
                        "currency": "INR",
                        "status": "captured",
                        "order_id": data["order_id"],
                    }
                }
            },
            "created_at": int(datetime.now(timezone.utc).timestamp()),
        }
        raw_body = json.dumps(webhook_payload)
        sig = compute_signature(raw_body, secret)

        try:
            webhook_resp = client.post(
                "/webhooks/razorpay",
                content=raw_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": sig,
                    "x-razorpay-event-id": evt_id,
                },
            )
            assert webhook_resp.status_code == 200
            webhook_data = webhook_resp.json()
            assert webhook_data["status"] == "received"
            assert webhook_data.get("attributed") is True

            # -------------------------------------------------------------------
            # Step 8: Outcome Attribution Verification
            # -------------------------------------------------------------------
            final_opp = client.get(f"/recovery/opportunities/{opp_id}").json()
            assert final_opp["status"] == "recovered"
            assert final_opp["recovered_amount"] == amount

            # Verify Action is completed
            final_act = client.get(f"/recovery/actions/{act_id}").json()
            assert final_act["status"] == "completed"

            # Verify duplicate webhook re-delivery is idempotent
            dup_webhook_resp = client.post(
                "/webhooks/razorpay",
                content=raw_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Razorpay-Signature": sig,
                    "x-razorpay-event-id": evt_id,
                },
            )
            assert dup_webhook_resp.status_code == 200
            assert dup_webhook_resp.json()["status"] == "duplicate"

            # -------------------------------------------------------------------
            # Step 9: Analytics Attribution Verification
            # -------------------------------------------------------------------
            final_analytics = client.get("/analytics/recovery")
            assert final_analytics.status_code == 200
            final_data = final_analytics.json()
            assert final_data["recovered_opportunities"] >= 1
            assert final_data["total_recovered_gmv_inr"] >= (amount / 100.0)
        finally:
            app.dependency_overrides.clear()

    def test_auto_approved_low_value_flow(self):
        """Verify that opportunities under approval ceiling auto-execute immediately."""
        uid = uuid.uuid4().hex[:8]
        merchant_id = f"m_auto_{uid}"
        customer_id = f"c_auto_{uid}"
        order_id = f"order_auto_{uid}"
        payment_id = f"pay_auto_{uid}"
        opp_id = f"opp_auto_{uid}"
        low_amount = 150000  # ₹1,500 (under ₹5,000 ceiling)

        with get_db_session() as session:
            session.add(Merchant(id=merchant_id, name="Auto Merchant"))
            session.add(Customer(id=customer_id, merchant_id=merchant_id, email=f"c_{uid}@ex.com"))
            session.add(Order(id=order_id, merchant_id=merchant_id, customer_id=customer_id, amount=low_amount))
            session.add(
                Payment(
                    id=payment_id,
                    merchant_id=merchant_id,
                    customer_id=customer_id,
                    order_id=order_id,
                    amount=low_amount,
                    currency="INR",
                    method="upi",
                    status="failed",
                    error_code="BAD_REQUEST_ERROR",
                    error_source="network",
                    error_step="payment_authorization",
                    error_reason="gateway_timeout",
                    attempt_number=1,
                )
            )
            session.add(
                RecoveryOpportunity(
                    id=opp_id,
                    payment_id=payment_id,
                    merchant_id=merchant_id,
                    status=OpportunityStatus.open.value,
                    amount_at_risk=low_amount,
                    detected_at=datetime.now(timezone.utc),
                    dataset_split="train",
                )
            )

        # Trigger decision
        res = client.post(f"/recovery/opportunities/{opp_id}/decide")
        assert res.status_code == 200
        d = res.json()
        assert d["requires_approval"] is False
        assert d["execution_status"] in ("approved", "completed", "executed")
        assert d.get("action_id") is not None

        # Verify action was auto-dispatched
        act = client.get(f"/recovery/actions/{d['action_id']}").json()
        assert act["status"] == "completed"
        assert act["external_reference_id"] is not None
