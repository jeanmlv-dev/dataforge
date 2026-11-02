import pandas as pd

from dataforge.pipeline import run_pipeline
from dataforge.storage.postgres import get_connection


def test_pipeline_end_to_end(tmp_path):
    record_ids = [990001, 990002]

    input_data = pd.DataFrame(
        {
            "record_id": record_ids,
            "patient_age": [25, 45],
            "study_group": ["A", "B"],
            "measurement": [2.0, 3.0],
        }
    )

    csv_path = tmp_path / "patients.csv"
    input_data.to_csv(csv_path, index=False)

    try:
        processed = run_pipeline(csv_path)
        assert processed == 2

        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT record_id, patient_age, study_group,
                       measurement, age_group, measurement_squared
                FROM patient_measurements
                WHERE record_id = ANY(%s)
                ORDER BY record_id
                """,
                (record_ids,),
            )
            rows = cursor.fetchall()

        assert rows == [
            (990001, 25, "A", 2.0, "18-39", 4.0),
            (990002, 45, "B", 3.0, "40-59", 9.0),
        ]

        # Re-running the same pipeline must not duplicate records.
        run_pipeline(csv_path)

        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM patient_measurements
                WHERE record_id = ANY(%s)
                """,
                (record_ids,),
            )
            assert cursor.fetchone()[0] == 2

    finally:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM patient_measurements
                WHERE record_id = ANY(%s)
                """,
                (record_ids,),
            )
