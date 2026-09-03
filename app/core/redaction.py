import re
from typing import Any, Dict, List, Union

# Compiled regular expressions for sensitive secrets and tokens
JWT_REGEX = re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}")
BEARER_REGEX = re.compile(r"Bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE)
API_KEY_REGEX = re.compile(r"(api[_-]?key|secret|token|password|auth_token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?", re.IGNORECASE)
CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,16}\b")
UPI_REGEX = re.compile(r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b")
PHONE_REGEX = re.compile(r"\b(?:\+?91[\-\s]?)?[6789]\d{9}\b")

# Sensitive dictionary keys to mask completely
SENSITIVE_KEYS = {
    "password", "password_hash", "hashed_password", "token", "access_token", "refresh_token",
    "jwt", "secret", "jwt_secret", "api_key", "auth_token", "twilio_auth_token",
    "razorpay_key_secret", "gemini_api_key", "card_number", "cvv", "otp", "medical_notes",
    "clinical_notes", "prescription", "notes"
}

def mask_string(val: str) -> str:
    """Masks secret tokens, credentials, and sensitive patterns in a raw string."""
    if not isinstance(val, str):
        return str(val)
    
    val = JWT_REGEX.sub("[REDACTED_JWT]", val)
    val = BEARER_REGEX.sub("Bearer [REDACTED_TOKEN]", val)
    val = API_KEY_REGEX.sub(r"\1=[REDACTED_SECRET]", val)
    val = CARD_REGEX.sub("[REDACTED_CARD]", val)
    return val

def redact_sensitive_data(data: Any, max_depth: int = 5) -> Any:
    """
    Recursively scrubs sensitive keys, tokens, and PII from dicts, lists, and strings.
    Safe for JSON serialization and logging.
    """
    if max_depth <= 0 or data is None:
        return data

    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(s in k_lower for s in SENSITIVE_KEYS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = redact_sensitive_data(v, max_depth - 1)
        return sanitized

    elif isinstance(data, list):
        return [redact_sensitive_data(item, max_depth - 1) for item in data]

    elif isinstance(data, tuple):
        return tuple(redact_sensitive_data(item, max_depth - 1) for item in data)

    elif isinstance(data, str):
        return mask_string(data)

    return data
