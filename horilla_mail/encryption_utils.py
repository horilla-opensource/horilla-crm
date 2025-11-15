import os

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_or_create_encryption_key():
    """
    Get encryption key from environment or generate new one.
    This is safe for open source projects.
    """
    # Try to get from environment variable first (production)
    key = os.environ.get("FIELD_ENCRYPTION_KEY")

    if not key:
        # Try to get from settings (if user configured it)
        key = getattr(settings, "FIELD_ENCRYPTION_KEY", None)

    if not key:
        # For development: try to read from local file
        key_file = os.path.join(settings.BASE_DIR, ".encryption_key")

        if os.path.exists(key_file):
            with open(key_file, "r") as f:
                key = f.read().strip()
        else:
            # Generate new key and save it
            key = Fernet.generate_key().decode()
            with open(key_file, "w") as f:
                f.write(key)
            print(f"⚠️  New encryption key generated and saved to {key_file}")
            print("⚠️  Keep this file secure and don't commit it to Git!")

    return key


def get_cipher():
    """Get Fernet cipher instance"""
    key = get_or_create_encryption_key()
    if not key:
        raise ImproperlyConfigured("Could not get or create encryption key")
    return Fernet(key.encode())


def encrypt_password(plain_password):
    """Encrypt password"""
    if not plain_password:
        return None
    cipher = get_cipher()
    return cipher.encrypt(plain_password.encode()).decode()


def decrypt_password(encrypted_password):
    """Decrypt password"""
    if not encrypted_password:
        return None
    cipher = get_cipher()
    try:
        return cipher.decrypt(encrypted_password.encode()).decode()
    except Exception as e:
        raise ValueError(
            f"Failed to decrypt password. You may be using a different encryption key. Error: {e}"
        )
