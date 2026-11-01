import pandas as pd
import pytest

from dataforge.storage.postgres import (
    get_connection,
    upsert_patient_data,
)


@pytest.fixture
def sample_data():
    return pd.DataFrame(
        {
            "record_id": [900001, 900002],
            "patient_age": [25, 45],
            "study_group": ["A", "B"],
            "measurement": [2.0, 3.0],
            "age_group": ["18-39", "40-64"],
            "measurement_squared": [4.0, 9.0],
        }
    )


def test_postgres_upsert_is_idempotent(sample_data):
    record_ids = sample_data["record_id"].tolist()

    try:
        inserted = upsert_patient_data(sample_data)
        assert inserted == 2

        # Running the same load twice must not create duplicates.
        upsert_patient_data(sample_data)

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

        # An existing record must be updated.
        updated_data = sample_data.copy()
        updated_data.loc[0, "measurement"] = 5.0
        updated_data.loc[0, "measurement_squared"] = 25.0

        upsert_patient_data(updated_data)

        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    SELECT measurement, measurement_squared
                    FROM patient_measurements
                    WHERE record_id = %s
                    """,
                (900001,),
            )
            assert cursor.fetchone() == (5.0, 25.0)

    finally:
        # Remove only the records created for this test.
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                    DELETE FROM patient_measurements
                    WHERE record_id = ANY(%s)
                    """,
                (record_ids,),
            )
