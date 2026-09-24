"""At-rest encryption for mailbox refresh tokens.

Tokens are encrypted with Fernet (AES-128-CBC + HMAC-SHA256) using the key in
EMAIL_TOKEN_ENCRYPTION_KEY. Without a valid key, mailbox connections are refused
rather than stored in plaintext. Never log or return the key, a token, or a
ciphertext.

Generate a key once per deployment (keep it in the secret store, not in git):
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

KEY_ENV = "EMAIL_TOKEN_ENCRYPTION_KEY"


class TokenCryptoUnavailable(RuntimeError):
    pass


def _fernet() -> Fernet:
    raw = os.environ.get(KEY_ENV, "").strip()
    if not raw:
        raise TokenCryptoUnavailable(f"{KEY_ENV} is not set")
    try:
        return Fernet(raw.encode())
    except (ValueError, TypeError) as exc:
        raise TokenCryptoUnavailable(f"{KEY_ENV} is not a valid Fernet key") from exc


def is_configured() -> bool:
    try:
        _fernet()
        return True
    except TokenCryptoUnavailable:
        return False


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:  # key rotated or data tampered with
        raise TokenCryptoUnavailable("stored token cannot be decrypted with the current key") from exc
