# ==========================================================
# 1️⃣ Base Image: lightweight Python + security patches
# ==========================================================
FROM python:3.11-slim

# Prevent Python from buffering logs
ENV PYTHONUNBUFFERED=1

# Set working directory inside container
WORKDIR /app

# ==========================================================
# 2️⃣ Install basic dependencies
# ==========================================================
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc curl && \
    rm -rf /var/lib/apt/lists/*

# ==========================================================
# 3️⃣ Copy dependency files and install Python packages
# ==========================================================
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================================
# 4️⃣ Copy project files
# ==========================================================
COPY . .

# ==========================================================
# 5️⃣ Environment setup
# ==========================================================
# (You can override these in your .env or docker run --env-file)
ENV MODE=cloud
ENV AWS_REGION=eu-north-1
ENV MLFLOW_TRACKING_URI=file:./mlruns
ENV S3_BUCKET=mlops-finance-bucket
ENV S3_MODEL_KEY=models/finance_assistant/model.pkl

# Expose FastAPI port
EXPOSE 8000

# ==========================================================
# 6️⃣ Healthcheck (optional)
# ==========================================================
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# ==========================================================
# 7️⃣ Entrypoint - launch FastAPI app (Uvicorn)
# ==========================================================
# If your main API file is testapi.py at project root or under src/
CMD ["uvicorn", "tests.testapi:app", "--host", "0.0.0.0", "--port", "8000"]
