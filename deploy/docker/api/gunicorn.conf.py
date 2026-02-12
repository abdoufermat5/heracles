# Gunicorn Configuration for Heracles API
# ========================================
# Production settings for gunicorn + uvicorn workers.

import multiprocessing
import os

# Bind
bind = "0.0.0.0:8000"

# Workers: 2 * CPU cores + 1 (optimal for mixed I/O / CPU workloads)
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Uvicorn worker class (async)
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
keepalive = 5

# Max requests per worker before restart (prevents memory leaks)
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = 50

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = os.getenv("LOG_LEVEL", "info").lower()

# Preload app (shares memory between workers, faster startup)
preload_app = False  # Disabled — each worker needs its own async event loop

# Process name
proc_name = "heracles-api"

# Forward proxy headers
forwarded_allow_ips = os.getenv("TRUSTED_PROXY_IPS", "*")
