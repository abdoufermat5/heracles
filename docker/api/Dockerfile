# Heracles API Dockerfile
# =======================

FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libldap2-dev \
    libsasl2-dev \
    libssl-dev \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for caching
COPY heracles-api/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy heracles-core for building
COPY heracles-core /heracles-core

# Build and install heracles-core Python bindings
WORKDIR /heracles-core
RUN pip install maturin && maturin build --release
RUN pip install target/wheels/*.whl

# Back to app directory
WORKDIR /app

# Copy application code
COPY heracles-api /app

# Copy plugins package
COPY heracles_plugins /heracles_plugins

# Install plugins package
RUN pip install -e /heracles_plugins

# Create non-root user
RUN useradd -m -u 1000 heracles
RUN chown -R heracles:heracles /app /heracles_plugins
USER heracles

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "heracles_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
