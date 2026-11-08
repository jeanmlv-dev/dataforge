"""End-to-end DataForge ETL pipeline with execution observability."""

import argparse
import json
import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dataforge.ingestion.csv_reader import read_csv
from dataforge.storage.postgres import upsert_patient_data_with_metrics
from dataforge.transformation.cleaning import transform_patient_data
from dataforge.validation.schemas import validate_patient_data

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT_DIR = PROJECT_ROOT / "reports" / "pipeline_runs"

STAGES = ("ingestion", "validation", "transformation", "storage")


def utc_now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(UTC).isoformat()


def save_execution_report(report: dict, report_dir: Path) -> Path:
    """Persist one JSON report per pipeline execution."""
    report_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{report['run_id']}.json"
    output_path = report_dir / filename
    temporary_path = report_dir / f".{filename}.tmp"

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(report, file, indent=2, ensure_ascii=False)
            file.write("\n")

        temporary_path.replace(output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path


def run_pipeline(
    input_path: str | Path,
    report_dir: str | Path | None = None,
) -> int:
    """Run ETL and save an execution report.

    Returns the number of processed records to preserve the original API.
    Raises the original exception when a pipeline stage fails.
    """
    start_time = time.perf_counter()
    run_id = f"{datetime.now(UTC):%Y%m%dT%H%M%S}_{uuid.uuid4().hex[:12]}"
    report_path = Path(report_dir) if report_dir is not None else DEFAULT_REPORT_DIR

    report = {
        "run_id": run_id,
        "status": "running",
        "input_file": str(input_path),
        "started_at": utc_now(),
        "finished_at": None,
        "duration_seconds": None,
        "records_read": 0,
        "records_validated": 0,
        "records_rejected": 0,
        "records_processed": 0,
        "records_inserted": 0,
        "records_updated": 0,
        "rejection_scope": "batch",
        "stage_durations": {stage: None for stage in STAGES},
        "error": None,
    }

    stage = "ingestion"
    stage_start = start_time

    logger.info(
        "Starting DataForge pipeline | run_id=%s | input=%s",
        run_id,
        input_path,
    )

    try:
        # Stage 1: Ingestion
        dataframe = read_csv(input_path)
        report["records_read"] = len(dataframe)
        report["stage_durations"]["ingestion"] = round(
            time.perf_counter() - stage_start, 6
        )

        logger.info(
            "Ingestion completed | records_read=%d",
            report["records_read"],
        )

        # Stage 2: Validation
        stage = "validation"
        stage_start = time.perf_counter()

        validate_patient_data(dataframe)

        report["records_validated"] = len(dataframe)
        report["stage_durations"]["validation"] = round(
            time.perf_counter() - stage_start, 6
        )

        logger.info(
            "Validation completed | status=success | records_validated=%d",
            report["records_validated"],
        )

        # Stage 3: Transformation
        stage = "transformation"
        stage_start = time.perf_counter()

        transformed = transform_patient_data(dataframe)

        report["stage_durations"]["transformation"] = round(
            time.perf_counter() - stage_start, 6
        )

        logger.info(
            "Transformation completed | records_output=%d",
            len(transformed),
        )

        # Stage 4: Storage
        stage = "storage"
        stage_start = time.perf_counter()

        storage_metrics = upsert_patient_data_with_metrics(transformed)

        report["stage_durations"]["storage"] = round(
            time.perf_counter() - stage_start, 6
        )

        report["records_processed"] = storage_metrics["records_processed"]
        report["records_inserted"] = storage_metrics["records_inserted"]
        report["records_updated"] = storage_metrics["records_updated"]

        logger.info(
            "Storage completed | processed=%d | inserted=%d | updated=%d",
            report["records_processed"],
            report["records_inserted"],
            report["records_updated"],
        )

        report["status"] = "success"

    except Exception as exc:
        report["status"] = "failed"

        if report["stage_durations"][stage] is None:
            report["stage_durations"][stage] = round(
                time.perf_counter() - stage_start, 6
            )

        if stage == "validation":
            # Pandera currently validates the batch as a whole.
            # This is not a row-level rejection count.
            report["records_rejected"] = report["records_read"]

        report["error"] = {
            "stage": stage,
            "type": type(exc).__name__,
            "message": str(exc),
        }

        logger.exception(
            "Pipeline failed | run_id=%s | stage=%s",
            run_id,
            stage,
        )

        raise

    finally:
        report["finished_at"] = utc_now()
        report["duration_seconds"] = round(time.perf_counter() - start_time, 6)

        try:
            saved_path = save_execution_report(report, report_path)
            logger.info("Execution report saved | path=%s", saved_path)
        except Exception:
            logger.exception(
                "Failed to save execution report | run_id=%s",
                run_id,
            )
            if report["status"] == "success":
                raise

        logger.info(
            "Pipeline completed | run_id=%s | status=%s | "
            "records_read=%d | records_processed=%d | "
            "records_inserted=%d | records_updated=%d | "
            "duration_seconds=%.3f",
            run_id,
            report["status"],
            report["records_read"],
            report["records_processed"],
            report["records_inserted"],
            report["records_updated"],
            report["duration_seconds"],
        )

    return report["records_processed"]


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description="Run the DataForge ETL pipeline.")

    parser.add_argument(
        "--input",
        default="data/sample/example.csv",
        help="Path to input CSV file",
    )

    parser.add_argument(
        "--report-dir",
        default=None,
        help="Directory for execution JSON reports",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    run_pipeline(args.input, report_dir=args.report_dir)


if __name__ == "__main__":
    main()
