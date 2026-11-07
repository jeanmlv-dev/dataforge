
FROM python:3.13-slim

# Install uv from the official image
COPY --from=ghcr.io/astral-sh/uv:0.9.0 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    UV_LINK_MODE=copy

# Copy project metadata, README and source code
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install locked production dependencies
RUN uv sync --frozen --no-dev

# Include sample input data
COPY data/sample/ ./data/sample/

# Run the ETL pipeline
CMD ["uv", "run", "--no-sync", "python", "-m", "dataforge.pipeline", "--input", "data/sample/example.csv"]
