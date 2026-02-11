# Heracles API Dockerfile — Multi-stage Production Build
# ======================================================
# Stage 1: Build heracles-core Rust → Python wheel
# Stage 2: Lean production image (~200MB vs ~1.5GB)

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
# Stage 2 — Production Python image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS production

# System deps for python-ldap / asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install production Python deps first (layer cache)
COPY heracles-api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install heracles-core wheel from builder stage
COPY --from=rust-builder /heracles-core/target/wheels/*.whl /tmp/
RUN pip install /tmp/*.whl && rm -f /tmp/*.whl

# Copy application code
COPY heracles-api /app

# Copy and install plugins
COPY heracles_plugins /heracles_plugins
RUN pip install /heracles_plugins

# Gunicorn config
COPY docker/api/gunicorn.conf.py /app/gunicorn.conf.py

# Create non-root user
RUN useradd -m -u 1000 heracles \
    && chown -R heracles:heracles /app /heracles_plugins
USER heracles

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# Production: gunicorn with uvicorn workers
CMD ["gunicorn", "heracles_api.main:app", "-c", "gunicorn.conf.py"]
