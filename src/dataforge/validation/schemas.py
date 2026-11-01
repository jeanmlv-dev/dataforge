import pandas as pd
import pandera.pandas as pa

PATIENT_SCHEMA = pa.DataFrameSchema(
    {
        "record_id": pa.Column(
            int,
            checks=pa.Check.ge(1),
            nullable=False,
            unique=True,
        ),
        "patient_age": pa.Column(
            int,
            checks=pa.Check.in_range(0, 120),
            nullable=False,
        ),
        "study_group": pa.Column(
            str,
            checks=pa.Check.isin(["A", "B"]),
            nullable=False,
        ),
        "measurement": pa.Column(
            float,
            checks=pa.Check.ge(0),
            nullable=False,
            coerce=True,
        ),
    },
    strict=True,
    coerce=False,
)


def validate_patient_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Validate the patient dataset against its data contract."""
    return PATIENT_SCHEMA.validate(dataframe, lazy=True)
