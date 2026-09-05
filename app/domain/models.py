"""
Pure Python domain dataclasses for RecoverAI.

These models decouple domain logic and decision-making from database ORM and external APIs.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class MerchantPolicy:
    """Merchant-defined guardrails and policy configuration."""
    max_recovery_attempts: int = 3
    max_customer_contacts: int = 2
    min_confidence_threshold: float = 0.65
    auto_execute_below_amount: int = 50000     # in paise (₹500)
    requires_approval_above: int = 500000      # in paise (₹5,000)
    max_incentive_discount_pct: float = 0.0


@dataclass
class PaymentContext:
    """
    Rich contextual snapshot of a payment failure and its surrounding history.
    Passed to diagnostic rules, ML scoring, and baseline policies.
    """
    payment_id: str
    customer_id: str
    merchant_id: str
    amount: int  # in paise
    currency: str = "INR"
    method: Optional[str] = None
    status: str = "failed"
    
    # Error classification
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    error_reason: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    attempt_number: int = 1
    
    # Customer context
    customer_opted_out: bool = False
    customer_total_payments: int = 0
    customer_successful_payments: int = 0
    customer_failed_payments: int = 0
    customer_successful_methods: List[str] = field(default_factory=list)
    customer_aov: Optional[float] = None
    
    # Order context
    order_id: Optional[str] = None
    order_category: Optional[str] = None
    
    # Opportunity & Contact tracking
    prior_contact_count: int = 0
    has_open_opportunity: bool = False
    created_at: Optional[datetime] = None
    dataset_split: str = "train"


@dataclass
class RecoveryCandidate:
    """
    A candidate recovery action scored by the policy or model.
    """
    strategy: str  # "payment_link", "delayed_retry", "reminder", "no_action", "human_review"
    predicted_recovery_probability: float
    expected_recovery_value: float  # paise
    estimated_cost: float = 0.0      # paise
    is_eligible: bool = True
    ineligibility_reason: Optional[str] = None


@dataclass
class GuardrailResult:
    """Result of policy/guardrail evaluation."""
    passed: bool
    reason: Optional[str] = None
    rule_name: Optional[str] = None
