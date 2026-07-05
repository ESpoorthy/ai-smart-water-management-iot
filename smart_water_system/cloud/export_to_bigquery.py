"""
Cloud Export – SQLite → BigQuery
=================================
One-off or scheduled script that reads from the existing local SQLite
database and writes it into a BigQuery table.

DESIGN RULES
------------
* Read-only access to the existing DB — no schema changes, no writes.
* Idempotent: uses WRITE_TRUNCATE by default so re-runs don't duplicate rows.
  Pass --mode=WRITE_APPEND for incremental loads (see below).
* Safe for partial runs: each batch is committed separately; progress is
  logged so you can resume.
* No edits to any existing project file.

ENVIRONMENT VARIABLES
---------------------
  GOOGLE_APPLICATION_CREDENTIALS   Path to your GCP service-account JSON key
                                    (or use Application Default Credentials)
  BQ_PROJECT_ID                     GCP project ID               (required)
  BQ_DATASET_ID                     BigQuery dataset name        (default: smart_water)
  BQ_TABLE_ID                       BigQuery table name          (default: sensor_data)
  WATER_DB_PATH                     Local SQLite path            (default: database/water.db)

USAGE
-----
  # Full export (truncate & reload — safe to re-run anytime)
  python cloud/export_to_bigquery.py

  # Incremental: only rows with id > last known max in BQ
  python cloud/export_to_bigquery.py --mode=incremental

  # Dry run: print what would be exported without touching BQ
  python cloud/export_to_bigquery.py --dry-run

  # Custom batch size (default 1000)
  python cloud/export_to_bigquery.py --batch-size=500

NEW DEPENDENCY: google-cloud-bigquery==3.20.1  db-dtypes==1.2.0
  Already noted in requirements-additions.txt.
  pip install google-cloud-bigquery==3.20.1 db-dtypes==1.2.0
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Optional BQ import — degrade gracefully so the file can be imported
# even if the library is not yet installed
# ---------------------------------------------------------------------------
try:
    from google.cloud import bigquery
    from google.cloud.bigquery import SchemaField, LoadJobConfig, WriteDisposition
    _BQ_AVAILABLE = True
except ImportError:
    _BQ_AVAILABLE = False


# ---------------------------------------------------------------------------
# BigQuery schema  (mirrors the existing sensor_data table exactly)
# ---------------------------------------------------------------------------
BQ_SCHEMA = [
    SchemaField("id",          "INTEGER",   mode="REQUIRED",
                description="Auto-increment primary key from SQLite") if _BQ_AVAILABLE else None,
    SchemaField("timestamp",   "TIMESTAMP", mode="REQUIRED",
                description="ISO-8601 timestamp when the reading was stored") if _BQ_AVAILABLE else None,
    SchemaField("flow",        "FLOAT64",   mode="REQUIRED",
                description="Flow rate (L/min)") if _BQ_AVAILABLE else None,
    SchemaField("pressure",    "FLOAT64",   mode="REQUIRED",
                description="Pressure (bar)") if _BQ_AVAILABLE else None,
    SchemaField("ph",          "FLOAT64",   mode="REQUIRED",
                description="pH level") if _BQ_AVAILABLE else None,
    SchemaField("turbidity",   "FLOAT64",   mode="REQUIRED",
                description="Turbidity (NTU)") if _BQ_AVAILABLE else None,
    SchemaField("temperature", "FLOAT64",   mode="REQUIRED",
                description="Temperature (°C)") if _BQ_AVAILABLE else None,
    # Export-only metadata columns — not in the source DB
    SchemaField("exported_at", "TIMESTAMP", mode="NULLABLE",
                description="UTC timestamp when this row was exported") if _BQ_AVAILABLE else None,
]
BQ_SCHEMA = [f for f in BQ_SCHEMA if f is not None]

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
def _cfg(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# ---------------------------------------------------------------------------
# SQLite helpers (read-only)
# ---------------------------------------------------------------------------

def _count_rows(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    n = conn.execute("SELECT COUNT(*) FROM sensor_data").fetchone()[0]
    conn.close()
    return n


def _max_id(db_path: str) -> int:
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT MAX(id) FROM sensor_data").fetchone()
    conn.close()
    return row[0] or 0


def _load_chunk(db_path: str, offset: int, limit: int) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT id, timestamp, flow, pressure, ph, turbidity, temperature
        FROM sensor_data
        ORDER BY id ASC
        LIMIT ? OFFSET ?
        """,
        conn,
        params=(limit, offset),
    )
    conn.close()
    return df


