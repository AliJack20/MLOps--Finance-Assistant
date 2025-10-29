# ================================
# Base (common bits)
# ================================
FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

# healthcheck needs curl
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ================================
# DEV
# ================================
FROM base AS dev
# keep code inside the image so it runs even without bind-mounts
EXPOSE 8000
# hot reload in dev
CMD ["uvicorn", "api:app", "--host","0.0.0.0","--port","8000","--reload"]

# ================================
# PROD
# ================================
FROM base AS prod
COPY . .

# non-root
RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser \
 && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
CMD curl -f http://localhost:8000/health || exit 1

# gunicorn + uvicorn worker
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","2","--bind","0.0.0.0:8000","api:app"]
