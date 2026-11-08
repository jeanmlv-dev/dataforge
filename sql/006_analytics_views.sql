
-- ============================================================
-- DataForge | SQL Analytics Layer
-- File: 006_analytics_views.sql
-- Description: Reusable analytical views
-- ============================================================

-- View 1: Descriptive statistics by study group

CREATE OR REPLACE VIEW vw_group_statistics AS
SELECT
    study_group,
    COUNT(*) AS total_records,
    ROUND(AVG(patient_age)::numeric, 2) AS mean_age,
    MIN(patient_age) AS min_age,
    MAX(patient_age) AS max_age,
    ROUND(AVG(measurement)::numeric, 2) AS mean_measurement,
    ROUND(STDDEV_SAMP(measurement)::numeric, 2)
        AS sd_measurement,
    MIN(measurement) AS min_measurement,
    MAX(measurement) AS max_measurement
FROM patient_measurements
GROUP BY study_group;


-- View 2: Age group distribution

CREATE OR REPLACE VIEW vw_age_group_distribution AS
WITH distribution AS (
    SELECT
        study_group,
        age_group,
        COUNT(*) AS total_records
    FROM patient_measurements
    GROUP BY study_group, age_group
)
SELECT
    study_group,
    age_group,
    total_records,
    SUM(total_records) OVER (
        PARTITION BY study_group
    ) AS group_total,
    ROUND(
        100.0 * total_records /
        NULLIF(
            SUM(total_records) OVER (
                PARTITION BY study_group
            ),
            0
        ),
        2
    ) AS percentage_within_group
FROM distribution;


-- View 3: Group comparisons

CREATE OR REPLACE VIEW vw_group_comparison AS
WITH group_statistics AS (
    SELECT
        study_group,
        COUNT(*) AS total_records,
        AVG(measurement) AS mean_measurement
    FROM patient_measurements
    GROUP BY study_group
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
FROM group_statistics a
CROSS JOIN group_statistics b
WHERE a.study_group = 'A'
  AND b.study_group = 'B';
