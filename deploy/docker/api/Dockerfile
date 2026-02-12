# Heracles API Dockerfile — Multi-stage Production Build
# ======================================================
# Stage 1: Build heracles-core Rust → Python wheel
# Stage 2: Lean production image with uv
# Package manager: uv (https://docs.astral.sh/uv/)

# ---------------------------------------------------------------------------
# Stage 1 — Rust builder: compile heracles-core Python wheel
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS rust-builder

RUN apt-get update && apt-get install -y \
    gcc curl pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

ENV RUSTUP_HOME=/usr/local/rustup \
    CARGO_HOME=/usr/local/cargo \
    PATH=/usr/local/cargo/bin:$PATH
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable

RUN pip install maturin

COPY heracles-core /heracles-core
WORKDIR /heracles-core
RUN maturin build --release
# Wheel lands in /heracles-core/target/wheels/*.whl

# ---------------------------------------------------------------------------
# Stage 2 — Production Python image (uv)
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

# System deps for python-ldap / asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# uv settings: install into system python, no venvs inside container
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install heracles-core wheel from builder stage
COPY --from=rust-builder /heracles-core/target/wheels/*.whl /tmp/
RUN uv pip install /tmp/*.whl && rm -f /tmp/*.whl

# Install API deps (layer cache: copy pyproject.toml first, install deps only)
COPY heracles-api/pyproject.toml /app/pyproject.toml
COPY heracles-api/CHANGELOG.md /app/CHANGELOG.md
RUN mkdir -p /app/heracles_api && touch /app/heracles_api/__init__.py \
    && uv pip install . \
    && rm -rf /app/heracles_api

# Copy application code (deps already cached in layer above)
COPY heracles-api /app

# Copy and install plugins
COPY heracles_plugins /heracles_plugins
RUN uv pip install /heracles_plugins

# Gunicorn config
COPY deploy/docker/api/gunicorn.conf.py /app/gunicorn.conf.py

# Create non-root user
RUN useradd -m -u 1000 heracles \
    && chown -R heracles:heracles /app /heracles_plugins
USER heracles

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Production: gunicorn with uvicorn workers
CMD ["gunicorn", "heracles_api.main:app", "-c", "gunicorn.conf.py"]
