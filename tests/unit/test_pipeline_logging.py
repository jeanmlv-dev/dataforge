"""Unit tests for DataForge pipeline observability."""

import logging

import pandas as pd
import pytest

from dataforge import pipeline


def test_pipeline_logs_success(monkeypatch, caplog):
    """Verify successful execution logs and metrics."""
    dataframe = pd.DataFrame(
        {
            "record_id": [1, 2],
            "patient_age": [25, 45],
            "study_group": ["A", "B"],
            "measurement": [2.0, 3.0],
        }
    )

    monkeypatch.setattr(pipeline, "read_csv", lambda path: dataframe)
    monkeypatch.setattr(pipeline, "validate_patient_data", lambda df: None)
    monkeypatch.setattr(pipeline, "transform_patient_data", lambda df: df)
    monkeypatch.setattr(pipeline, "upsert_patient_data", lambda df: len(df))

    with caplog.at_level(logging.INFO):
        result = pipeline.run_pipeline("sample.csv")

    assert result == 2
    assert "Ingestion completed | records_read=2" in caplog.text
    assert "Validation completed | status=success" in caplog.text
    assert "Transformation completed | records_output=2" in caplog.text
    assert "Storage completed | records_processed=2" in caplog.text
    assert "Pipeline completed | status=success" in caplog.text
    assert "duration_seconds=" in caplog.text


def test_pipeline_logs_failure(monkeypatch, caplog):
    """Verify failure logs identify the stage and preserve errors."""

    def raise_validation_error(df):
        raise ValueError("Invalid test data")

    monkeypatch.setattr(
        pipeline,
        "read_csv",
        lambda path: pd.DataFrame({"record_id": [1]}),
    )
    monkeypatch.setattr(
        pipeline,
        "validate_patient_data",
        raise_validation_error,
    )

    with (
        caplog.at_level(logging.ERROR),
        pytest.raises(ValueError, match="Invalid test data"),
    ):
        pipeline.run_pipeline("invalid.csv")

    assert "Pipeline failed | stage=validation" in caplog.text
    assert "duration_seconds=" in caplog.text
    assert "ValueError: Invalid test data" in caplog.text
