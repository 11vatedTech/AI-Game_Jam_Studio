from __future__ import annotations

import sqlite3

from elevenvt_studio.db import SCHEMA, SCHEMA_VERSION, Database


def _v1_database(path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA user_version=1")
        conn.execute(
            "INSERT INTO jobs(id,name,status,spec_json,created_at,updated_at,workspace)"
            " VALUES('job-old','legacy','SUCCEEDED','{}','2026-11-01T00:00:00Z','2026-11-01T00:00:00Z','C:/ws')"
        )
        conn.commit()
    finally:
        conn.close()


def test_v1_database_upgrades_without_losing_rows(tmp_path):
    path = tmp_path / "studio.sqlite3"
    _v1_database(path)

    Database(path)  # opening performs the migration

    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("SELECT name FROM jobs WHERE id='job-old'").fetchone()[0] == "legacy"
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"operations", "critic_findings", "decisions"} <= tables
    finally:
        conn.close()


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "studio.sqlite3"
    _v1_database(path)
    Database(path)
    Database(path)  # second open must be a no-op, not a re-run

    conn = sqlite3.connect(path)
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    finally:
        conn.close()


def test_fresh_database_lands_on_current_version(tmp_path):
    Database(tmp_path / "fresh.sqlite3")
    conn = sqlite3.connect(tmp_path / "fresh.sqlite3")
    try:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        conn.close()


def test_newer_database_is_refused(tmp_path):
    path = tmp_path / "future.sqlite3"
    Database(path)
    conn = sqlite3.connect(path)
    try:
        conn.execute(f"PRAGMA user_version={SCHEMA_VERSION + 1}")
        conn.commit()
    finally:
        conn.close()

    try:
        Database(path)
    except RuntimeError as error:
        assert "newer" in str(error)
    else:  # pragma: no cover
        raise AssertionError("a future schema version must not be opened by an older runtime")
