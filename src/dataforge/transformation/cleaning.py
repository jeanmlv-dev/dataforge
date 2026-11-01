import pandas as pd


def transform_patient_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Transform validated patient data into analysis-ready data."""

    result = dataframe.copy()

    result["study_group"] = result["study_group"].astype("category")

    result["age_group"] = pd.cut(
        result["patient_age"],
        bins=[-1, 17, 39, 59, 120],
        labels=["0-17", "18-39", "40-59", "60+"],
    )

    result["measurement_squared"] = result["measurement"] ** 2

    return result
