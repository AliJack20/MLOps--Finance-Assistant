# MLOps Project – "From Notebook to Reproducible Repository"

🚀 **Elevator Pitch:**  
A regression model which predicts hosuing prices.

---

## 🧩 Architecture
```mermaid
flowchart LR
    A[GitHub Actions CI/CD] -->|Build & Push Docker Image| B[AWS EC2 / ECS]
    B -->|Hosts FastAPI Inference API| C[Users / Clients]
    D[MLflow Tracking Server] -->|Stores Artifacts| E[S3 Bucket]
    B -->|Logs & Metrics| F[CloudWatch]
    C -->|Sends API Requests| B


## ☁️ Cloud Deployment

### AWS S3
- Stores MLflow experiments, metrics, and serialized models.  
- Configured via environment variables in `.env` and referenced by `MLFLOW_TRACKING_URI`.

### AWS EC2
- Hosts the Dockerized FastAPI inference API.  
- GitHub Actions automatically deploys the latest image to EC2 through SSH.  

### How to Reproduce
1. Create an S3 bucket named `mlops-project-bucket`.
2. Launch an EC2 instance (Amazon Linux 2, t2.micro + Docker).
3. Add `.env` to `/home/ec2-user/`.
4. Trigger the GitHub Actions pipeline (push to `main`).
5. Visit `http://<ec2-public-ip>/docs` to view API docs.

### Screenshot Proof
*(Insert screenshots of your running EC2 instance and S3 bucket here.)*

Need MLOps pair.pem key at root directory