from django.db import models

from .encryption_utils import encrypt_password


class EncryptedCharField(models.CharField):
    """
    Custom field that encrypts data but NEVER decrypts automatically.
    Decryption must be done explicitly when needed (e.g., sending emails).
    """

    def from_db_value(self, value, expression, connection):
        """
        Return encrypted value AS-IS.
        DO NOT decrypt automatically - keeps password hidden in forms.
        """
        return value

    def get_prep_value(self, value):
        """Encrypt when saving to database"""
        if value is None or value == "":
            return value

        # If already encrypted (long string), don't re-encrypt
        if isinstance(value, str) and len(value) > 100:
            return value

        # Encrypt plain text password
        return encrypt_password(value)
