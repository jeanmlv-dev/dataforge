
-- ============================================================
-- DataForge | SQL Analytics Layer
-- File: 005_group_comparisons.sql
-- Description: Comparison of study group measurements
-- ============================================================

WITH group_statistics AS (
    SELECT
        study_group,
        COUNT(*) AS total_records,
        AVG(measurement) AS mean_measurement,
        STDDEV_SAMP(measurement) AS sd_measurement
    FROM patient_measurements
    GROUP BY study_group
),
group_a AS (
    SELECT *
    FROM group_statistics
    WHERE study_group = 'A'
),
group_b AS (
    SELECT *
    FROM group_statistics
    WHERE study_group = 'B'
)
SELECT
    a.total_records AS group_a_records,
    b.total_records AS group_b_records,

    ROUND(a.mean_measurement::numeric, 2)
        AS group_a_mean,

    ROUND(b.mean_measurement::numeric, 2)
        AS group_b_mean,

    ROUND(
        (b.mean_measurement - a.mean_measurement)::numeric,
        2
    ) AS absolute_difference,

    ROUND(
        (
            100.0 *
            (b.mean_measurement - a.mean_measurement) /
            NULLIF(a.mean_measurement, 0)
        )::numeric,
        2
    ) AS percentage_difference

FROM group_a a
CROSS JOIN group_b b;
