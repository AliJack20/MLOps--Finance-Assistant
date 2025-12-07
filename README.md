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


# 🚀 RAG System Deployment on AWS EC2/S3

A complete step-by-step guide to deploy your Retrieval-Augmented Generation (RAG) system on AWS infrastructure.

---

## 🏗️ Architecture Overview

```
┌─────────────┐         ┌─────────────┐
│   S3 Bucket │◄────────┤ EC2 Instance│
│  Documents  │         │  RAG API    │
│  Embeddings │         │  FastAPI    │
└─────────────┘         └─────────────┘

```

## 🎯 Part 1: AWS Setup & Prerequisites

### Step 1: Install AWS CLI

```bash
# Download AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

### Step 2: Configure AWS Credentials

```bash
aws configure
```

**Enter when prompted:**
- AWS Access Key ID: `<your-access-key>`
- AWS Secret Access Key: `<your-secret-key>`
- Default region name: `us-east-1`
- Default output format: `json`

> 💡 **Don't have credentials?** Go to AWS Console → IAM → Users → Add User → Enable "Programmatic access"

---

## 📦 Part 2: S3 Bucket Setup

### Step 1: Create S3 Bucket

```bash
# Create bucket (choose unique name)
export BUCKET_NAME="your-rag-bucket-$(date +%s)"
aws s3 mb s3://$BUCKET_NAME --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
    --bucket $BUCKET_NAME \
    --versioning-configuration Status=Enabled

# Verify bucket created
aws s3 ls
```

### Step 2: Upload Documents

```bash
# Upload documents folder
aws s3 cp src/rag_app/data/ s3://$BUCKET_NAME/data/ --recursive

# Upload embeddings cache (if exists)
aws s3 cp src/rag_app/embeddings_cache/ s3://$BUCKET_NAME/embeddings_cache/ --recursive

# List uploaded files
aws s3 ls s3://$BUCKET_NAME/ --recursive
```

---

## 🖥️ Part 3: EC2 Instance Setup

### Step 1: Create IAM Role for EC2

```bash
# Create trust policy
cat > ec2-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
EOF

# Create role
aws iam create-role \
    --role-name RAG-EC2-S3-Role \
    --assume-role-policy-document file://ec2-trust-policy.json

# Attach S3 permissions
aws iam attach-role-policy \
    --role-name RAG-EC2-S3-Role \
    --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# Create instance profile
aws iam create-instance-profile --instance-profile-name RAG-EC2-Profile
aws iam add-role-to-instance-profile \
    --instance-profile-name RAG-EC2-Profile \
    --role-name RAG-EC2-S3-Role
```

### Step 2: Launch EC2 Instance

**Via AWS Console (Recommended for beginners):**

1. Navigate to **EC2 Dashboard** → **Launch Instance**
2. Configure instance:
   - **Name**: `rag-application-server`
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Instance Type**: `t3.medium` (2 vCPU, 4GB RAM)
   - **Key Pair**: Create new (save `.pem` file safely)
   - **Network**: Create security group with these rules:
     - SSH (22) from your IP
     - HTTP (80) from anywhere (0.0.0.0/0)
     - Custom TCP (8000) from anywhere (0.0.0.0/0)
   - **Storage**: 30GB gp3 SSD
   - **Advanced Details** → **IAM instance profile**: `RAG-EC2-Profile`
3. Click **Launch Instance**
4. Wait for instance state to be "Running"

### Step 3: Get Instance Details

```bash
# Get instance public IP (replace INSTANCE_ID)
export INSTANCE_ID="i-xxxxxxxxxx"
export EC2_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

echo "Your EC2 IP: $EC2_IP"
```

---

## 🔌 Part 4: Connect & Install Dependencies

### Step 1: SSH into EC2

```bash
# Set permissions on key file
chmod 400 your-key.pem

# Connect to EC2
ssh -i your-key.pem ubuntu@$EC2_IP
```

### Step 2: Update System

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install essentials
sudo apt install -y python3.11 python3.11-venv python3-pip git unzip curl htop
```

### Step 3: Install AWS CLI on EC2

```bash
# Download and install
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf aws awscliv2.zip

# Verify installation
aws --version

# Test S3 access (should work without credentials due to IAM role)
aws s3 ls
```

---

## 🚀 Part 5: Deploy RAG Application

### Step 1: Create Project Structure

```bash
# Create directory
mkdir -p ~/rag-app
cd ~/rag-app

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### Step 2: Install Python Dependencies

```bash
# Install required packages
pip install numpy sentence-transformers scikit-learn faiss-cpu boto3 fastapi uvicorn[standard] python-multipart
```

### Step 3: Download Data from S3

```bash
# Create directories
mkdir -p src/rag_app/data
mkdir -p src/rag_app/embeddings_cache

# Download documents (replace BUCKET_NAME)
export BUCKET_NAME="your-rag-bucket"
aws s3 sync s3://$BUCKET_NAME/data/ src/rag_app/data/

# Download embeddings if they exist
aws s3 sync s3://$BUCKET_NAME/embeddings_cache/ src/rag_app/embeddings_cache/ 2>/dev/null || echo "No cached embeddings found"
```

### Step 4: Create `rag.py`

```bash
# Create file
nano src/rag_app/rag.py
```

**Paste your `rag.py` code, then press `Ctrl+X`, `Y`, `Enter`**

Or upload from local machine:

```bash
# On your local machine
scp -i your-key.pem rag.py ubuntu@$EC2_IP:~/rag-app/src/rag_app/
```

### Step 5: Create API Server

```bash
# Create API server file
nano ~/rag-app/api_server.py
```

**Paste this code:**

```python
# src/api.py
import os
import logging
from fastapi import FastAPI, Response, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
import pandas as pd
from pydantic import BaseModel
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any

