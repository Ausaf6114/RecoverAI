import hmac
import hashlib
from typing import Optional


def verify_razorpay_signature(
    raw_body: bytes,
    signature: Optional[str],
    webhook_secret: Optional[str]
) -> bool:
    """
    Verifies Razorpay webhook signature using HMAC-SHA256 and constant-time comparison.
    
    NEVER logs or exposes the webhook secret or raw credentials.
    """
    if not signature or not webhook_secret:
        return False

    try:
        expected_signature = hmac.new(
            key=webhook_secret.strip().encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected_signature, signature)
    except Exception:
        return False
