# 1️⃣ DEV STAGE
# =========================================
FROM python:3.11-slim AS dev
WORKDIR /app
COPY  requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Expose FastAPI port
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# 1️⃣ PROD STAGE
# =========================================
FROM python:3.11-slim AS PROD
WORKDIR /app
COPY --from=dev /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dev /usr/local/bin/gunicorn /usr/local/bin/gunicorn

COPY app/ .

RUN useradd --system --no-create-home --shell /usr/sbin/nologin appuser
USER appuser
EXPOSE 8000
# Healthcheck (calls FastAPI /health endpoint)
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker","--bind", "0.0.0.0:8000", "main:app"]
