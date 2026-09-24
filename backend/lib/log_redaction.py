"""Keep OAuth secrets out of log lines.

The mailbox OAuth callback URL carries `code` and `state` in its query string, and
uvicorn's access log / httpx's request log print full URLs at INFO. This filter
rewrites those values (and any access/refresh token or client secret that might
appear in a URL) to "[redacted]" before a record is emitted.
"""

from __future__ import annotations

import logging
import re

_SENSITIVE = re.compile(r"(?i)\b(code|state|access_token|refresh_token|id_token|client_secret|token)=([^&\s\"']+)")
LOGGERS = ("uvicorn.access", "uvicorn.error", "httpx", "httpx2", "httpcore")


def redact(text: str) -> str:
    return _SENSITIVE.sub(lambda m: f"{m.group(1)}=[redacted]", text)


class RedactOAuthParams(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact(a) if isinstance(a, str) else redact(str(a)) if a.__class__.__name__ == "URL" else a for a in record.args)
        elif isinstance(record.args, dict):
            record.args = {k: redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
        return True


_FILTER = RedactOAuthParams()


def install() -> None:
    """Idempotent: attach the filter to the loggers (and their handlers) that print URLs."""
    for name in LOGGERS:
        logger = logging.getLogger(name)
        if _FILTER not in logger.filters:
            logger.addFilter(_FILTER)
        for handler in logger.handlers:
            if _FILTER not in handler.filters:
                handler.addFilter(_FILTER)
