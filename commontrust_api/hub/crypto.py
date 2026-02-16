from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class HubCryptoError(Exception):
    pass


def _fernet(key_b64: str) -> Fernet:
    try:
        return Fernet(key_b64.encode("ascii"))
    except Exception as e:  # pragma: no cover
        raise HubCryptoError(f"Invalid encryption key: {e}") from e


def encrypt_token(key_b64: str, token: str) -> str:
    f = _fernet(key_b64)
    return f.encrypt(token.encode("utf-8")).decode("ascii")


def decrypt_token(key_b64: str, token_encrypted: str) -> str:
    f = _fernet(key_b64)
    try:
        return f.decrypt(token_encrypted.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise HubCryptoError("Failed to decrypt remote token") from e

