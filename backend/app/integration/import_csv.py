"""Generic CSV importer for real nursery data.

Drop CSV files (named below) into a folder and run:

    python -m app.integration.import_csv ./my_data
    python -m app.integration.import_csv ./my_data --truncate   # wipe facts/dims first

Rules
-----
* Files are loaded in FK-safe order (sites → rooms → parents → children → staff → facts).
* A file is optional — skip what you don't have.
* The CSV header names must match the table column names (a subset is fine; unknown
  columns are ignored). Provide your own consistent integer IDs across files
  (e.g. dim_room.site_id must match a dim_site.id you supplied).
* See docs/DATA_INTEGRATION.md for the column list of every file.
"""
from __future__ import annotations

import csv
import pathlib
import sys

import psycopg

from app.core.config import settings

# filename -> (table, fk-safe order is the list order below)
FILES = [
    ("sites.csv", "dim_site"),
    ("rooms.csv", "dim_room"),
    ("parents.csv", "dim_parent"),
    ("children.csv", "dim_child"),
    ("staff.csv", "dim_staff"),
    ("attendance.csv", "fact_attendance"),
    ("enrollment_events.csv", "fact_enrollment_event"),
    ("invoices.csv", "fact_invoice"),
    ("payments.csv", "fact_payment"),
    ("shifts.csv", "fact_staff_shift"),
    ("incidents.csv", "fact_incident"),
    ("eyfs.csv", "fact_eyfs_observation"),
    ("meals.csv", "fact_meal"),
    ("messages.csv", "fact_message"),
]
TRUNCATE_ORDER = [t for _, t in reversed(FILES)]


def _dsn() -> str:
    return (f"host={settings.POSTGRES_HOST} port={settings.POSTGRES_PORT} dbname={settings.POSTGRES_DB} "
            f"user={settings.POSTGRES_USER} password={settings.POSTGRES_PASSWORD}")


def _columns(conn: psycopg.Connection, table: str) -> set[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,)
    ).fetchall()
    return {r[0] for r in rows}


def _load_file(conn: psycopg.Connection, path: pathlib.Path, table: str) -> int:
    valid = _columns(conn, table)
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        headers = [h for h in (reader.fieldnames or []) if h in valid]
        if not headers:
            print(f"  ! {path.name}: no matching columns for {table}; skipped")
            return 0
        cols = ", ".join(headers)
        ph = ", ".join(["%s"] * len(headers))
        sql = f"INSERT INTO {table} ({cols}) VALUES ({ph})"
        rows = [[(row[h] if row.get(h) not in ("", None) else None) for h in headers] for row in reader]
    if rows:
        conn.cursor().executemany(sql, rows)
    return len(rows)


def run(folder: str, truncate: bool = False) -> None:
    base = pathlib.Path(folder)
    if not base.is_dir():
        raise SystemExit(f"folder not found: {folder}")
    with psycopg.connect(_dsn()) as conn:
        if truncate:
            print("[import] truncating existing dim_/fact_ tables …")
            conn.execute("TRUNCATE " + ", ".join(TRUNCATE_ORDER) + " RESTART IDENTITY CASCADE")
            conn.commit()
        total = 0
        for fname, table in FILES:
            path = base / fname
            if not path.exists():
                continue
            n = _load_file(conn, path, table)
            conn.commit()
            total += n
            print(f"[import] {fname:24} -> {table:24} {n:>7} rows")
        print(f"[import] done — {total} rows loaded")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: python -m app.integration.import_csv <folder> [--truncate]")
        raise SystemExit(1)
    run(args[0], truncate="--truncate" in args)
