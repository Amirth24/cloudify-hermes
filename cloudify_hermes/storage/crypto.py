"""AES-256-GCM encryption using a passphrase from environment variable."""
from __future__ import annotations
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from cloudify_hermes.env import CloudifyEnv

_env = CloudifyEnv()

def _derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))

def encrypt(data: bytes, passphrase_env: str | None = None) -> bytes:
    passphrase_env = passphrase_env if passphrase_env is not None else _env.passphrase_env
    passphrase = os.environ.get(passphrase_env, "").strip()
    if not passphrase:
        raise ValueError(f"Passphrase env var '{passphrase_env}' is not set")
    salt = os.urandom(16)
    key = _derive_key(passphrase, salt)
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data)
    return salt + encrypted

def decrypt(data: bytes, passphrase_env: str | None = None) -> bytes:
    passphrase_env = passphrase_env if passphrase_env is not None else _env.passphrase_env
    passphrase = os.environ.get(passphrase_env, "").strip()
    if not passphrase:
        raise ValueError(f"Passphrase env var '{passphrase_env}' is not set")
    salt = data[:16]
    encrypted = data[16:]
    key = _derive_key(passphrase, salt)
    fernet = Fernet(key)
    return fernet.decrypt(encrypted)