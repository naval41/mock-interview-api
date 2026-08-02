# syntax=docker/dockerfile:1.7

FROM python:3.11-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \  
        build-essential \
        libpq-dev \
        ffmpeg \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgl1 \
        libglib2.0-0 \
        libsndfile1 \
        libopus0 \
        libvpx7 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


FROM base AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt ./
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# --------------------------------------------------------------------------- #
# Test stage — runs the deterministic (hermetic) suite. This GATES the build:
# `runtime` copies from this stage, so if any test fails the image build fails.
# The `llm_live` evals are excluded by the default pytest config (they are paid
# and networked); run those separately with `pytest -m llm_live`.
# --------------------------------------------------------------------------- #
FROM base AS test

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    ENV="test"

COPY --from=builder /opt/venv /opt/venv

COPY pyproject.toml ./
COPY app ./app
COPY config ./config
COPY tests ./tests

# Fails the build on any test failure. Dummy settings keep the suite hermetic
# (no real DB/secrets); the DB engine is created lazily and never connects.
RUN DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test" \
    JWT_SECRET_KEY="test-secret-not-used" \
    pytest


FROM base AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    ENV="production"

# Copy from `test` (not `builder`) so the runtime image can only be produced
# after the test stage passes.
COPY --from=test /opt/venv /opt/venv

COPY pyproject.toml ./
COPY app ./app
COPY config ./config

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

