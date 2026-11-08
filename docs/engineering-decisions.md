# DataForge — Engineering Decisions

## 1. Overview

DataForge is a reproducible Python and SQL data engineering project designed to demonstrate practical engineering decisions across the complete Extract, Transform, Load (ETL) lifecycle.

The project processes synthetic patient-measurement data through a modular pipeline, validates data quality, applies transformations, and persists records in PostgreSQL.

The architecture prioritizes:

- **Reproducibility:** Consistent execution across local and containerized environments.
- **Data integrity:** Validation before persistence and database-level constraints.
- **Idempotency:** Repeated executions do not create duplicate records.
- **Maintainability:** Separation of responsibilities across pipeline components.
- **Observability:** Structured execution metrics, logs, and JSON reports.
- **Testability:** Automated unit, integration, and end-to-end testing.
- **Analytical usability:** SQL queries and views that expose meaningful insights from stored data.

This document explains the main architectural decisions, their rationale, trade-offs, and potential improvements.

---

## 2. Technology Selection

### 2.1 Python for ETL Orchestration

**Decision:** Use Python as the primary programming language for ingestion, validation, transformation, and pipeline orchestration.

**Rationale:**

Python provides a mature ecosystem for data processing, database integration, automated testing, and application packaging.

Its modular structure also supports independent testing and future extensions.

**Trade-offs:**

- Python is not optimized for very large distributed workloads.
- In-memory processing can become a limitation as dataset size increases.

**Future improvement:** Evaluate chunked ingestion, incremental processing, or distributed processing frameworks for larger datasets.

### 2.2 Pandas for Data Processing

**Decision:** Use Pandas for CSV ingestion and transformation.

**Rationale:**

- Provides an expressive DataFrame interface.
- Simplifies tabular data manipulation.
- Integrates with the validation and persistence layers.
- Is appropriate for the project's small synthetic dataset.

**Trade-off:** Pandas generally loads data into memory, making it less suitable for datasets that exceed available RAM.

**Future improvement:** Introduce chunked processing or alternative execution engines when required.

### 2.3 Pandera for Data Validation

**Decision:** Validate input data using Pandera before transformation and persistence.

**Rationale:**

Pandera enables explicit data-quality expectations, including required columns, data types, permitted categorical values, and numerical constraints.

Validation is performed before writing data to PostgreSQL, reducing the risk of storing invalid records.

**Trade-offs:**

- Strict schemas can reject data that might otherwise be recoverable.
- Schema evolution requires coordinated updates to validation rules and tests.

**Current approach:** Invalid input causes the batch to fail before persistence.

**Future improvement:** Introduce configurable row-level rejection and quarantine workflows.

---

## 3. PostgreSQL as the Storage Layer

**Decision:** Use PostgreSQL as the relational database.

**Rationale:**

PostgreSQL provides:

- ACID-compliant transactions.
- Primary keys and relational constraints.
- Native UPSERT support.
- SQL aggregation and analytical views.
- Reliable integration with Python through Psycopg.

The main table, `patient_measurements`, stores source and derived fields, including `record_id`, `patient_age`, `study_group`, `measurement`, `age_group`, and `measurement_squared`.

**Trade-offs:**

- PostgreSQL requires database administration and infrastructure.
- It is not a distributed analytical warehouse.
- Analytical workloads can compete with transactional workloads at scale.

**Future improvement:** Separate analytical workloads from operational storage if data volume or query complexity increases.

---

## 4. Idempotent Data Loading

**Decision:** Implement PostgreSQL UPSERT operations using `ON CONFLICT (record_id) DO UPDATE`.

**Rationale:**

ETL pipelines may be executed repeatedly because of retries, corrections, or scheduled reprocessing.

An idempotent loading strategy ensures that the same `record_id` does not create multiple database rows.

The persistence layer also returns execution metrics distinguishing records classified as inserted and updated.

**Implementation considerations:**

- `record_id` acts as the conflict key.
- Existing records are updated rather than duplicated.
- Database operations execute within a transaction.
- Batch processing provides inserted and updated counts.
- The implementation uses a PostgreSQL transaction-level advisory lock to coordinate cooperating DataForge writers.

**Trade-offs:**

- Existing records can be overwritten when the same identifier is processed again.
- The current design does not retain historical versions of updated measurements.
- Advisory locking requires cooperating writers to follow the same convention.
- Inserted and updated metrics describe database operations, not necessarily changes in business values.

**Future improvement:** Introduce historical tracking, change-data capture, or versioned records if auditability requirements increase.

---

## 5. Modular ETL Architecture

**Decision:** Separate ingestion, validation, transformation, storage, and orchestration into independent modules.

