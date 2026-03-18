# syntax=docker/dockerfile:1
FROM ghcr.io/cartsnitch/mirror/python:3.12-slim AS base

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini ./

FROM base AS test
RUN pip install --no-cache-dir ".[dev]"
COPY tests/ tests/
CMD ["pytest", "--tb=short", "-q"]

FROM base AS prod
CMD ["python", "-c", "import cartsnitch_common; print(f'cartsnitch-common ready')"]
