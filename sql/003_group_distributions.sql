
-- DataForge | Analytics Layer
-- Distribution by study group and age group

WITH distribution AS (
    SELECT
        study_group,
        age_group,
        COUNT(*) AS total_records
    FROM patient_measurements
    GROUP BY
        study_group,
        age_group
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
FROM distribution
ORDER BY study_group, age_group;
