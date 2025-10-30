# 🧠 D7 API Documentation

## Overview
The **D7 Model Prediction API** is a containerized FastAPI service that loads a trained machine learning model from AWS S3 and exposes endpoints for prediction and health monitoring.  
FastAPI automatically generates interactive documentation via Swagger UI and ReDoc.

---

## 🚀 Base URLs

| Environment | Description | URL |
|--------------|-------------|-----|
| **Development** | Local development (Uvicorn, hot reload) | `http://localhost:8000` |
| **Production** | Dockerized service (Gunicorn via `web-prod`) | `http://localhost:8001` |

---

## 📖 Endpoints

| Method | Path | Description | Example |
|:-------|:-----|:-------------|:---------|
| **GET** | `/health` | Checks if the API is running and healthy | `{"status": "healthy"}` |
| **POST** | `/predict` | Accepts tabular JSON data and returns model predictions | See cURL below |
| **GET** | `/metrics` | Exposes Prometheus metrics for monitoring | Text-based metrics output |
| **GET** | `/docs` | FastAPI’s built-in Swagger UI for live testing | Interactive browser docs |
| **GET** | `/redoc` | Alternative documentation interface | Read-only documentation |

---

## 💻 Example cURL Request

```bash
curl -X POST http://localhost:8001/predict \
     -H "Content-Type: application/json" \
     -d '{
           "instances": [
             { "feature1": 1.2, "feature2": 3.4 },
             { "feature1": 5.6, "feature2": 7.8 }
           ]
         }'
OUTPUT:
{
  "predictions": [12345.67, 98765.43]
}
