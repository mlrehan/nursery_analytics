"""Lightweight, idempotent SQL migration runner.

Applies numbered ``*.sql`` files from ``app/migrations/sql`` in order and records
each applied file in a ``schema_migrations`` table so re-runs are no-ops. This is a
deliberately small, transparent migration system (no external tooling) that runs on
container start and is safe to invoke repeatedly.
"""
from __future__ import annotations

import hashlib
import pathlib
import time

import psycopg

from app.core.config import settings

SQL_DIR = pathlib.Path(__file__).parent / "sql"


def _dsn() -> str:
    return (
        f"host={settings.POSTGRES_HOST} port={settings.POSTGRES_PORT} "
        f"dbname={settings.POSTGRES_DB} user={settings.POSTGRES_USER} "
        f"password={settings.POSTGRES_PASSWORD}"
    )


def _wait_for_db(max_attempts: int = 30, delay: float = 2.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with psycopg.connect(_dsn(), connect_timeout=3):
                return
        except psycopg.OperationalError as exc:  # pragma: no cover - infra timing
            print(f"[migrate] waiting for database ({attempt}/{max_attempts}): {exc}")
            time.sleep(delay)
    raise RuntimeError("Database did not become available in time")


def _ensure_tracking_table(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   TEXT PRIMARY KEY,
            checksum   TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def _applied(conn: psycopg.Connection) -> set[str]:
    rows = conn.execute("SELECT filename FROM schema_migrations").fetchall()
    return {r[0] for r in rows}


def run_migrations() -> None:
    _wait_for_db()
    files = sorted(SQL_DIR.glob("*.sql"))
    with psycopg.connect(_dsn(), autocommit=False) as conn:
        _ensure_tracking_table(conn)
        conn.commit()
        done = _applied(conn)
        for path in files:
            if path.name in done:
                print(f"[migrate] skip {path.name} (already applied)")
                continue
            sql = path.read_text(encoding="utf-8")
            checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()[:16]
            print(f"[migrate] applying {path.name} ...")
            try:
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (filename, checksum) VALUES (%s, %s)",
                    (path.name, checksum),
                )
                conn.commit()
                print(f"[migrate] applied  {path.name}")
            except Exception:
                conn.rollback()
                print(f"[migrate] FAILED   {path.name}")
                raise
    print("[migrate] all migrations up to date")


if __name__ == "__main__":
    run_migrations()
