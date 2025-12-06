# 🏦 Financial Assistant LLMOps

A smart financial assistant that provides personalized advice, expense tracking, and query handling using Mistral-7B LLM.

![Build Status](https://img.shields.io/badge/status-active-brightgreen)
![Version](https://img.shields.io/badge/version-v2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Project Overview

The Financial Assistant LLMOps project demonstrates a complete operational workflow for Large Language Models (LLMs) in the financial domain. It integrates a Retrieval-Augmented Generation (RAG) pipeline, safety guardrails, monitoring, evaluation, and deployment automation.

### Purpose & Goals
- Provide personalized financial insights and advice.
- Implement RAG-based retrieval + LLM response pipeline.
- Compare multiple prompting strategies: zero-shot, few-shot, and chain-of-thought.
- Ensure safe LLM usage with guardrails for input validation and output moderation.
- Monitor model metrics, latency, token usage, and data drift with Prometheus, Grafana, and Evidently.

### LLMOps Objectives
- Operationalize Mistral-7B for financial tasks.
- Enable prompt experimentation and evaluation.
- Automate deployment and CI/CD for reproducibility.
- Maintain responsible AI practices and auditability.

---

## Architecture
![WhatsApp Image 2025-12-05 at 01 59 27_9722532b](https://github.com/user-attachments/assets/b5f980c5-b93b-4abe-8af4-89c85e619793)

## Program Flow
![WhatsApp Image 2025-12-05 at 02 03 44_6abbf4b9](https://github.com/user-attachments/assets/1b1f0d13-ec1b-4714-9e95-3f5d0002a31b)


## Features
Prompting Strategies

### Zero-Shot Prompting – baseline strategy without examples.

### Few-Shot Prompting – includes 3-5 examples for context.

### Chain-of-Thought / Meta-Prompting – guides the model to reason step-by-step or adopt a structured persona.

## Monitoring

### Grafana – visualizes Prometheus metrics with dashboards for system health and performance.

![grafana](https://github.com/user-attachments/assets/6dfcc91f-39c8-48cf-833a-f98374463407)

### Prometheus – tracks LLM metrics like latency, token usage, and guardrail violations.
![prom](https://github.com/user-attachments/assets/ee561652-ab24-47af-a92b-57fab6968017)


### Evidently AI – monitors data drift and evaluates retrieval corpus quality.
![ev1](https://github.com/user-attachments/assets/0dd47e1f-ea3c-4554-8c3d-776a8a389b90)




# Step-by-Step RAG Deployment Guide

## 1. Clone Repository
```bash
git clone <repo-url>
cd <repo-folder>
```


## 2. Environment Setup

```bash
cp .env.example .env
# Set AWS credentials, HF_TOKEN, and other required variables
```

## 3. Build & Run Docker Containers

make docker-run       # Starts FastAPI API (port 8000)
make docker-stop      # Stops and removes the container


Build & Push to AWS ECR

make push-ecr         # Builds, tags, and pushes image
make deploy-ec2       # Pulls image and runs on EC2 (port 80)


Run RAG Pipeline

make rag              # Builds embeddings, vector store, and indexes documents


Verify Health

curl http://localhost:8000/health
# Response: {"status": "healthy"}

API Usage Examples
1. Question-Answering (RAG)
curl -X POST http://localhost:8000/qa \
-H "Content-Type: application/json" \
-d '{"query": "How much did I spend on food last month?"}'


Response:

{
  "answer": "You spent $320 on food last month. (Source: training_case_5)",
  "context": "...retrieved RAG context here...",
  "guardrail": {"rule": "ok"}
}

2. Predict Next Week Spending
curl -X POST http://localhost:8000/predict \
-H "Content-Type: application/json" \
-d '{"week": "2025-12-01", "actual_spending": 1200}'


Response:

{
  "input": {"week": "2025-12-01", "actual_spending": 1200},
  "prediction_next_week": 1350.5
}

3. Guardrails Example (PII Detection)
curl -X POST http://localhost:8000/qa \
-H "Content-Type: application/json" \
-d '{"query": "My SSN is 123-45-6789"}'


Response:

{
  "detail": "Input rejected by guardrails: pii_detected"
}

4. Metrics Endpoint (Prometheus)
curl http://localhost:8000/metrics
# Exposes latency, token usage, input/output violations

Notes

RAG indexing supports JSON and plain text documents.

Vector store can use FAISS if available, else TF-IDF fallback.

Guardrails enforce input validation (PII, prompt injection) and output moderation (toxicity, hallucination detection).

FastAPI exposes /metrics for Prometheus and is fully instrumented via prometheus-fastapi-instrumentator.

Step-by-step deployment is reproducible via the Makefile.





