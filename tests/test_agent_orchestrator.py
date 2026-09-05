"""
Unit tests for RecoverAI Agent: Context Builder, Gemini Diagnosis, State, and Orchestrator.
"""
import pytest
from unittest.mock import patch, MagicMock
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
    ActionStatus,
)
from app.domain.models import PaymentContext, MerchantPolicy
from app.agent.context_builder import build_payment_context_from_db, build_payment_context_from_dict
from app.agent.diagnosis import GeminiDiagnostician, DiagnosisResult
from app.agent.state import AgentState, AgentStage
from app.agent.orchestrator import RecoverAIOrchestrator


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
def sample_db_setup(db_session):
    merchant = Merchant(id="m_orch", name="Orchestrator Merchant")
    customer = Customer(id="c_orch", merchant_id="m_orch", successful_methods="upi,card", total_payments=3, successful_payments=2)
    order = Order(id="o_orch", merchant_id="m_orch", customer_id="c_orch", amount=180000)
    payment = Payment(
        id="p_orch_fail",
        merchant_id="m_orch",
        customer_id="c_orch",
        order_id="o_orch",
        amount=180000,
        status="failed",
        method="card",
        error_source="bank",
        error_step="payment_authentication",
        error_reason="incorrect_otp",
        attempt_number=1,
    )
    db_session.add_all([merchant, customer, order, payment])
    db_session.commit()
    return payment.id


class TestContextBuilder:
    def test_build_from_db(self, db_session, sample_db_setup):
        ctx = build_payment_context_from_db(sample_db_setup, db_session)
        assert ctx is not None
        assert ctx.payment_id == sample_db_setup
        assert ctx.amount == 180000
        assert "upi" in ctx.customer_successful_methods
        assert ctx.customer_opted_out is False

    def test_build_from_dict(self):
        data = {
            "payment_id": "pay_mock",
            "amount": 50000,
            "status": "failed",
            "customer_successful_methods": ["upi", "card"],
        }
        ctx = build_payment_context_from_dict(data)
        assert ctx.payment_id == "pay_mock"
        assert ctx.amount == 50000
        assert ctx.customer_successful_methods == ["upi", "card"]


class TestGeminiDiagnosis:
    def test_deterministic_fallback_pattern_a(self):
        diagnostician = GeminiDiagnostician(api_key=None)
        ctx = PaymentContext(
            payment_id="p1",
            customer_id="c1",
            merchant_id="m1",
            amount=100000,
            method="card",
            error_source="bank",
            error_step="payment_authentication",
            customer_successful_methods=["upi"],
        )
        res = diagnostician.diagnose(ctx)
        assert res.failure_category == "authentication_failure"
        assert res.confidence == "high"
        assert res.recommended_strategy_hint == "payment_link"
        assert res.provider == "deterministic_fallback"

    def test_deterministic_fallback_pattern_b(self):
        diagnostician = GeminiDiagnostician(api_key=None)
        ctx = PaymentContext(
            payment_id="p2",
            customer_id="c2",
            merchant_id="m1",
            amount=100000,
            error_source="network",
            error_reason="gateway_timeout",
        )
        res = diagnostician.diagnose(ctx)
        assert res.failure_category == "network_timeout"
        assert res.recommended_strategy_hint == "delayed_retry"

    @patch("httpx.Client.post")
    def test_mock_gemini_api_call(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '{"failure_category": "authentication_failure", "hypothesis": "OTP entry timed out", "confidence": "high", "key_signals": ["otp_expired"], "recommended_strategy_hint": "payment_link"}'
                    }]
                }
            }]
        }
        mock_post.return_value = mock_response

        diagnostician = GeminiDiagnostician(api_key="mock_key")
        ctx = PaymentContext(
            payment_id="p_gem",
            customer_id="c_gem",
            merchant_id="m_gem",
            amount=100000,
        )
        res = diagnostician.diagnose(ctx)
        assert res.failure_category == "authentication_failure"
        assert res.hypothesis == "OTP entry timed out"
        assert res.provider == "gemini"

    def test_injected_gemini_http_client_is_used(self, fake_gemini_http_client):
        diagnostician = GeminiDiagnostician(api_key="mock_key", http_client=fake_gemini_http_client)
        ctx = PaymentContext(
            payment_id="p_gem_inj",
            customer_id="c_gem_inj",
            merchant_id="m_gem_inj",
            amount=100000,
        )
        res = diagnostician.diagnose(ctx)
        assert res.failure_category == "authentication_failure"
        assert "injected client mock" in res.hypothesis
        assert res.provider == "gemini"
        fake_gemini_http_client.post.assert_called_once()


