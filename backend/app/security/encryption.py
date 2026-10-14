"""
Cryptographic primitives used across the paper lifecycle:
- AES-256 (CBC) encryption/decryption of paper content
- SHA-256 hashing for tamper detection & chained audit logs
- RSA digital signatures for paper authenticity
"""
import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization

from app.config import settings

# --------------------------------------------------------------------------
# AES-256 symmetric encryption (paper contents)
# --------------------------------------------------------------------------

def _get_key() -> bytes:
    key = settings.aes_secret_key.encode()
    return key[:32].ljust(32, b"0")  # ensure exactly 32 bytes


def aes_encrypt(plaintext: bytes) -> str:
    key = _get_key()
    iv = os.urandom(16)
    padder = sym_padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + ciphertext).decode()


def aes_decrypt(blob_b64: str) -> bytes:
    raw = base64.b64decode(blob_b64)
    iv, ciphertext = raw[:16], raw[16:]
    key = _get_key()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = sym_padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


# --------------------------------------------------------------------------
# SHA-256 hashing (integrity + chained audit log)
# --------------------------------------------------------------------------

def sha256_hash(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def chain_hash(prev_hash: str, entry_data: str) -> str:
    """Chain each audit log entry to the previous one's hash, like a mini blockchain."""
    return sha256_hash(prev_hash + entry_data)


# --------------------------------------------------------------------------
# RSA digital signatures (paper authenticity - who set/approved it)
# --------------------------------------------------------------------------

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()


def sign_data(data: bytes) -> str:
    signature = _private_key.sign(
        data,
        asym_padding.PSS(
            mgf=asym_padding.MGF1(hashes.SHA256()),
            salt_length=asym_padding.PSS.MAX_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode()


def verify_signature(data: bytes, signature_b64: str) -> bool:
    signature = base64.b64decode(signature_b64)
    try:
        _public_key.verify(
            signature,
            data,
            asym_padding.PSS(
                mgf=asym_padding.MGF1(hashes.SHA256()),
                salt_length=asym_padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return True
    except Exception:
        return False
