import os
import pytest
from cloudify_hermes.storage.crypto import encrypt, decrypt

def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setenv("CLOUDIFY_PASSPHRASE", "test-passphrase-123")
    plaintext = b"sensitive backup data"
    ciphertext = encrypt(plaintext, passphrase_env="CLOUDIFY_PASSPHRASE")
    assert ciphertext != plaintext
    decrypted = decrypt(ciphertext, passphrase_env="CLOUDIFY_PASSPHRASE")
    assert decrypted == plaintext

def test_encrypt_produces_different_ciphertext(monkeypatch):
    monkeypatch.setenv("CLOUDIFY_PASSPHRASE", "test-passphrase-123")
    plaintext = b"same data"
    ct1 = encrypt(plaintext, passphrase_env="CLOUDIFY_PASSPHRASE")
    ct2 = encrypt(plaintext, passphrase_env="CLOUDIFY_PASSPHRASE")
    assert ct1 != ct2

def test_decrypt_wrong_passphrase_fails(monkeypatch):
    monkeypatch.setenv("CLOUDIFY_PASSPHRASE", "correct")
    plaintext = b"secret"
    ciphertext = encrypt(plaintext, passphrase_env="CLOUDIFY_PASSPHRASE")
    monkeypatch.setenv("CLOUDIFY_PASSPHRASE", "wrong")
    with pytest.raises(Exception):
        decrypt(ciphertext, passphrase_env="CLOUDIFY_PASSPHRASE")

def test_missing_passphrase_raises(monkeypatch):
    monkeypatch.delenv("CLOUDIFY_PASSPHRASE", raising=False)
    with pytest.raises(ValueError):
        encrypt(b"data", passphrase_env="CLOUDIFY_PASSPHRASE")