def _load_incremental(db_path: str, since_id: int) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(
        """
        SELECT id, timestamp, flow, pressure, ph, turbidity, temperature
        FROM sensor_data
        WHERE id > ?
        ORDER BY id ASC
        """,
        conn,
        params=(since_id,),
    )
    conn.close()
    return df


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce types and add the exported_at metadata column."""
    df = df.copy()
    # BQ expects UTC timestamps; parse whatever SQLite stored
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["exported_at"] = pd.Timestamp.utcnow()
    for col in ["flow", "pressure", "ph", "turbidity", "temperature"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# BigQuery helpers
# ---------------------------------------------------------------------------

def _get_bq_max_id(client: Any, table_ref: str) -> int:
    """Return the max id currently in BQ, or 0 if the table is empty / absent."""
    try:
        result = client.query(
            f"SELECT COALESCE(MAX(id), 0) AS max_id FROM `{table_ref}`"
        ).result()
        return list(result)[0]["max_id"]
    except Exception:
        return 0


def _upload_df(
    client: Any,
    df: pd.DataFrame,
    table_ref: str,
    write_disposition: str,
    schema: list,
) -> None:
    job_config = LoadJobConfig(
        schema=schema,
        write_disposition=write_disposition,
        # Let BQ auto-detect timestamp strings
        autodetect=False,
    )
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # wait for completion; raises on error


# ---------------------------------------------------------------------------
# Main export logic
# ---------------------------------------------------------------------------

def export(
    mode: str = "truncate",
    batch_size: int = 1000,
    dry_run: bool = False,
    db_path: str | None = None,
    project_id: str | None = None,
    dataset_id: str | None = None,
    table_id: str | None = None,
) -> dict[str, Any]:
    """
    Export sensor_data from SQLite to BigQuery.

    Parameters
    ----------
    mode        : "truncate"    – full reload (safe to re-run)
                  "incremental" – only rows with id > BQ max id
    batch_size  : rows per BQ upload batch
    dry_run     : if True, load from DB and report counts without uploading
    db_path     : override WATER_DB_PATH env var
    project_id  : override BQ_PROJECT_ID env var
    dataset_id  : override BQ_DATASET_ID env var
    table_id    : override BQ_TABLE_ID env var

    Returns
    -------
    dict with keys: rows_exported, batches, duration_s, status
    """
    start = datetime.utcnow()

    # ── Resolve config ────────────────────────────────────────────────────
    db_path    = db_path    or _cfg("WATER_DB_PATH",  "database/water.db")
    project_id = project_id or _cfg("BQ_PROJECT_ID")
    dataset_id = dataset_id or _cfg("BQ_DATASET_ID",  "smart_water")
    table_id   = table_id   or _cfg("BQ_TABLE_ID",    "sensor_data")

    if not dry_run and not _BQ_AVAILABLE:
        raise RuntimeError(
            "google-cloud-bigquery is not installed.\n"
            "Run: pip install google-cloud-bigquery==3.20.1 db-dtypes==1.2.0"
        )

    if not dry_run and not project_id:
        raise ValueError(
            "BQ_PROJECT_ID environment variable is not set. "
            "Export: set BQ_PROJECT_ID=your-gcp-project-id"
        )

    table_ref = f"{project_id}.{dataset_id}.{table_id}"

    # ── Count source rows ─────────────────────────────────────────────────
    total_local = _count_rows(db_path)
    print(f"[BigQuery Export] Source DB: {db_path}")
    print(f"[BigQuery Export] Total rows in local DB: {total_local:,}")
    print(f"[BigQuery Export] Target table: {table_ref}")
    print(f"[BigQuery Export] Mode: {mode}  |  Batch size: {batch_size}")
    if dry_run:
        print("[BigQuery Export] DRY RUN — no data will be uploaded.")

    # ── Connect BQ ────────────────────────────────────────────────────────
    client = None
    if not dry_run:
        client = bigquery.Client(project=project_id)
        # Ensure dataset exists
        dataset_obj = bigquery.Dataset(f"{project_id}.{dataset_id}")
        dataset_obj.location = "US"
        client.create_dataset(dataset_obj, exists_ok=True)
        print(f"[BigQuery Export] Dataset '{dataset_id}' ready.")

    # ── Load data ──────────────────────────────────────────────────────────
    if mode == "incremental":
        since_id = _get_bq_max_id(client, table_ref) if client else 0
        print(f"[BigQuery Export] Incremental: loading rows with id > {since_id}")
        df_all = _load_incremental(db_path, since_id)
        write_disp = WriteDisposition.WRITE_APPEND if _BQ_AVAILABLE else "WRITE_APPEND"
    else:
        df_all = pd.concat(
            [_load_chunk(db_path, i, batch_size)
             for i in range(0, total_local, batch_size)],
            ignore_index=True,
        ) if total_local > 0 else pd.DataFrame()
        write_disp = WriteDisposition.WRITE_TRUNCATE if _BQ_AVAILABLE else "WRITE_TRUNCATE"

    if df_all.empty:
        print("[BigQuery Export] No new rows to export.")
        elapsed = (datetime.utcnow() - start).total_seconds()
        return {"rows_exported": 0, "batches": 0,
                "duration_s": elapsed, "status": "no_new_rows"}

    df_all = _prepare_df(df_all)
    total_export = len(df_all)
    print(f"[BigQuery Export] Rows to export: {total_export:,}")

    if dry_run:
        print("[BigQuery Export] Dry run complete. Sample (first 3 rows):")
        print(df_all.head(3).to_string())
        elapsed = (datetime.utcnow() - start).total_seconds()
        return {"rows_exported": total_export, "batches": 0,
                "duration_s": elapsed, "status": "dry_run"}

    # ── Upload in batches ─────────────────────────────────────────────────
    batches = 0
    rows_uploaded = 0
    for start_idx in range(0, total_export, batch_size):
        chunk = df_all.iloc[start_idx: start_idx + batch_size]
        # First batch uses the configured disposition;
        # subsequent batches always append so we don't overwrite prior work
        disp = write_disp if start_idx == 0 else (
            WriteDisposition.WRITE_APPEND if _BQ_AVAILABLE else "WRITE_APPEND"
        )
        _upload_df(client, chunk, table_ref, disp, BQ_SCHEMA)
        rows_uploaded += len(chunk)
        batches += 1
        pct = rows_uploaded / total_export * 100
        print(f"[BigQuery Export]   Batch {batches}: "
              f"{rows_uploaded:,}/{total_export:,} rows ({pct:.0f}%)")

    elapsed = (datetime.utcnow() - start).total_seconds()
    print(f"\n[BigQuery Export] ✅ Done — {rows_uploaded:,} rows in "
          f"{batches} batches ({elapsed:.1f}s)")
    print(f"[BigQuery Export] Table: https://console.cloud.google.com/bigquery"
          f"?project={project_id}&ws=!1m5!1m4!4m3!1s{project_id}!2s{dataset_id}!3s{table_id}")

    return {
        "rows_exported": rows_uploaded,
        "batches":       batches,
        "duration_s":    elapsed,
        "status":        "success",
        "table":         table_ref,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Export smart water sensor data from SQLite to BigQuery."
    )
    p.add_argument(
        "--mode",
        choices=["truncate", "incremental"],
        default="truncate",
        help=(
            "truncate (default): full reload, safe to re-run. "
            "incremental: only new rows since last export."
        ),
    )
    p.add_argument(
        "--batch-size", type=int, default=1000,
        help="Number of rows per BigQuery upload batch (default: 1000).",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Read from DB and show counts/sample without uploading to BQ.",
    )
    p.add_argument("--db-path",    default=None, help="Override WATER_DB_PATH.")
    p.add_argument("--project-id", default=None, help="Override BQ_PROJECT_ID.")
    p.add_argument("--dataset-id", default=None, help="Override BQ_DATASET_ID.")
    p.add_argument("--table-id",   default=None, help="Override BQ_TABLE_ID.")
    return p.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    result = export(
        mode=args.mode,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        db_path=args.db_path,
        project_id=args.project_id,
        dataset_id=args.dataset_id,
        table_id=args.table_id,
    )
    sys.exit(0 if result["status"] in ("success", "dry_run", "no_new_rows") else 1)
