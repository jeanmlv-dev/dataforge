import pandas as pd
import pandera.errors as pa_errors
import pytest

from dataforge.validation.schemas import validate_patient_data


@pytest.fixture
def valid_data():
    return pd.DataFrame(
        {
            "record_id": [1, 2, 3],
            "patient_age": [34, 45, 29],
            "study_group": ["A", "B", "A"],
            "measurement": [12.5, 15.2, 11.8],
        }
    )


def test_valid_data_passes_validation(valid_data):
    result = validate_patient_data(valid_data)

    assert len(result) == 3


def test_duplicate_record_id_fails(valid_data):
    valid_data.loc[1, "record_id"] = 1

    with pytest.raises(pa_errors.SchemaErrors):
        validate_patient_data(valid_data)


def test_invalid_age_fails(valid_data):
    valid_data.loc[0, "patient_age"] = 150

    with pytest.raises(pa_errors.SchemaErrors):
        validate_patient_data(valid_data)


def test_invalid_study_group_fails(valid_data):
    valid_data.loc[0, "study_group"] = "C"

    with pytest.raises(pa_errors.SchemaErrors):
        validate_patient_data(valid_data)


def test_missing_measurement_fails(valid_data):
    valid_data.loc[0, "measurement"] = None

    with pytest.raises(pa_errors.SchemaErrors):
        validate_patient_data(valid_data)


def test_unexpected_column_fails(valid_data):
    valid_data["unexpected"] = "extra"

    with pytest.raises(pa_errors.SchemaErrors):
        validate_patient_data(valid_data)
