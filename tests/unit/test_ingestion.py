import pandas as pd
import pytest

from dataforge.ingestion.csv_reader import read_csv


def test_read_csv_returns_dataframe(tmp_path):
    csv_file = tmp_path / "sample.csv"
    csv_file.write_text(
        "record_id,value\n1,10\n2,20\n",
        encoding="utf-8",
    )

    result = read_csv(csv_file)

    assert isinstance(result, pd.DataFrame)
    assert result.shape == (2, 2)
    assert result["record_id"].tolist() == [1, 2]


def test_read_csv_raises_error_for_missing_file(tmp_path):
    missing_file = tmp_path / "missing.csv"

    with pytest.raises(FileNotFoundError):
        read_csv(missing_file)


def test_read_csv_rejects_empty_dataset(tmp_path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text(
        "record_id,value\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="no data rows"):
        read_csv(csv_file)
