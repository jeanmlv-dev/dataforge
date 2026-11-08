
-- DataForge | Analytics Layer
-- Descriptive statistics by study group

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
GROUP BY study_group
ORDER BY study_group;
