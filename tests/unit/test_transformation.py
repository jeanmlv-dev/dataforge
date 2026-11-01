import pandas as pd

from dataforge.transformation.cleaning import transform_patient_data


def test_transformation_creates_expected_columns():
    dataframe = pd.DataFrame(
        {
            "record_id": [1, 2, 3],
            "patient_age": [17, 34, 65],
            "study_group": ["A", "B", "A"],
            "measurement": [2.0, 3.0, 4.0],
        }
    )

    result = transform_patient_data(dataframe)

    assert "age_group" in result.columns
    assert "measurement_squared" in result.columns
    assert result["age_group"].astype(str).tolist() == [
        "0-17",
        "18-39",
        "60+",
    ]
    assert result["measurement_squared"].tolist() == [
        4.0,
        9.0,
        16.0,
    ]


def test_transformation_does_not_modify_input():
    dataframe = pd.DataFrame(
        {
            "record_id": [1],
            "patient_age": [34],
            "study_group": ["A"],
            "measurement": [2.0],
        }
    )

    original = dataframe.copy(deep=True)

    transform_patient_data(dataframe)

    pd.testing.assert_frame_equal(dataframe, original)


def test_transformation_is_deterministic():
    dataframe = pd.DataFrame(
        {
            "record_id": [1],
            "patient_age": [45],
            "study_group": ["B"],
            "measurement": [5.0],
        }
    )

    first_result = transform_patient_data(dataframe)
    second_result = transform_patient_data(dataframe)

    pd.testing.assert_frame_equal(first_result, second_result)
