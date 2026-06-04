import hmac
import hashlib
from django.conf import settings


def verify_whatsapp_signature(request_body: bytes, signature_header: str) -> bool:
    """
    Verify that the webhook request is from WhatsApp by validating the signature.

    Args:
        request_body: The raw request body as bytes
        signature_header: The X-Hub-Signature-256 header value from the request

    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not signature_header:
        return False

    # The signature header format is "sha256=<signature>"
    try:
        expected_signature = signature_header.split('sha256=')[1]
    except (IndexError, AttributeError):
        return False

    # Calculate the expected signature using HMAC SHA256
    app_secret = settings.WHATSAPP_APP_SECRET.encode('utf-8')
    calculated_signature = hmac.new(
        app_secret,
        request_body,
        hashlib.sha256
    ).hexdigest()

    # Compare signatures using constant-time comparison to prevent timing attacks
    return hmac.compare_digest(calculated_signature, expected_signature)
