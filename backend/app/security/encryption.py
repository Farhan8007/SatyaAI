"""
Cryptographic primitives used across the paper lifecycle:
- AES-256 (CBC) encryption/decryption of paper content
- SHA-256 hashing for tamper detection & chained audit logs
- RSA digital signatures for paper authenticity

Day 2 changes (Security Lead):
- RSA keys are now loaded from persistent PEM files on disk. If the files
  don't exist on first startup, a new keypair is generated and saved so that
  signatures survive server restarts.
- AES key handling is config-driven with validation (must be exactly 32 bytes).
"""
import base64
import hashlib
import os
import pathlib
from typing import Optional

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization

from app.config import settings

# --------------------------------------------------------------------------
# AES-256 symmetric encryption (paper contents)
# --------------------------------------------------------------------------

def _get_key() -> bytes:
    """Return exactly 32 bytes for AES-256 from the configured secret.

    Validates key length at call-time so misconfigurations surface early.
    """
    raw = settings.aes_secret_key.encode()
    if len(raw) < 32:
        raise ValueError(
            f"AES_SECRET_KEY must be at least 32 bytes, got {len(raw)}. "
            "Set a proper 32-byte key in your .env file."
        )
    return raw[:32]


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
#
# Day 2: Keys are loaded from / persisted to PEM files so that signatures
# survive backend restarts. On first run the key directory and files are
# created automatically.
# --------------------------------------------------------------------------

def _ensure_key_dir(path: str) -> None:
    """Create parent directories for a key file if they don't exist."""
    pathlib.Path(path).parent.mkdir(parents=True, exist_ok=True)


def _generate_and_save_keys(priv_path: str, pub_path: str):
    """Generate a fresh RSA-2048 keypair and write PEM files to disk."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    _ensure_key_dir(priv_path)
    _ensure_key_dir(pub_path)

    with open(priv_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    with open(pub_path, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    return private_key, public_key


def get_rsa_key_paths() -> tuple[str, str]:
    """Resolve paths to RSA private and public PEM files.

    Configurable via environment variables (RSA_KEYS_DIR, RSA_PRIVATE_KEY_PATH,
    RSA_PUBLIC_KEY_PATH) or backend settings, defaulting to directory ./keys/.
    """
    keys_dir = os.environ.get("RSA_KEYS_DIR", getattr(settings, "rsa_keys_dir", "./keys"))
    priv_path = os.environ.get(
        "RSA_PRIVATE_KEY_PATH",
        getattr(settings, "rsa_private_key_path", "") or os.path.join(keys_dir, "satya_rsa_private.pem"),
    )
    pub_path = os.environ.get(
        "RSA_PUBLIC_KEY_PATH",
        getattr(settings, "rsa_public_key_path", "") or os.path.join(keys_dir, "satya_rsa_public.pem"),
    )
    return priv_path, pub_path


def _load_or_create_keys(priv_path: Optional[str] = None, pub_path: Optional[str] = None):
    """Load RSA keys from configured PEM paths, generating them once if missing."""
    if not priv_path or not pub_path:
        priv_path, pub_path = get_rsa_key_paths()

    if os.path.isfile(priv_path) and os.path.isfile(pub_path):
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        with open(pub_path, "rb") as f:
            public_key = serialization.load_pem_public_key(f.read())
        return private_key, public_key

    # First run only — generate and persist to disk
    print(f"[encryption] RSA key files not found. Generating new keypair at:")
    print(f"  private: {priv_path}")
    print(f"  public:  {pub_path}")
    return _generate_and_save_keys(priv_path, pub_path)


_private_key, _public_key = _load_or_create_keys()


def reload_keys(priv_path: Optional[str] = None, pub_path: Optional[str] = None):
    """Explicitly reload RSA keys from disk (useful for tests and restarts)."""
    global _private_key, _public_key
    _private_key, _public_key = _load_or_create_keys(priv_path, pub_path)
    return _private_key, _public_key


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
    try:
        signature = base64.b64decode(signature_b64)
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
