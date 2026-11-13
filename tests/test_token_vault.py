import os
import unittest
from unittest.mock import patch

from autored.token_vault import D1EncryptedTokenStore, TokenVaultError


class FakeD1:
    def __init__(self):
        self.rows = {}

    def query(self, sql, params):
        if sql.startswith("SELECT encrypted_refresh_token"):
            row = self.rows.get((params[0], params[1]))
            return {"results": [row] if row else []}
        if sql.startswith("INSERT INTO provider_tokens"):
            self.rows[(params[0], params[1])] = {
                "encrypted_refresh_token": params[2],
                "iv": params[3],
                "key_version": params[4],
            }
            return {"results": []}
        raise AssertionError("unexpected SQL")


class D1EncryptedTokenStoreTests(unittest.TestCase):
    def setUp(self):
        self.key = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
        self.d1 = FakeD1()
        self.store = D1EncryptedTokenStore(self.d1, self.key)

    def test_round_trip_stores_only_ciphertext(self):
        token = "refresh-token-value"
        self.store.save_refresh_token("tiktok_pieknemedia", token)
        row = self.d1.rows[("tiktok", "tiktok_pieknemedia")]
        self.assertNotIn(token, row["encrypted_refresh_token"])
        self.assertNotIn(token, row["iv"])
        self.assertEqual(token, self.store.get_refresh_token("tiktok_pieknemedia"))

    def test_refresh_rotation_replaces_encrypted_value(self):
        self.store.save_refresh_token("tiktok_pieknemedia", "old-refresh")
        old_ciphertext = self.d1.rows[("tiktok", "tiktok_pieknemedia")]["encrypted_refresh_token"]
        self.store.save_refresh_token("tiktok_pieknemedia", "new-refresh")
        new_ciphertext = self.d1.rows[("tiktok", "tiktok_pieknemedia")]["encrypted_refresh_token"]
        self.assertNotEqual(old_ciphertext, new_ciphertext)
        self.assertEqual("new-refresh", self.store.get_refresh_token("tiktok_pieknemedia"))

    def test_wrong_key_cannot_decrypt_token(self):
        self.store.save_refresh_token("tiktok_pieknemedia", "refresh-token-value")
        wrong_key = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="
        wrong_store = D1EncryptedTokenStore(self.d1, wrong_key)
        with self.assertRaisesRegex(TokenVaultError, "token_decryption_failed"):
            wrong_store.get_refresh_token("tiktok_pieknemedia")

    def test_missing_initial_token_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(TokenVaultError, "refresh_token_missing"):
                self.store.get_refresh_token("tiktok_pieknemedia")

    def test_initial_environment_token_is_migrated_to_encrypted_d1(self):
        with patch.dict(os.environ, {"TIKTOK_PIEKNEMEDIA_REFRESH_TOKEN": "initial-refresh"}, clear=True):
            self.assertEqual("initial-refresh", self.store.get_refresh_token("tiktok_pieknemedia"))
        self.assertIn(("tiktok", "tiktok_pieknemedia"), self.d1.rows)

    def test_invalid_encryption_key_is_rejected(self):
        with self.assertRaisesRegex(TokenVaultError, "encryption_key_must_be_32_bytes_base64"):
            D1EncryptedTokenStore(self.d1, "c2hvcnQ=")


if __name__ == "__main__":
    unittest.main()
