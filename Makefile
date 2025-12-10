# =========================================================
# Makefile for MLOps Project (Phase 1 - AWS Integration)
# =========================================================

PROJECT_NAME = mlops-project
IMAGE_NAME = mlops-app
AWS_REGION = ap-south-1
ACCOUNT_ID = <your-aws-account-id>  # replace this once
ECR_REGISTRY = $(ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com
EC2_IP = <your-ec2-public-ip>       # replace this once
KEY_PATH = ~/.ssh/ec2-key.pem

# =========================================================
# Environment Setup
# =========================================================
dev:
	pip install --upgrade pip
	pip install -r requirements.txt
	pre-commit install
	echo "✅ Development environment ready."

# =========================================================
# Code Quality
# =========================================================
lint:
	black --check src
	ruff src
	echo "✅ Linting passed."

format:
	black src
	ruff --fix src
	echo "✅ Code formatted."

# =========================================================
# Testing
# =========================================================
test:
	pytest --cov=src --cov-fail-under=80
	echo "✅ Tests passed with sufficient coverage."

# =========================================================
# Docker Build & Run
# =========================================================
docker-build:
	docker build -t $(IMAGE_NAME):latest .

docker-run:
	docker run -d -p 8000:8000 --env-file .env --name $(IMAGE_NAME) $(IMAGE_NAME):latest
	echo "🚀 API running at http://localhost:8000/docs"

docker-stop:
	docker stop $(IMAGE_NAME) || true
	docker rm $(IMAGE_NAME) || true
	echo "🛑 Container stopped and removed."

# =========================================================
# AWS ECR (Container Registry)
# =========================================================
ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)

ecr-create:
	aws ecr create-repository --repository-name $(IMAGE_NAME) --region $(AWS_REGION) || true

push-ecr: docker-build ecr-login
	docker tag $(IMAGE_NAME):latest $(ECR_REGISTRY)/$(IMAGE_NAME):latest
	docker push $(ECR_REGISTRY)/$(IMAGE_NAME):latest
	echo "✅ Image pushed to ECR: $(ECR_REGISTRY)/$(IMAGE_NAME):latest"

# =========================================================
# AWS EC2 Deployment
# =========================================================
deploy-ec2: push-ecr
	ssh -i $(KEY_PATH) ec2-user@$(EC2_IP) "\
	sudo docker pull $(ECR_REGISTRY)/$(IMAGE_NAME):latest && \
	sudo docker stop $(IMAGE_NAME) || true && \
	sudo docker rm $(IMAGE_NAME) || true && \
	sudo docker run -d -p 80:8000 \
	--env-file /home/ec2-user/.env \
	--name $(IMAGE_NAME) \
	$(ECR_REGISTRY)/$(IMAGE_NAME):latest"
	echo "🚀 Deployment complete at http://$(EC2_IP)/docs"

# =========================================================
# Cleanup
# =========================================================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	echo "🧹 Cleanup complete."

# =========================================================
# Convenience
# =========================================================
help:
	@echo "Available commands:"
	@echo "  make dev           - Setup local environment"
	@echo "  make lint          - Run linter"
	@echo "  make format        - Auto-fix style issues"
	@echo "  make test          - Run pytest with coverage"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run API locally in container"
	@echo "  make push-ecr      - Push image to AWS ECR"
	@echo "  make deploy-ec2    - Deploy image to EC2"
	@echo "  make clean         - Remove temp files and caches"
