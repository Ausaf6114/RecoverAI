"""
Contextual diagnosis engine using Google Gemini structured JSON.

Analyzes payment failures to hypothesize the root cause and confidence.
Includes a deterministic rule-based fallback when GEMINI_API_KEY is not configured
or during offline test execution.
"""
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Any
import httpx

from app.core.config import get_settings
from app.domain.models import PaymentContext

logger = logging.getLogger(__name__)


@dataclass
class DiagnosisResult:
    """Structured diagnosis output produced by contextual reasoning."""
    failure_category: str       # "authentication_failure" | "network_timeout" | "insufficient_funds" | "general_failure"
    hypothesis: str             # Root cause explanation
    confidence: str             # "high" | "medium" | "low"
    key_signals: List[str] = field(default_factory=list)
    recommended_strategy_hint: Optional[str] = None
    provider: str = "gemini"     # "gemini" or "deterministic_fallback"


_UNSET = object()


class GeminiDiagnostician:
    """
    Contextual failure diagnostician using Google Gemini structured JSON generation.
    """

    def __init__(self, api_key: Any = _UNSET, model: str = "gemini-1.5-flash"):
        settings = get_settings()
        self.api_key = settings.GEMINI_API_KEY if api_key is _UNSET else api_key
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    def diagnose(self, context: PaymentContext) -> DiagnosisResult:
        """
        Diagnoses a payment failure context.
        Attempts Gemini LLM diagnosis if API key is present; falls back cleanly to deterministic reasoning.
        """
        if not self.api_key:
            return self._deterministic_fallback(context, reason="gemini_api_key_missing")

        try:
            return self._call_gemini(context)
        except Exception as e:
            logger.warning(f"Gemini diagnosis API call failed: {e}. Falling back to deterministic diagnosis.")
            return self._deterministic_fallback(context, reason=f"gemini_call_error: {str(e)}")

    def _call_gemini(self, context: PaymentContext) -> DiagnosisResult:
        """Calls Gemini API with structured JSON output constraint."""
        prompt = f"""
You are an expert payment recovery diagnostics engine for RecoverAI.
Analyze the following payment failure context and return strict JSON conforming to this schema:
{{
  "failure_category": "authentication_failure" | "network_timeout" | "insufficient_funds" | "general_failure",
  "hypothesis": "Short, objective explanation of the likely failure mechanism (do not invent facts)",
  "confidence": "high" | "medium" | "low",
  "key_signals": ["signal1", "signal2"],
  "recommended_strategy_hint": "payment_link" | "delayed_retry" | "reminder" | "no_action"
}}

Payment Failure Context:
- Amount: ₹{context.amount / 100:.2f} ({context.currency})
- Method: {context.method or 'unknown'}
- Error Source: {context.error_source or 'unknown'}
- Error Step: {context.error_step or 'unknown'}
- Error Reason: {context.error_reason or 'unknown'}
- Error Code: {context.error_code or 'none'}
- Attempt Number: {context.attempt_number}
- Customer Successful Methods History: {', '.join(context.customer_successful_methods) if context.customer_successful_methods else 'none'}
- Customer Prior Failures: {context.customer_failed_payments}
- Customer Prior Successes: {context.customer_successful_payments}

Return ONLY valid JSON.
"""

        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1,
            },
        }

        url = f"{self.endpoint}?key={self.api_key}"
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        text_output = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text_output)

        return DiagnosisResult(
            failure_category=parsed.get("failure_category", "general_failure"),
            hypothesis=parsed.get("hypothesis", "Failure analyzed via Gemini."),
            confidence=parsed.get("confidence", "medium"),
            key_signals=parsed.get("key_signals", []),
            recommended_strategy_hint=parsed.get("recommended_strategy_hint"),
            provider="gemini",
        )

    def _deterministic_fallback(self, context: PaymentContext, reason: str = "") -> DiagnosisResult:
        """
        Deterministic, rule-based fallback aligning with synthetic failure patterns.
        """
        err_src = (context.error_source or "").lower()
        err_step = (context.error_step or "").lower()
        err_reason = (context.error_reason or "").lower()
        method = (context.method or "").lower()
        attempts = context.attempt_number

        # Pattern A: Card authentication failure + alternate method available
        if err_step == "payment_authentication" or "otp" in err_reason or err_reason == "auth_failed":
            signals = ["card_3ds_step_failed"]
            if "upi" in [m.lower() for m in context.customer_successful_methods]:
                signals.append("customer_has_upi_history")
            return DiagnosisResult(
                failure_category="authentication_failure",
                hypothesis="Card 3D-Secure authentication failed. Customer possesses alternative UPI payment history.",
                confidence="high",
                key_signals=signals,
                recommended_strategy_hint="payment_link",
                provider="deterministic_fallback",
            )

        # Pattern B: Network / gateway timeout
        if err_src == "network" or "timeout" in err_reason or "timed_out" in err_reason:
            return DiagnosisResult(
                failure_category="network_timeout",
                hypothesis="Transient banking gateway timeout occurred during authorization.",
                confidence="high",
                key_signals=["network_gateway_timeout", "single_attempt"],
                recommended_strategy_hint="delayed_retry",
                provider="deterministic_fallback",
            )

        # Pattern C: Repeated failures / balance exhaustion
        if attempts >= 3 or "insufficient" in err_reason or context.customer_failed_payments >= 3:
            return DiagnosisResult(
                failure_category="insufficient_funds",
                hypothesis=f"Repeated authorization declines across {attempts} attempts indicate balance exhaustion or expired instrument.",
                confidence="high",
                key_signals=["repeated_declines", f"attempt_count_{attempts}"],
                recommended_strategy_hint="no_action",
                provider="deterministic_fallback",
            )

        # Pattern D: General / default
        return DiagnosisResult(
            failure_category="general_failure",
            hypothesis=f"Payment attempt was declined at {err_step or 'initiation'} by {err_src or 'gateway'}.",
            confidence="medium",
            key_signals=[f"error_reason_{err_reason or 'unknown'}"],
            recommended_strategy_hint="payment_link",
            provider="deterministic_fallback",
        )