# local imports
from src.inference import load_model, predict  # your existing functions

from src.rag_app.llm import classify_intent, extract_transactions, generate_answer  # the GradioLLM instance
from rag_app.rag import RAG
from src.rag_app.guardrails import Guardrails
from src.rag_app.llm import llm_adapter  # the GradioLLM instance
from src.rag_app.rag import RAG

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Finance Assistant API", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow all origins (use specific domains in prod)
    allow_credentials=True,
    allow_methods=["*"],          # allow all HTTP methods
    allow_headers=["*"],          # allow all headers
)

# Initialize Prometheus
instrumentator = Instrumentator().instrument(app)

# Globals (populated at startup)
model = None
rag = None
hf_llm = None
guardrails= None


class QueryIn(BaseModel):
    query: str

@app.on_event("startup")
async def startup_event():
    global model, rag, hf_llm

    # 1) Load prediction model
    try:
        model = load_model()
        logger.info("✅ Prediction model loaded")
    except Exception:
        model = None
        logger.exception("Failed loading prediction model at startup")

    # 2) Load/build RAG index
    try:
        rag = RAG(
            docs_folder="src/rag_app/data",
            index_path="src/rag_app/embeddings_cache/faiss_index"
        )
        await asyncio.to_thread(rag.build_index_if_missing)
        logger.info("✅ RAG index ready")
    except Exception:
        rag = None
        logger.exception("Failed to load/build RAG index at startup")

    # 3) Use Gradio LLM Adapter
    try:
        from src.rag_app.llm import llm_adapter
        hf_llm = llm_adapter
        logger.info("✅ Gradio LLM adapter initialized")
    except Exception:
        hf_llm = None
        logger.exception("Failed initializing llm_adapter")

        # after hf_llm initialization in startup_event
    try:
        guardrails = Guardrails(embeddings=rag.embeddings if rag is not None else None,
                           tox_threshold=0.3, hallucination_threshold=0.6)
        # attach to module-global so endpoints can access
        globals()["guardrails"] = guardrails
        logger.info("✅ Guardrails initialized")
    except Exception:
        globals()["guardrails"] = None
        logger.exception("Failed to initialize guardrails")

    # 4) Expose metrics
    instrumentator.expose(app)
    logger.info("✅ Startup complete")



@app.post("/qa")
async def qa(q: QueryIn):
    global rag, hf_llm, guardrails

    if rag is None:
        raise HTTPException(status_code=503, detail="RAG index not available")

    if hf_llm is None:
        raise HTTPException(status_code=503, detail="LLM not available")

    # 0. Input validation
    if guardrails is not None:
        ok, details = guardrails.validate_input(q.query)
        if not ok:
            # log event and return 400 (or choose to redact)
            guardrails.log_event("input_violation", {"input": q.query, **details})
            raise HTTPException(status_code=400, detail=f"Input rejected by guardrails: {details['rule']}")

    try:
        res = rag.query(q.query, k=4)
        prompt = res["prompt"]
        context = res["context"]

        answer = await asyncio.to_thread(
            hf_llm.generate,
            prompt,
            "",
            256,
            0.7
        )

        # Output moderation
        if guardrails is not None:
            ok_out, out_details = guardrails.moderate_output(answer, context=context)
            if not ok_out:
                guardrails.log_event("output_violation", {"prompt": prompt, "answer": answer, **out_details})
                # Option 1: redact and return safe message
                redacted = "[The model output was rejected by moderation policies. Please rephrase your query.]"
                return {"answer": redacted, "context": context, "guardrail": out_details}
                # Option 2: raise HTTPException(503, ...) to indicate failure
                # raise HTTPException(status_code=503, detail="Output rejected by guardrails")

        return {"answer": answer, "context": context}

    except Exception:
        logger.exception("QA request failed")
        raise HTTPException(status_code=500, detail="LLM generation failed")




@app.get("/health")
def health():
    """Simple health check"""
    return {"status": "healthy"}


@app.post("/predict")
async def predict_api(payload: dict):
    try:
        print("Received payload:", payload)
        df = pd.DataFrame([payload])
        print("Input DataFrame:", df)
        if "week" in df.columns:
            df["week"] = pd.to_datetime(df["week"])
            df["week_num"] = df["week"].view("int64") // 10**9

        df = df.select_dtypes(include=["number"])

        preds = model.predict(df)

        return {
            "input": payload,
            "prediction_next_week": float(preds[0])
        }

    except Exception as e:
        logger.exception("Prediction failed")
        return {"error": str(e)}    
    """
    {
    "week": "04/01/2004",
    "actual_spending": 6869.02
    }
    """


@app.get("/metrics")
def metrics():
    """Expose Prometheus metrics endpoint."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

```

**Save with `Ctrl+X`, `Y`, `Enter`**

### Step 6: Test the API

```bash
# Run the server
cd ~/rag-app
source venv/bin/activate
uvicorn api_server:app --host 0.0.0.0 --port 8000
```

**In a new terminal, test:**

```bash
# Health check
curl http://localhost:8000/health

# Query test
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is financial planning?", "k": 3}'
```

Press `Ctrl+C` to stop the server.


**🎉 Congratulations! Your RAG system is now live on AWS!**

Access your API at: `http://your-ec2-ip:8000/docs`


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

Also added a LangChain implementation to the RAG pipeline for Markdown.
This enables better retrieval and structured Markdown output with our vector store.

FastAPI exposes /metrics for Prometheus and is fully instrumented via prometheus-fastapi-instrumentator.

Step-by-step deployment is reproducible via the Makefile.





