"""
Razorpay Action Adapter with idempotency, safety guardrails, and audit logging.

Enforces Test Mode safety:
- Only keys starting with 'rzp_test_' are permitted.
- Rejects any live keys or unverified execution.
- Safe simulation fallback when credentials are unconfigured or in offline test mode.
"""
import uuid
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import httpx

from app.core.config import get_settings
from app.domain.models import PaymentContext

logger = logging.getLogger(__name__)


class RazorpaySecurityError(Exception):
    """Raised when an unsafe or live Razorpay key operation is attempted."""
    pass


@dataclass
class ExecutionResult:
    """Standardized response from Razorpay action dispatch."""
    strategy: str
    status: str                         # "completed" | "pending" | "failed"
    reference_id: Optional[str] = None  # e.g. plink_test_xxx
    reference_url: Optional[str] = None # e.g. https://rzp.io/i/xxx
    raw_response: Optional[Dict[str, Any]] = None
    is_simulated: bool = False
    error_message: Optional[str] = None


_UNSET = object()
_default_razorpay_client: Optional[httpx.Client] = None


def set_default_razorpay_client(client: Optional[httpx.Client]) -> None:
    """Sets a global default HTTP client for Razorpay adapters (used for mocking/testing)."""
    global _default_razorpay_client
    _default_razorpay_client = client


def get_default_razorpay_client() -> Optional[httpx.Client]:
    """Returns the current default HTTP client for Razorpay adapters."""
    return _default_razorpay_client


class RazorpayActionAdapter:
    """
    Adapter for dispatching approved recovery interventions to Razorpay APIs
    with strict idempotency and Test Mode isolation.
    """

    def __init__(
        self,
        key_id: Any = _UNSET,
        key_secret: Any = _UNSET,
        base_url: str = "https://api.razorpay.com/v1",
        http_client: Optional[httpx.Client] = None,
    ):
        settings = get_settings()
        self.key_id = settings.RAZORPAY_KEY_ID if key_id is _UNSET else key_id
        self.key_secret = settings.RAZORPAY_KEY_SECRET if key_secret is _UNSET else key_secret
        self.base_url = base_url
        self.http_client = http_client if http_client is not None else get_default_razorpay_client()

        # Validate Test Mode safety
        self._validate_test_mode_safety()

    def _validate_test_mode_safety(self) -> None:
        """Ensures credentials belong strictly to Razorpay Test Mode."""
        if self.key_id:
            if not self.key_id.startswith("rzp_test_"):
                raise RazorpaySecurityError(
                    f"Live Razorpay Key detected ('{self.key_id[:8]}...'). "
                    "RecoverAI operates strictly in Test Mode ('rzp_test_...'). "
                    "Refusing to initialize adapter."
                )

    def is_configured(self) -> bool:
        """Returns True if test credentials are present."""
        return bool(self.key_id and self.key_secret and self.key_id.startswith("rzp_test_"))

    def execute_action(
        self,
        strategy: str,
        context: PaymentContext,
        idempotency_key: str,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Executes a gated recovery intervention.
        Dispatches to concrete strategy handler.
        """
        if strategy == "no_action":
            return ExecutionResult(
                strategy="no_action",
                status="completed",
                reference_id=f"noop_{idempotency_key}",
                is_simulated=True,
            )

        if strategy == "payment_link":
            return self.create_payment_link(
                context=context,
                idempotency_key=idempotency_key,
                customer_email=customer_email,
                customer_phone=customer_phone,
            )

        if strategy == "delayed_retry":
            return self.schedule_delayed_retry(context=context, idempotency_key=idempotency_key)

        if strategy == "reminder":
            return self.dispatch_reminder(context=context, idempotency_key=idempotency_key)

        return ExecutionResult(
            strategy=strategy,
            status="failed",
            error_message=f"Unknown recovery strategy '{strategy}'",
        )

    def create_payment_link(
        self,
        context: PaymentContext,
        idempotency_key: str,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Creates a Standard Razorpay Payment Link (S-01).
        """
        # If credentials not provided or in offline test mode, produce deterministic simulated link
        if not self.is_configured():
            sim_id = f"plink_test_{uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_key).hex[:14]}"
            return ExecutionResult(
                strategy="payment_link",
                status="completed",
                reference_id=sim_id,
                reference_url=f"https://rzp.io/i/{sim_id}",
                is_simulated=True,
            )

        url = f"{self.base_url}/payment_links"
        payload = {
            "amount": context.amount,
            "currency": context.currency,
            "accept_partial": False,
            "description": f"RecoverAI Recovery - Order {context.order_id or context.payment_id}",
            "reference_id": idempotency_key[:40],
            "notify": {"sms": False, "email": False},  # Default to silent for safety
        }

        cust_info = {}
        if customer_email:
            cust_info["email"] = customer_email
        if customer_phone:
            cust_info["contact"] = customer_phone
        if cust_info:
            payload["customer"] = cust_info

        headers = {
            "X-Razorpay-Idempotency-Key": idempotency_key,
        }

        try:
            if self.http_client is not None:
                resp = self.http_client.post(
                    url,
                    json=payload,
                    headers=headers,
                    auth=(self.key_id, self.key_secret),
                )
                resp.raise_for_status()
                data = resp.json()
            else:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(
                        url,
                        json=payload,
                        headers=headers,
                        auth=(self.key_id, self.key_secret),
                    )
                    resp.raise_for_status()
                    data = resp.json()

            return ExecutionResult(
                strategy="payment_link",
                status="completed",
                reference_id=data.get("id"),
                reference_url=data.get("short_url"),
                raw_response=data,
                is_simulated=False,
            )
        except httpx.HTTPStatusError as e:
            raw_err = None
            try:
                raw_err = e.response.json()
            except Exception:
                pass
            logger.error(f"Razorpay Payment Link creation failed with HTTP {e.response.status_code}: {raw_err or e}")
            return ExecutionResult(
                strategy="payment_link",
                status="failed",
                error_message=str(e),
                raw_response=raw_err,
                is_simulated=False,
            )
        except Exception as e:
            logger.error(f"Razorpay Payment Link creation failed: {e}")
            return ExecutionResult(
                strategy="payment_link",
                status="failed",
                error_message=str(e),
                is_simulated=False,
            )

    def schedule_delayed_retry(
        self,
        context: PaymentContext,
        idempotency_key: str,
    ) -> ExecutionResult:
        """
        Schedules a delayed retry for transient network failures (S-02).
        No customer disturbance; staged internally.
        """
        retry_id = f"retry_test_{uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_key).hex[:12]}"
        return ExecutionResult(
            strategy="delayed_retry",
            status="completed",
            reference_id=retry_id,
            is_simulated=True,
        )

    def dispatch_reminder(
        self,
        context: PaymentContext,
        idempotency_key: str,
    ) -> ExecutionResult:
        """
        Stages customer recovery reminder (S-03).
        """
        rem_id = f"rem_test_{uuid.uuid5(uuid.NAMESPACE_DNS, idempotency_key).hex[:12]}"
        return ExecutionResult(
            strategy="reminder",
            status="completed",
            reference_id=rem_id,
            is_simulated=True,
        )
