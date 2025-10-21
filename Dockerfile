# ========= Stage 1 – builder =========
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y build-essential curl && rm -rf /var/lib/apt/lists/*
COPY src/requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip wheel -r requirements.txt --wheel-dir=/wheels

# ========= Stage 2 – runtime =========
FROM python:3.11-slim

# Security best-practice: non-root user
RUN useradd --create-home appuser
USER appuser
WORKDIR /app

# Copy wheels + source
COPY --from=builder /wheels /wheels
COPY src /app

# Install dependencies
RUN pip install --no-index --find-links=/wheels -r /app/requirements.txt

# Healthcheck script
COPY docker/healthcheck.sh /usr/local/bin/healthcheck
USER root
RUN chmod +x /usr/local/bin/healthcheck
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s CMD ["bash", "/usr/local/bin/healthcheck"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
