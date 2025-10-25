# =========================================================
# Stage 1: Builder - install dependencies cleanly
# =========================================================
FROM python:3.11-slim AS builder

# Install system packages required for building dependencies
RUN apt-get update && apt-get install -y \
    build-essential curl gcc git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files
COPY requirements.txt .

# Install Python dependencies into a local directory
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# =========================================================
# Stage 2: Runtime - lightweight image for running app
# =========================================================
FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Install minimal runtime deps (curl for healthchecks)
RUN apt-get update && apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser

# Copy installed dependencies from builder
COPY --from=builder /install /usr/local

# Copy project source code
COPY --chown=appuser:appuser src/ src/
COPY --chown=appuser:appuser .env ./
COPY --chown=appuser:appuser README.md ./

# Expose FastAPI port
EXPOSE 8000

# Healthcheck endpoint for CI/CD
HEALTHCHECK CMD curl --fail http://localhost:8000/health || exit 1

# Start the API
CMD ["python", "src/api.py"]
