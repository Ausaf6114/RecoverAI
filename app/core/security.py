import hmac
import hashlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def verify_razorpay_signature(
    raw_body: bytes,
    signature: Optional[str],
    webhook_secret: Optional[str]
) -> bool:
    """
    Verifies Razorpay webhook signature using HMAC-SHA256 and constant-time comparison.
    
    NEVER logs or exposes the webhook secret or raw credentials.
    """
    if not signature:
        logger.warning("HMAC verification failed: signature is missing or empty")
        return False
    if not webhook_secret:
        logger.warning("HMAC verification failed: webhook_secret is missing or empty")
        return False

    try:
        expected_signature = hmac.new(
            key=webhook_secret.strip().encode("utf-8"),
            msg=raw_body,
            digestmod=hashlib.sha256
        ).hexdigest()

        match = hmac.compare_digest(expected_signature, signature.strip())
        if not match:
            logger.warning("HMAC verification failed: signature mismatch (invalid HMAC)")
        return match
    except Exception as e:
        logger.warning("HMAC verification failed with exception: %s", type(e).__name__)
        return False
