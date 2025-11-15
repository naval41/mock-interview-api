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


FROM base AS runtime

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    ENV="production"

COPY --from=builder /opt/venv /opt/venv

COPY pyproject.toml ./
COPY app ./app
COPY config ./config

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

