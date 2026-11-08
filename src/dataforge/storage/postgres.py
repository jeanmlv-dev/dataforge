"""PostgreSQL storage and transactional UPSERT operations."""

import logging
import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

COLUMNS = (
    "record_id",
    "patient_age",
    "study_group",
    "measurement",
    "age_group",
    "measurement_squared",
)


def get_connection():
    """Create a PostgreSQL connection using environment settings."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "dataforge"),
        user=os.getenv("POSTGRES_USER", "dataforge"),
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        options="-c statement_timeout=10000 -c lock_timeout=3000",
    )


def _prepare_rows(dataframe: pd.DataFrame) -> list[tuple]:
    """Convert a validated DataFrame into PostgreSQL-compatible rows."""
    missing = set(COLUMNS) - set(dataframe.columns)
    if missing:
        raise ValueError(f"Missing columns for PostgreSQL storage: {sorted(missing)}")

    if dataframe["record_id"].isna().any():
        raise ValueError("record_id cannot contain null values")

    if dataframe["record_id"].duplicated().any():
        raise ValueError("Duplicate record_id values in the input batch")

    return [
        (
            int(row.record_id),
            int(row.patient_age),
            str(row.study_group),
            float(row.measurement),
            str(row.age_group),
            float(row.measurement_squared),
        )
        for row in dataframe.loc[:, COLUMNS].itertuples(index=False)
    ]


def upsert_patient_data_with_metrics(dataframe: pd.DataFrame) -> dict[str, int]:
    """UPSERT a batch and return actual inserted/updated record counts.

    A transaction-scoped advisory lock serializes DataForge writers using
    this function. A temporary table stages the input and lets PostgreSQL
    classify existing versus new record IDs before applying the UPSERT.

    The counts describe database operations, not whether updated values
    differed from their previous values.
    """
    rows = _prepare_rows(dataframe)

    if not rows:
        logger.info("Storage skipped | records_processed=0")
        return {
            "records_processed": 0,
            "records_inserted": 0,
            "records_updated": 0,
        }

    logger.info("Preparing PostgreSQL UPSERT | records=%d", len(rows))

    with get_connection() as connection, connection.cursor() as cursor:
        # Serializes cooperating DataForge writers within this database.
        # Other writers must use the same locking convention.
        cursor.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            (42617, 1001),
        )

        cursor.execute(
            """
                CREATE TEMP TABLE dataforge_upsert_batch (
                    record_id BIGINT PRIMARY KEY,
                    patient_age INTEGER NOT NULL,
                    study_group TEXT NOT NULL,
                    measurement DOUBLE PRECISION NOT NULL,
                    age_group TEXT NOT NULL,
                    measurement_squared DOUBLE PRECISION NOT NULL
                ) ON COMMIT DROP
                """
        )

        cursor.executemany(
            """
                INSERT INTO dataforge_upsert_batch (
                    record_id,
                    patient_age,
                    study_group,
                    measurement,
                    age_group,
                    measurement_squared
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
            rows,
        )

        cursor.execute(
            """
                SELECT COUNT(*)
                FROM dataforge_upsert_batch AS batch
                JOIN patient_measurements AS target
                  ON target.record_id = batch.record_id
                """
        )
        records_updated = int(cursor.fetchone()[0])
        records_inserted = len(rows) - records_updated

        cursor.execute(
            """
                INSERT INTO patient_measurements (
                    record_id,
                    patient_age,
                    study_group,
                    measurement,
                    age_group,
                    measurement_squared
                )
                SELECT
                    record_id,
                    patient_age,
                    study_group,
                    measurement,
                    age_group,
                    measurement_squared
                FROM dataforge_upsert_batch
                WHERE TRUE
                ON CONFLICT (record_id)
                DO UPDATE SET
                    patient_age = EXCLUDED.patient_age,
                    study_group = EXCLUDED.study_group,
                    measurement = EXCLUDED.measurement,
                    age_group = EXCLUDED.age_group,
                    measurement_squared = EXCLUDED.measurement_squared,
                    updated_at = NOW()
                """
        )

        if cursor.rowcount != len(rows):
            raise RuntimeError("UPSERT row count does not match the input batch size")

    metrics = {
        "records_processed": len(rows),
        "records_inserted": records_inserted,
        "records_updated": records_updated,
    }

    logger.info(
        "PostgreSQL transaction committed | "
        "records_processed=%d | records_inserted=%d | records_updated=%d",
        metrics["records_processed"],
        metrics["records_inserted"],
        metrics["records_updated"],
    )

    return metrics


def upsert_patient_data(dataframe: pd.DataFrame) -> int:
    """Insert or update records, preserving the original integer API."""
    metrics = upsert_patient_data_with_metrics(dataframe)
    return metrics["records_processed"]
