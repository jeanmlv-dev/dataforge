
CREATE TABLE IF NOT EXISTS patient_measurements (
    record_id INTEGER PRIMARY KEY,
    patient_age INTEGER NOT NULL
        CHECK (patient_age BETWEEN 0 AND 120),
    study_group VARCHAR(1) NOT NULL
        CHECK (study_group IN ('A', 'B')),
    measurement DOUBLE PRECISION NOT NULL
        CHECK (measurement >= 0),
    age_group VARCHAR(5) NOT NULL,
    measurement_squared DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
