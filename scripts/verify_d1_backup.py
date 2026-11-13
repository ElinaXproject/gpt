#!/usr/bin/env python3
"""Decrypt and verify an AUTORED IDEA D1 SQL backup without touching production."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_TABLES = {
    "profiles",
    "content_items",
    "publication_jobs",
    "quota_ledger",
    "daily_runs",
    "events",
}


def verify_sql_dump(sql_path: Path, expected_tables: set[str] | None = None) -> dict[str, Any]:
    sql = sql_path.read_text(encoding="utf-8")
    if not sql.strip():
        raise ValueError("empty_sql_dump")
    connection = sqlite3.connect(":memory:")
    try:
        connection.executescript(sql)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("sqlite_integrity_check_failed")
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        missing = (expected_tables or EXPECTED_TABLES) - tables
        if missing:
            raise ValueError("missing_expected_tables:" + ",".join(sorted(missing)))
        counts = {}
        for table in sorted(tables):
            safe_table = table.replace('"', '""')
            counts[table] = connection.execute(f'SELECT COUNT(*) FROM "{safe_table}"').fetchone()[0]
        return {"integrity": "ok", "tables": sorted(tables), "row_counts": counts}
    finally:
        connection.close()


def decrypt_and_verify(archive: Path, identity: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hash = manifest.get("plaintext_sha256")
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        raise ValueError("invalid_backup_manifest")
    with tempfile.TemporaryDirectory(prefix="autored-backup-") as tmp:
        sql_path = Path(tmp) / "autored_idea_db.sql"
        subprocess.run(
            ["age", "--decrypt", "--identity", str(identity), "--output", str(sql_path), str(archive)],
            check=True,
            capture_output=True,
            text=True,
        )
        actual_hash = hashlib.sha256(sql_path.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError("backup_sha256_mismatch")
        result = verify_sql_dump(sql_path)
        result["plaintext_sha256"] = actual_hash
        result["encrypted_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
        result["database"] = manifest.get("database", "unknown")
        return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = decrypt_and_verify(args.archive, args.identity, args.manifest)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)[:160]}, ensure_ascii=False))
        return 2
    print(json.dumps({"status": "verified", **result}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
