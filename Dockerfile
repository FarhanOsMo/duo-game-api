# syntax=docker/dockerfile:1

# Pinned by tag AND digest: the tag documents the version for humans, the digest
# guarantees every build (local, CI, release) uses byte-identical base layers.
# Dependabot opens a PR when a newer patch image is published.
ARG PYTHON_IMAGE=python:3.12.16-slim-trixie@sha256:962f801b08c870ac2a51b72bf02dae38c9a4162319e5e882ec244e198188d54e

# --- build stage: install dependencies into an isolated virtualenv ----------
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
# Copy only the requirements first so this layer stays cached until they change.
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt \
    # pip is not needed at runtime; removing it shrinks the image and the scan surface.
    && /opt/venv/bin/pip uninstall --yes pip

# --- runtime stage: only the virtualenv, the code and the data --------------
FROM ${PYTHON_IMAGE} AS runtime

ARG GIT_SHA=unknown
ARG APP_VERSION=1.0.0

LABEL org.opencontainers.image.title="duo-game-api" \
      org.opencontainers.image.description="Read-only companion API for the Lanternfall game's data" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.licenses="MIT"

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    GIT_SHA=${GIT_SHA}

# A fixed, unprivileged UID so file ownership is predictable and the container
# never runs as root, even if the process is compromised.
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
# The data is baked into the image: one image = one code version + one data version,
# so promoting an image promotes exactly the data that CI validated.
COPY data ./data

USER app
EXPOSE 8000

# Uses Python's stdlib instead of curl so the slim image needs no extra packages.
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
