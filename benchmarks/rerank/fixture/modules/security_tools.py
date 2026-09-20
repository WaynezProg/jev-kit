"""Safe display and request helpers, not cryptographic primitives."""

def mask_email(value):
    local, domain = value.split("@", 1)
    return local[:1] + "***@" + domain

def redact_token(value):
    return value[:4] + "..." if len(value) > 4 else "..."

def is_safe_redirect(url):
    return url.startswith("/") and not url.startswith("//")

def constant_label(value):
    return "set" if value else "missing"

def safe_header_value(value):
    """Reject CR/LF so a value cannot create a second HTTP header."""
    if "\n" in value:
        raise ValueError("header value contains a line break")
    return value.strip()

def require_origin(origin, allowed):
    if origin not in allowed:
        raise PermissionError("origin is not allowed")
    return origin
