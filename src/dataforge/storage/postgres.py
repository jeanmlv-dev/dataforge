import os
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv

# Load local environment configuration
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


def get_connection():
    """Create a PostgreSQL connection from environment settings."""
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        dbname=os.getenv("POSTGRES_DB", "dataforge"),
        user=os.getenv("POSTGRES_USER", "dataforge"),
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=5,
        options="-c statement_timeout=10000 -c lock_timeout=3000",
    )


def upsert_patient_data(dataframe: pd.DataFrame) -> int:
    """Insert or update patient records without creating duplicates."""
    query = """
        INSERT INTO patient_measurements (
            record_id,
            patient_age,
            study_group,
            measurement,
            age_group,
            measurement_squared
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (record_id)
        DO UPDATE SET
            patient_age = EXCLUDED.patient_age,
            study_group = EXCLUDED.study_group,
            measurement = EXCLUDED.measurement,
            age_group = EXCLUDED.age_group,
            measurement_squared = EXCLUDED.measurement_squared,
            updated_at = NOW()
    """

    rows = [
        (
            int(row.record_id),
            int(row.patient_age),
            str(row.study_group),
            float(row.measurement),
            str(row.age_group),
            float(row.measurement_squared),
        )
        for row in dataframe.itertuples(index=False)
    ]

    print(f"[DataForge] Preparing to insert {len(rows)} records", flush=True)

    with get_connection() as connection:
        print("[DataForge] PostgreSQL connection established", flush=True)

        with connection.cursor() as cursor:
            print("[DataForge] Executing UPSERT", flush=True)
            cursor.executemany(query, rows)
            print("[DataForge] UPSERT executed successfully", flush=True)

    print("[DataForge] Transaction committed", flush=True)

    return len(rows)