**Project organization:**

```text
src/dataforge/
├── ingestion/
├── validation/
├── transformation/
├── storage/
├── observability/
└── pipeline.py
```

**Rationale:**

Each component has a clearly defined responsibility.

This design improves:

- Code readability.
- Independent unit testing.
- Debugging and error isolation.
- Component reuse.
- Future maintainability.

The `pipeline.py` module coordinates execution without embedding all processing logic in one function.

**Trade-off:** A modular architecture introduces additional files and interfaces compared with a single-script implementation.

**Future improvement:** Introduce formal pipeline interfaces or configurable processing stages if the application grows substantially.

---

## 6. Containerization with Docker

**Decision:** Containerize the Python ETL application and PostgreSQL database using Docker and Docker Compose.

**Rationale:**

Containerization reduces environment inconsistencies and allows the complete application to run without installing Python or PostgreSQL directly on the host operating system.

The solution includes:

- A Python application image defined by `Dockerfile`.
- A PostgreSQL service defined in `compose.yaml`.
- A dedicated ETL service.
- A database health check.
- Persistent PostgreSQL storage through a Docker volume.
- Environment-based configuration.

**Trade-offs:**

- Containers introduce additional operational complexity.
- Docker must be installed on the host.
- Local containerization does not automatically provide production-grade orchestration, high availability, or disaster recovery.

**Future improvement:** Introduce deployment-specific configurations, container image scanning, and a managed database service.

---

## 7. Dependency Management with uv

**Decision:** Use `uv` for Python dependency management and reproducible environments.

**Rationale:**

The project maintains dependencies in `pyproject.toml` and resolves them through the committed `uv.lock` file.

This supports:

- Reproducible dependency installation.
- Consistent development and CI environments.
- Simplified Python project management.
- Faster dependency resolution and installation.

**Trade-off:** Contributors must install `uv` or use the containerized workflow.

**Future improvement:** Establish a scheduled dependency-update process with automated compatibility and security checks.

---

## 8. Observability and Execution Reporting

**Decision:** Implement structured logging and machine-readable JSON execution reports.

**Rationale:**

Successful data processing requires visibility into both results and failures.

The pipeline captures execution information such as:

- Unique execution identifier.
- Start and completion timestamps.
- Overall execution status.
- Input file.
- Total execution duration.
- Stage-level durations.
- Records read and validated.
- Records rejected.
- Records processed.
- Records inserted and updated.
- Processing stage associated with failures.
- Error type and message.

Execution reports are generated under `reports/pipeline_runs/`.

**Important distinction:** The current validation strategy rejects invalid batches rather than supporting partial acceptance of individual records. Consequently, rejected-record metrics must be interpreted according to the implemented batch-level behavior.

**Trade-offs:**

- JSON reports are stored locally rather than in a centralized observability platform.
- The project does not yet implement distributed tracing.
- Local execution reports require appropriate retention and storage management.

**Future improvement:** Integrate centralized logging, metrics collection, dashboards, and execution-history monitoring.

---

## 9. Automated Testing Strategy

**Decision:** Implement multiple levels of automated testing using Pytest.

### Unit Testing

Unit tests verify individual components, including:

- CSV ingestion.
- Data validation.
- Transformation logic.
- Logging and pipeline behavior.
- Error handling.

### Integration Testing

Integration tests verify interactions with PostgreSQL and the SQL analytics layer.

These tests exercise actual database behavior rather than relying exclusively on mocks.

### End-to-End Testing

End-to-end tests execute the complete processing flow:

```text
CSV
  → Ingestion
  → Validation
  → Transformation
  → PostgreSQL
```

They also verify that repeated executions do not create duplicate records and that invalid input is rejected.

**Rationale:**

Different test levels detect different classes of failures.

Unit tests provide fast feedback, while integration and end-to-end tests validate interactions between components.

**Trade-offs:**

- Database integration tests require a running PostgreSQL instance.
- End-to-end tests are slower than isolated unit tests.
- Test data and database state must be managed carefully to maintain repeatability.

**Future improvement:** Expand edge-case coverage, failure-injection testing, and performance regression testing.

---

## 10. Continuous Integration with GitHub Actions

**Decision:** Use GitHub Actions to execute automated quality checks on repository changes.

**Rationale:**

Continuous integration helps identify regressions before changes are accepted into the main development branch.

The CI workflow executes:

- Dependency installation with `uv`.
- Ruff linting.
- Ruff formatting verification.
- Pytest automated tests.
- PostgreSQL-backed integration tests.

The workflow provisions a PostgreSQL service within the GitHub Actions runner, allowing database tests to execute independently of the developer's local computer.

