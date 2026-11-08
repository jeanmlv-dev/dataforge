"""Integration tests for the DataForge SQL analytics layer."""

from pathlib import Path

import pytest

from dataforge.storage.postgres import get_connection

PROJECT_ROOT = Path(__file__).resolve().parents[2]

ANALYTICS_VIEWS_SQL = PROJECT_ROOT / "sql" / "006_analytics_views.sql"

EXPECTED_VIEWS = {
    "vw_group_statistics": {
        "study_group",
        "total_records",
        "mean_age",
        "min_age",
        "max_age",
        "mean_measurement",
        "sd_measurement",
        "min_measurement",
        "max_measurement",
    },
    "vw_age_group_distribution": {
        "study_group",
        "age_group",
        "total_records",
        "group_total",
        "percentage_within_group",
    },
    "vw_group_comparison": {
        "group_a_records",
        "group_b_records",
        "group_a_mean",
        "group_b_mean",
        "absolute_difference",
        "percentage_difference",
    },
}


@pytest.fixture(scope="module")
def analytics_connection():
    """Connect to PostgreSQL and initialize analytics views."""

    sql = ANALYTICS_VIEWS_SQL.read_text(encoding="utf-8")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)

        connection.commit()

        yield connection


@pytest.mark.parametrize(
    "view_name",
    sorted(EXPECTED_VIEWS),
)
def test_analytics_view_exists(
    analytics_connection,
    view_name,
):
    """Verify that each analytics view exists."""

    with analytics_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.views
                WHERE table_schema = 'public'
                  AND table_name = %s
            )
            """,
            (view_name,),
        )

        assert cursor.fetchone()[0] is True


@pytest.mark.parametrize(
    "view_name",
    sorted(EXPECTED_VIEWS),
)
def test_analytics_view_columns(
    analytics_connection,
    view_name,
):
    """Verify that each view exposes its expected columns."""

    with analytics_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            """,
            (view_name,),
        )

        actual_columns = {row[0] for row in cursor.fetchall()}

    assert EXPECTED_VIEWS[view_name] <= actual_columns


def test_group_statistics_counts(analytics_connection):
    """Verify that group totals match the source table."""

    with analytics_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT COALESCE(SUM(total_records), 0)
            FROM vw_group_statistics
            """
        )
        view_total = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM patient_measurements
            """
        )
        source_total = cursor.fetchone()[0]

    assert view_total == source_total


def test_age_distribution_percentages(analytics_connection):
    """Verify age-group percentages sum to 100 per group."""

    with analytics_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                study_group,
                SUM(percentage_within_group)
            FROM vw_age_group_distribution
            GROUP BY study_group
            """
        )

        results = cursor.fetchall()

    for study_group, percentage in results:
        assert abs(float(percentage) - 100.0) <= 0.01, (
            f"Invalid percentage for group {study_group}"
        )


def test_group_comparison_difference(analytics_connection):
    """Verify the difference between group means."""

    with analytics_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                group_a_mean,
                group_b_mean,
                absolute_difference
            FROM vw_group_comparison
            """
        )

        result = cursor.fetchone()

    if result is None:
        pytest.skip("Both study groups A and B are required")

    mean_a, mean_b, difference = result

    assert abs(float(difference) - (float(mean_b) - float(mean_a))) <= 0.02
