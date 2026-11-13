import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_d1_backup import decrypt_and_verify, verify_sql_dump


class BackupVerificationTests(unittest.TestCase):
    def write_sql(self, sql):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "backup.sql"
        path.write_text(sql, encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return path

    def test_valid_sql_dump_passes_integrity_and_table_checks(self):
        sql = """
        CREATE TABLE profiles (id TEXT PRIMARY KEY);
        CREATE TABLE content_items (id TEXT PRIMARY KEY);
        CREATE TABLE publication_jobs (id TEXT PRIMARY KEY);
        CREATE TABLE quota_ledger (id TEXT PRIMARY KEY);
        CREATE TABLE daily_runs (local_date TEXT PRIMARY KEY);
        CREATE TABLE events (id TEXT PRIMARY KEY);
        CREATE TABLE provider_tokens (provider TEXT, profile_id TEXT, encrypted_refresh_token TEXT, iv TEXT, key_version TEXT);
        INSERT INTO profiles(id) VALUES ('tiktok_pieknemedia');
        """
        result = verify_sql_dump(self.write_sql(sql))
        self.assertEqual("ok", result["integrity"])
        self.assertEqual(1, result["row_counts"]["profiles"])
        self.assertEqual(7, len(result["tables"]))

    def test_missing_required_table_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing_expected_tables"):
            verify_sql_dump(self.write_sql("CREATE TABLE profiles (id TEXT PRIMARY KEY);"))

    def test_encrypted_archive_hash_is_checked_before_decryption(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "backup.sql.age"
            identity = root / "identity.txt"
            manifest = root / "manifest.json"
            archive.write_bytes(b"tampered-ciphertext")
            identity.write_text("not-used", encoding="utf-8")
            manifest.write_text(json.dumps({
                "plaintext_sha256": "0" * 64,
                "encrypted_sha256": "1" * 64,
                "database": "autored_idea_db"
            }), encoding="utf-8")
            with patch("verify_d1_backup.subprocess.run") as decrypt:
                with self.assertRaisesRegex(ValueError, "backup_encrypted_sha256_mismatch"):
                    decrypt_and_verify(archive, identity, manifest)
                decrypt.assert_not_called()

    def test_empty_dump_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "empty_sql_dump"):
            verify_sql_dump(self.write_sql("  "))


if __name__ == "__main__":
    unittest.main()
