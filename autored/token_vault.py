"""AES-GCM encrypted D1 token storage for rotating provider refresh tokens."""
from __future__ import annotations

import base64
import os
from typing import Any


class TokenVaultError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__("token_vault_" + code)


class D1EncryptedTokenStore:
    PROVIDER = "tiktok"
    KEY_VERSION = "v1"

    def __init__(self, d1_client: Any, encryption_key: str | bytes | None = None):
        raw_key = encryption_key if encryption_key is not None else os.environ.get("AUTORED_TOKEN_ENCRYPTION_KEY", "")
        if isinstance(raw_key, str):
            try:
                key = base64.urlsafe_b64decode(raw_key.encode("ascii"))
            except (ValueError, UnicodeEncodeError):
                raise TokenVaultError("invalid_encryption_key_encoding") from None
        else:
            key = raw_key
        if not isinstance(key, bytes) or len(key) != 32:
            raise TokenVaultError("encryption_key_must_be_32_bytes_base64")
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        except ImportError:
            raise TokenVaultError("cryptography_dependency_missing") from None
        self._aes = AESGCM(key)
        self.d1 = d1_client

    @staticmethod
    def _associated_data(profile_id: str) -> bytes:
        return f"AUTORED|{D1EncryptedTokenStore.PROVIDER}|{profile_id}|{D1EncryptedTokenStore.KEY_VERSION}".encode("utf-8")

    def get_refresh_token(self, profile_id: str) -> str:
        rows = self.d1.query(
            "SELECT encrypted_refresh_token, iv, key_version FROM provider_tokens WHERE provider=? AND profile_id=?",
            [self.PROVIDER, profile_id],
        ).get("results", [])
        if rows:
            row = rows[0]
            if row.get("key_version") != self.KEY_VERSION:
                raise TokenVaultError("unsupported_key_version")
            try:
                ciphertext = base64.urlsafe_b64decode(row["encrypted_refresh_token"].encode("ascii"))
                iv = base64.urlsafe_b64decode(row["iv"].encode("ascii"))
                plaintext = self._aes.decrypt(iv, ciphertext, self._associated_data(profile_id))
                token = plaintext.decode("utf-8")
            except Exception:
                raise TokenVaultError("token_decryption_failed") from None
            if not token:
                raise TokenVaultError("stored_token_empty")
            return token

        env_name = {
            "tiktok_pieknemedia": "TIKTOK_PIEKNEMEDIA_REFRESH_TOKEN",
            "tiktok_ocenionona6": "TIKTOK_OCENIONONA6_REFRESH_TOKEN",
        }.get(profile_id)
        initial = os.environ.get(env_name, "") if env_name else ""
        if not initial:
            raise TokenVaultError("refresh_token_missing")
        self.save_refresh_token(profile_id, initial)
        return initial

    def save_refresh_token(self, profile_id: str, refresh_token: str) -> None:
        if not profile_id or not refresh_token:
            raise TokenVaultError("invalid_token_record")
        iv = os.urandom(12)
        encrypted = self._aes.encrypt(iv, refresh_token.encode("utf-8"), self._associated_data(profile_id))
        self.d1.query(
            "INSERT INTO provider_tokens (provider, profile_id, encrypted_refresh_token, iv, key_version, updated_at) "
            "VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
            "ON CONFLICT(provider, profile_id) DO UPDATE SET "
            "encrypted_refresh_token=excluded.encrypted_refresh_token, iv=excluded.iv, "
            "key_version=excluded.key_version, updated_at=CURRENT_TIMESTAMP",
            [
                self.PROVIDER,
                profile_id,
                base64.urlsafe_b64encode(encrypted).decode("ascii"),
                base64.urlsafe_b64encode(iv).decode("ascii"),
                self.KEY_VERSION,
            ],
        )
