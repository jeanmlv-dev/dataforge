"""End-to-end DataForge data pipeline."""

import argparse
import logging
import time
from pathlib import Path

from dataforge.ingestion.csv_reader import read_csv
from dataforge.storage.postgres import upsert_patient_data
from dataforge.transformation.cleaning import transform_patient_data
from dataforge.validation.schemas import validate_patient_data

logger = logging.getLogger(__name__)


def run_pipeline(input_path: str | Path) -> int:
    """Ingest, validate, transform and store patient data."""
    start_time = time.perf_counter()
    stage = "ingestion"

    logger.info("Starting DataForge pipeline | input=%s", input_path)

    try:
        dataframe = read_csv(input_path)
        records_read = len(dataframe)

        logger.info(
            "Ingestion completed | records_read=%d",
            records_read,
        )

        stage = "validation"
        validate_patient_data(dataframe)
        logger.info("Validation completed | status=success")

        stage = "transformation"
        transformed = transform_patient_data(dataframe)

        logger.info(
            "Transformation completed | records_output=%d",
            len(transformed),
        )

        stage = "storage"
        processed = upsert_patient_data(transformed)

        logger.info(
            "Storage completed | records_processed=%d",
            processed,
        )

    except Exception:
        duration = time.perf_counter() - start_time

        logger.exception(
            "Pipeline failed | stage=%s | duration_seconds=%.3f",
            stage,
            duration,
        )
        raise

    duration = time.perf_counter() - start_time

    logger.info(
        "Pipeline completed | status=success | "
        "records_read=%d | records_processed=%d | "
        "duration_seconds=%.3f",
        records_read,
        processed,
        duration,
    )

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