**Trade-offs:**

- CI execution depends on GitHub-hosted runner availability.
- Database integration increases execution time.
- A successful CI run does not guarantee production readiness.

**Future improvement:** Add dependency vulnerability checks, container image scanning, and release-specific validation.

---

## 11. SQL Analytics Layer

**Decision:** Implement a dedicated SQL analytics layer using reusable queries and PostgreSQL views.

**Rationale:**

Persisting validated data is only one part of a data engineering workflow. The stored data must also support downstream analysis.

The analytics layer includes:

| SQL file | Purpose |
|---|---|
| `002_descriptive_statistics.sql` | Aggregate descriptive statistics |
| `003_group_distributions.sql` | Distribution of records across groups |
| `004_data_quality_checks.sql` | Database-level data-quality checks |
| `005_group_comparisons.sql` | Comparative statistics between study groups |
| `006_analytics_views.sql` | Reusable analytical views |

The layer demonstrates aggregation, grouping, conditional calculations, data-quality checks, and reusable database objects.

**Important limitation:** Group comparisons are descriptive and should not be interpreted as evidence of treatment effects or statistically significant differences.

The dataset is synthetic and is not designed for clinical inference.

**Trade-offs:**

- The current SQL queries are designed for a small demonstration dataset.
- Analytical views may need optimization as data volume increases.
- Descriptive summaries do not replace formal statistical modeling.

**Future improvement:** Add indexed analytical access patterns, more advanced SQL queries, and integration with reporting or visualization tools.

---

## 12. Configuration and Security

**Decision:** Store environment-specific configuration outside application source code.

**Rationale:**

Database connection parameters are read from environment variables.

The local `.env` file is excluded from version control, while `.env.example` documents the expected configuration.

Additional safeguards include:

- Parameterized SQL operations.
- Database transactions.
- Controlled database connection settings.
- Synthetic demonstration data.
- Avoidance of hardcoded production credentials.

**Trade-offs and limitations:**

- Local environment files are not a substitute for managed secrets.
- Docker Compose is configured primarily for local development.
- Database credentials and network access require additional controls in production.
- Synthetic data reduces privacy risks but does not eliminate the need for secure engineering practices.

**Future improvement:** Adopt managed secret storage, least-privilege database roles, and automated security scanning.

---

## 13. Data Quality and Failure Handling

**Decision:** Apply validation before database persistence and fail the pipeline when critical processing errors occur.

**Rationale:**

Fail-fast behavior prevents invalid batches from silently contaminating downstream datasets.

The pipeline records the failure stage and error details in its execution report.

Database transactions provide atomicity for the storage operation, preventing partial database writes when the transaction fails.

**Trade-offs:**

- One invalid record may prevent an entire batch from being loaded.
- Automatic recovery and retry orchestration are not currently implemented.
- Validation rules must evolve alongside the data model.

**Future improvement:** Introduce configurable retry policies, row-level quarantine, and operational alerting.

---

## 14. Known Limitations

DataForge is a portfolio-scale implementation, not a production clinical data platform.

Current limitations include:

1. CSV-based ingestion rather than multiple source systems.
2. In-memory processing through Pandas.
3. A small synthetic demonstration dataset.
4. Batch-level validation without row-level quarantine.
5. Local JSON reports rather than centralized monitoring.
6. No built-in workflow scheduler or automatic retry orchestration.
7. No historical versioning of updated records.
8. No production-grade high-availability or disaster-recovery architecture.
9. No formal statistical inference or causal analysis.

These limitations are intentional boundaries of the initial project scope and provide opportunities for future engineering extensions.

---

## 15. Future Engineering Roadmap

Potential enhancements include:

- Incremental ingestion and batch processing.
- Support for Parquet and additional source formats.
- Configurable data-quality rules and rejected-record quarantine.
- Automated orchestration and scheduled execution.
- Centralized metrics and monitoring dashboards.
- Database migration management.
- Historical data tracking.
- Performance and scalability benchmarks.
- Container vulnerability scanning.
- Analytical dashboards and reporting integrations.

These enhancements are not prerequisites for the initial portfolio release.

---

## 16. Conclusion

DataForge demonstrates a complete, reproducible data engineering workflow that connects Python-based ETL processing with PostgreSQL storage and SQL analytics.

The main engineering priorities are **data integrity, idempotency, modularity, reproducibility, observability, and automated verification**.

By combining containerized execution, automated testing, structured execution reporting, and reusable SQL analytics, the project provides a practical foundation for further data engineering development.

---

*DataForge is an independent portfolio project. All demonstration data is synthetic and must not be interpreted as real clinical-trial information.*