class TestAgentState:
    def test_state_lifecycle_transitions(self):
        state = AgentState(payment_id="pay_test_001")
        assert state.stage == AgentStage.DETECTED

        state.transition(AgentStage.DIAGNOSED, "Diagnosis complete")
        assert state.stage == AgentStage.DIAGNOSED
        assert len(state.audit_trail) == 1
        assert state.audit_trail[0]["event_type"] == "transition.diagnosed"


class TestOrchestratorPipeline:
    def test_full_pipeline_pattern_a(self, db_session, sample_db_setup):
        orchestrator = RecoverAIOrchestrator()
        state = orchestrator.run_pipeline(sample_db_setup, session=db_session)

        assert state.stage == AgentStage.LEARNED
        assert state.decision is not None
        assert state.decision.selected_action == "payment_link"
        assert state.action_id is not None
        assert state.execution_status == "approved"

        # Verify DB records created
        opp = db_session.query(RecoveryOpportunity).filter_by(payment_id=sample_db_setup).first()
        assert opp is not None

        action = db_session.query(RecoveryAction).filter_by(opportunity_id=opp.id).first()
        assert action is not None
        assert action.strategy == "payment_link"

    def test_non_failed_payment_skips_pipeline(self, db_session):
        # Create captured payment
        m = Merchant(id="m_cap", name="Merchant Cap")
        c = Customer(id="c_cap", merchant_id="m_cap")
        p = Payment(id="p_cap", merchant_id="m_cap", customer_id="c_cap", amount=10000, status="captured")
        db_session.add_all([m, c, p])
        db_session.commit()

        orchestrator = RecoverAIOrchestrator()
        state = orchestrator.run_pipeline("p_cap", session=db_session)
        assert state.stage == AgentStage.COMPLETED
        assert state.decision is None

    def test_high_amount_triggers_manual_approval_state(self, db_session):
        # Amount = ₹10,000 (exceeds default approval threshold of ₹5,000)
        m = Merchant(id="m_hi", name="Merchant Hi")
        c = Customer(id="c_hi", merchant_id="m_hi", successful_methods="upi")
        p = Payment(
            id="p_hi",
            merchant_id="m_hi",
            customer_id="c_hi",
            amount=1000000,  # ₹10,000 in paise
            status="failed",
            method="card",
            error_source="bank",
            error_step="payment_authentication",
        )
        db_session.add_all([m, c, p])
        db_session.commit()

        policy = MerchantPolicy(requires_approval_above=500000)
        orchestrator = RecoverAIOrchestrator()
        state = orchestrator.run_pipeline("p_hi", policy=policy, session=db_session)

        assert state.decision.requires_approval is True
        assert state.execution_status == "pending"

        action = db_session.query(RecoveryAction).filter_by(id=state.action_id).first()
        assert action.status == ActionStatus.pending.value

    def test_replan_workflow(self):
        orchestrator = RecoverAIOrchestrator()
        ctx = PaymentContext(
            payment_id="p_rep",
            customer_id="c_rep",
            merchant_id="m_rep",
            amount=100000,
            status="failed",
            customer_successful_methods=["upi"],
        )
        state = orchestrator.run_pipeline("p_rep", context=ctx)
        orig_action = state.decision.selected_action

        # Replan
        success = orchestrator.replan(state, reason="first_choice_timed_out")
        assert success is True
        assert state.stage == AgentStage.REPLANNED
        assert state.replan_count == 1
