"""End-to-end DataForge data pipeline."""

import argparse
import logging
from pathlib import Path

from dataforge.ingestion.csv_reader import read_csv
from dataforge.storage.postgres import upsert_patient_data
from dataforge.transformation.cleaning import transform_patient_data
from dataforge.validation.schemas import validate_patient_data

logger = logging.getLogger(__name__)


def run_pipeline(input_path: str | Path) -> int:
    """Ingest, validate, transform and store patient data."""
    logger.info("Starting DataForge pipeline")

    dataframe = read_csv(input_path)
    logger.info("Ingested %d records", len(dataframe))

    validate_patient_data(dataframe)
    logger.info("Data validation completed")

    transformed = transform_patient_data(dataframe)
    logger.info("Data transformation completed")

    processed = upsert_patient_data(transformed)
    logger.info("Stored %d records in PostgreSQL", processed)

    return processed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the DataForge ETL pipeline.")
    parser.add_argument(
        "--input",
        default="data/sample/example.csv",
        help="Path to input CSV file",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    run_pipeline(args.input)


if __name__ == "__main__":
    main()
