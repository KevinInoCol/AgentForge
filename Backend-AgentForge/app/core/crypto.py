"""Cifrado simétrico de credenciales de terceros (tokens OAuth) antes de guardarlas.

Usamos Fernet (AES-128 + HMAC). La clave vive en `ENCRYPTION_KEY` (.env) y NUNCA
en la DB. Si la clave falta, fallamos ruidosamente al cifrar (no queremos guardar
tokens en texto plano por accidente).

Generar una clave:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
import json
from functools import lru_cache

from cryptography.fernet import Fernet

from app.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    if not settings.encryption_key:
        raise RuntimeError(
            "ENCRYPTION_KEY no configurada: no se pueden cifrar credenciales. "
            "Genera una con Fernet.generate_key() y ponla en .env."
        )
    return Fernet(settings.encryption_key.encode())


def encrypt_json(data: dict) -> str:
    """Serializa un dict y lo cifra → texto (para guardar en DB)."""
    return _fernet().encrypt(json.dumps(data).encode()).decode()


def decrypt_json(blob: str) -> dict:
    """Descifra un blob previamente creado con encrypt_json → dict."""
    if not blob:
        return {}
    return json.loads(_fernet().decrypt(blob.encode()).decode())


def sign_state(data: dict) -> str:
    """Firma+cifra un `state` para el flujo OAuth (viaja a Google y vuelve).

    Es un token Fernet (url-safe), así que se puede pasar como query param.
    """
    return encrypt_json(data)


def verify_state(token: str, max_age_seconds: int = 600) -> dict:
    """Verifica el `state` del callback. Lanza si es inválido o expiró (>10 min)."""
    return json.loads(_fernet().decrypt(token.encode(), ttl=max_age_seconds).decode())
