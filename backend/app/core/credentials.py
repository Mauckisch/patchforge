import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SECRET_KEY_FILE = Path("/data/secret.key")
KEY_SIZE = 32
NONCE_SIZE = 12


def _load_or_create_master_key() -> bytes:
    if SECRET_KEY_FILE.exists():
        key = SECRET_KEY_FILE.read_bytes()

        if len(key) != KEY_SIZE:
            raise RuntimeError(
                "Invalid PatchForge master key length in /data/secret.key"
            )

        return key

    key = AESGCM.generate_key(bit_length=256)

    fd = os.open(
        SECRET_KEY_FILE,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )

    try:
        os.write(fd, key)
    finally:
        os.close(fd)

    return key


def encrypt_secret(value: str) -> tuple[bytes, bytes]:
    if not value:
        raise ValueError("Secret must not be empty")

    key = _load_or_create_master_key()
    nonce = os.urandom(NONCE_SIZE)

    aesgcm = AESGCM(key)

    ciphertext = aesgcm.encrypt(
        nonce,
        value.encode("utf-8"),
        None,
    )

    return nonce, ciphertext


def decrypt_secret(
    nonce: bytes,
    ciphertext: bytes,
) -> str:
    key = _load_or_create_master_key()

    aesgcm = AESGCM(key)

    plaintext = aesgcm.decrypt(
        nonce,
        ciphertext,
        None,
    )

    return plaintext.decode("utf-8")
