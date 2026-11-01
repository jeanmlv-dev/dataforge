from pathlib import Path

import pandas as pd


def read_csv(
    file_path: str | Path,
    *,
    encoding: str = "utf-8",
    separator: str = ",",
) -> pd.DataFrame:
    """Read a CSV file and return its contents as a DataFrame."""

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {path}")

    try:
        dataframe = pd.read_csv(
            path,
            encoding=encoding,
            sep=separator,
        )
    except (pd.errors.ParserError, UnicodeError) as exc:
        raise ValueError(f"Unable to read CSV file: {path}") from exc

    if dataframe.empty:
        raise ValueError(f"CSV file contains no data rows: {path}")

    return dataframe
