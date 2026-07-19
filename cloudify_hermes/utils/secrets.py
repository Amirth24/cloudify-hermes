"""Secret detection and stripping utilities."""
from __future__ import annotations
from typing import Any, Dict, Set

SECRET_KEY_PATTERNS: Set[str] = {
    "api_key", "apikey", "token", "password", "passwd", "secret",
    "passphrase", "private_key", "access_key", "secret_key",
    "client_secret", "refresh_token", "bearer_token",
}

SECRET_ENV_PATTERNS: Set[str] = {
    "API_KEY", "TOKEN", "PASSWORD", "SECRET", "PASSPHRASE",
    "PRIVATE_KEY", "ACCESS_KEY", "SECRET_KEY", "CLIENT_SECRET",
    "REFRESH_TOKEN", "BEARER_TOKEN",
}


def is_secret_key(key: str) -> bool:
    """Return True if the key looks like a secret."""
    lower = key.lower()
    for pattern in SECRET_KEY_PATTERNS:
        if pattern in lower:
            return True
    for pattern in SECRET_ENV_PATTERNS:
        if pattern in key.upper():
            return True
    return False


def strip_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively remove any key that looks like a secret."""
    result: Dict[str, Any] = {}
    for k, v in config.items():
        if is_secret_key(k):
            continue
        if isinstance(v, dict):
            result[k] = strip_secrets(v)
        elif isinstance(v, list):
            result[k] = [strip_secrets(item) if isinstance(item, dict) else item for item in v]
        else:
            result[k] = v
    return result