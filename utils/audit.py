import json
from typing import Any
from urllib.parse import urlsplit, urlunsplit

MAX_AUDIT_BYTES = 16 * 1024
SENSITIVE_KEYS = (
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "apikey",
    "accesskey",
    "privatekey",
    "credential",
    "phone",
    "email",
    "error",
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("_", "").replace("-", "")
            if any(sensitive in normalized for sensitive in SENSITIVE_KEYS):
                redacted[key] = "[REDACTED]"
            elif normalized.endswith("url") and isinstance(item, str):
                redacted[key] = sanitize_url(item)
            elif normalized == "params" and isinstance(item, str):
                redacted[key] = sanitize_params(item)
            else:
                redacted[key] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str) and value.lstrip().startswith(("{", "[")):
        try:
            nested = json.loads(value)
        except ValueError:
            return "[无法解析的嵌套参数，已省略]"
        return json.dumps(_redact(nested), ensure_ascii=False)
    return value


def sanitize_params(params: str | bytes | None) -> str | None:
    if not params:
        return None
    if (
        len(params if isinstance(params, bytes) else params.encode())
        > MAX_AUDIT_BYTES
    ):
        return "[参数过长，已省略]"
    try:
        value = json.loads(params)
    except ValueError, UnicodeError, RecursionError:
        return "[非 JSON 参数，已省略]"
    if not isinstance(value, (dict, list)):
        return "[非结构化参数，已省略]"
    try:
        serialized = json.dumps(_redact(value), ensure_ascii=False)
        if len(serialized.encode()) > MAX_AUDIT_BYTES:
            return "[脱敏后参数过长，已省略]"
        return serialized
    except RecursionError:
        return "[嵌套过深，已省略]"


def sanitize_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parts = urlsplit(url)
        return urlunsplit(
            (parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", "")
        )[:500]
    except ValueError:
        return "[无效地址]"
