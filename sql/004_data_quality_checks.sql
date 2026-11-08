
-- ============================================================
-- DataForge | SQL Analytics Layer
-- File: 004_data_quality_checks.sql
-- Description: Data quality checks for patient_measurements
-- ============================================================

WITH quality_metrics AS (
    SELECT
        -- Total number of records
        COUNT(*) AS total_records,

        -- Duplicate record identifiers
        COUNT(*) - COUNT(DISTINCT record_id)
            AS duplicate_record_ids,

        -- Records containing missing values
        COUNT(*) FILTER (
            WHERE record_id IS NULL
               OR patient_age IS NULL
               OR study_group IS NULL
               OR measurement IS NULL
               OR age_group IS NULL
               OR measurement_squared IS NULL
        ) AS records_with_missing_values,

        -- Invalid patient ages
        COUNT(*) FILTER (
            WHERE patient_age < 0
               OR patient_age > 120
        ) AS invalid_age_records,

        -- Inconsistent squared measurements
        -- Floating-point tolerance: 0.000001
        COUNT(*) FILTER (
            WHERE measurement_squared IS NOT NULL
              AND measurement IS NOT NULL
              AND ABS(
                  measurement_squared -
                  (measurement * measurement)
              ) > 0.000001
        ) AS inconsistent_squared_measurements

    FROM patient_measurements
)

SELECT
    total_records,
    duplicate_record_ids,
    records_with_missing_values,
    invalid_age_records,
    inconsistent_squared_measurements,

    CASE
        WHEN duplicate_record_ids = 0
         AND records_with_missing_values = 0
         AND invalid_age_records = 0
         AND inconsistent_squared_measurements = 0
        THEN 'PASS'
        ELSE 'FAIL'
    END AS quality_status

FROM quality_metrics;
