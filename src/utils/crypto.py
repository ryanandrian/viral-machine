"""
Enkripsi kredensial sensitif tenant (OAuth refresh_token/client_secret dll) — Phase 4 BYO-CC.

Fernet (AES-128-CBC + HMAC) dengan master key di env `ENCRYPTION_KEY` (di `.env` VPS,
TIDAK pernah di-commit). Prinsip: plaintext kredensial sensitif TIDAK pernah disimpan di DB —
selalu lewat encrypt() sebelum tulis, decrypt() saat baca (hanya worker/backend service_role).
"""

import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken


class CryptoError(Exception):
    """Error enkripsi/dekripsi kredensial."""
    pass


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise CryptoError(
            "ENCRYPTION_KEY tidak diset di .env — wajib untuk enkripsi kredensial tenant."
        )
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except Exception as e:
        raise CryptoError(
            f"ENCRYPTION_KEY tidak valid (harus Fernet key base64 url-safe 32-byte): {e}"
        ) from e


def encrypt(plaintext: str | None) -> str | None:
    """Enkripsi string → token (str). None → None (kolom opsional)."""
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str | None) -> str | None:
    """Dekripsi token → plaintext. None → None. Raise CryptoError jika token rusak/key beda."""
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:
        raise CryptoError(
            "Dekripsi gagal — token rusak atau ENCRYPTION_KEY berbeda dari saat enkripsi."
        ) from e


def generate_key() -> str:
    """Generate Fernet key baru (untuk setup ENCRYPTION_KEY di .env)."""
    return Fernet.generate_key().decode()
