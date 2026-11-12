"""Redact credential material from a detached JSON export."""

import re

REDACTED = "[REDACTED]"
_FIELDS = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "clientsecret",
    "apikey",
    "accesskey",
    "secretkey",
    "secretaccesskey",
    "awssecretaccesskey",
    "token",
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "sessiontoken",
    "authorization",
    "proxyauthorization",
    "cookie",
    "setcookie",
    "privatekey",
    "credentials",
    "credential",
    "connectionstring",
}
_ASSIGNMENT = re.compile(
    r"""(?ix)\b(password|passwd|pwd|client[_-]?secret|api[_-]?key|"""
    r"""access[_-]?token|refresh[_-]?token|secret|token)["']?\s*[=:]\s*"""
    r"""("[^"\r\n]*"|'[^'\r\n]*'|[^\s&,;]+)"""
)
_AUTH = re.compile(r"(?i)\b(Bearer|Basic)\s+[A-Za-z0-9+/_.=~-]+")
_PRIVATE_KEY = re.compile(
    r"-----BEGIN (?:[A-Z ]* )?PRIVATE KEY-----.*?"
    r"-----END (?:[A-Z ]* )?PRIVATE KEY-----",
    re.DOTALL,
)
_URL_AUTH = re.compile(r"(\b[a-zA-Z][a-zA-Z0-9+.-]*://)[^\s/@]+:[^\s/@]+@")


def _restricted(field: str) -> bool:
    # Support nested, dotted and JSON Pointer field names.
    parts = re.split(r"[./]", field)
    return any(re.sub(r"[^a-z0-9]", "", part.lower()) in _FIELDS for part in parts)


def redact_export(document: dict) -> dict:
    """Keep evidence locations but replace restricted values, including copies."""
    secrets: set[str] = set()

    def collect(value, restricted=False):
        if isinstance(value, dict):
            pointed = _restricted(str(value.get("pointer", "")))
            for key, item in value.items():
                collect(
                    item, restricted or _restricted(key) or (pointed and key == "value")
                )
        elif isinstance(value, list):
            for item in value:
                collect(item, restricted)
        elif restricted and value is not None and not isinstance(value, bool):
            secrets.add(str(value))
        elif isinstance(value, str):
            for match in _ASSIGNMENT.finditer(value):
                secrets.add(match[2].strip("\"'"))
            for match in _AUTH.finditer(value):
                secrets.add(match[0].split(None, 1)[1])

    collect(document)
    secrets.discard("")
    secret_pattern = (
        re.compile(
            "|".join(re.escape(s) for s in sorted(secrets, key=len, reverse=True))
        )
        if secrets
        else None
    )

    def clean(value):
        if isinstance(value, dict):
            pointed = _restricted(str(value.get("pointer", "")))
            return {
                key: REDACTED
                if _restricted(key) or (pointed and key == "value")
                else clean(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, str):
            if secret_pattern is not None:
                value = secret_pattern.sub(lambda match: REDACTED, value)
            value = _PRIVATE_KEY.sub(REDACTED, value)
            value = _ASSIGNMENT.sub(lambda match: match[1] + "=" + REDACTED, value)
            value = _AUTH.sub(lambda match: match[1] + " " + REDACTED, value)
            value = _URL_AUTH.sub(lambda match: match[1] + REDACTED + "@", value)
            return value
        return value

    return clean(document)
