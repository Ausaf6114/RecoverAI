"""
State representation for RecoverAI Agent lifecycle.

Tracks state transitions across the 8-stage orchestration lifecycle:
Detect → Diagnose → Decide → Guardrail → Execute → Measure → Learn → Replan
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.domain.models import PaymentContext, RecoveryCandidate
from app.agent.diagnosis import DiagnosisResult
from app.agent.decision_engine import DecisionResult


class AgentStage:
    DETECTED = "DETECTED"
    DIAGNOSED = "DIAGNOSED"
    DECIDED = "DECIDED"
    GUARDRAILED = "GUARDRAILED"
    EXECUTED = "EXECUTED"
    MEASURED = "MEASURED"
    LEARNED = "LEARNED"
    REPLANNED = "REPLANNED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


@dataclass
class AgentState:
    """Immutable/mutable state packet carrying all context and decisions through the pipeline."""
    payment_id: str
    opportunity_id: Optional[str] = None
    stage: str = AgentStage.DETECTED
    
    context: Optional[PaymentContext] = None
    diagnosis: Optional[DiagnosisResult] = None
    decision: Optional[DecisionResult] = None
    
    # Execution & Action tracking
    action_id: Optional[str] = None
    execution_status: Optional[str] = None  # "pending" | "approved" | "completed" | "blocked"
    external_reference_id: Optional[str] = None
    
    # Measurement & Outcome tracking
    recovered: Optional[bool] = None
    recovered_amount: Optional[int] = None
    time_to_recovery_seconds: Optional[int] = None
    
    # Replanning
    replan_count: int = 0
    max_replans: int = 2
    
    # Audit log
    audit_trail: List[Dict[str, Any]] = field(default_factory=list)

    def log_event(self, event_type: str, detail: Optional[str] = None) -> None:
        """Appends an immutable timestamped event to the audit trail."""
        self.audit_trail.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": self.stage,
            "event_type": event_type,
            "detail": detail,
        })

    def transition(self, new_stage: str, detail: Optional[str] = None) -> None:
        """Transitions to a new lifecycle stage and logs the transition."""
        self.stage = new_stage
        self.log_event(f"transition.{new_stage.lower()}", detail)
