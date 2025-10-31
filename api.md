API Documentation — Finance Assistant

Overview

This FastAPI service serves a regression model for real-time predictions. Interactive docs are available at:

- Swagger UI: http://localhost:8000/docs
- OpenAPI JSON: http://localhost:8000/openapi.json

Base URL

- Local (Docker Compose): http://localhost:8000

Endpoints

GET /health

- Purpose: Liveness/health check
- Response 200:

```json
{
  "status": "healthy"
}
```

GET /metrics

- Purpose: Prometheus scrape endpoint (automatically exposed)
- Content-Type: text/plain; version=0.0.4

POST /predict

- Purpose: Run a prediction for a single record
- Accept: application/json
- Produce: application/json

Example cURL

```bash
curl -X 'POST' \
  'http://localhost:8000/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "full_sq": 89,
  "life_sq": 50,
  "floor": 9,
  "product_type": "Investment"
}'
```

Request JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PredictRequest",
  "type": "object",
  "properties": {
    "full_sq": { "type": "number", "description": "Total area in square meters" },
    "life_sq": { "type": "number", "description": "Living area in square meters" },
    "floor":   { "type": "number", "description": "Floor number" },
    "product_type": {
      "type": "string",
      "enum": ["Investment", "OwnerOccupier"],
      "description": "Categorical feature mapped internally to numeric"
    }
  },
  "required": ["full_sq", "life_sq", "floor", "product_type"],
  "additionalProperties": true
}
```

Response JSON (success)

```json
{
  "input": {
    "full_sq": 89,
    "life_sq": 50,
    "floor": 9,
    "product_type": "Investment"
  },
  "prediction": 123456.78
}
```

Response JSON Schema (success)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "PredictResponse",
  "type": "object",
  "properties": {
    "input": { "type": "object" },
    "prediction": { "type": "number" }
  },
  "required": ["prediction"],
  "additionalProperties": true
}
```

Response JSON (error)

```json
{
  "error": "<message>"
}
```

Notes

- The service internally maps `product_type` to a numeric value using {"Investment": 1, "OwnerOccupier": 0} and drops non-numeric leftovers before inference.
- The Prometheus metrics endpoint is provided by `prometheus-fastapi-instrumentator` and custom exposure at `/metrics`.
