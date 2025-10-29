# ==============================
# Stage 1 — Base setup
# ==============================
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing pyc files & enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependency file first for caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Create a non-root user for better security
RUN useradd -m appuser
USER appuser

# Default command — start FastAPI inference API
CMD ["uvicorn", "src.inference:app", "--host", "0.0.0.0", "--port", "8000"]
