.PHONY: dev test docker build push run lint format

dev:
	docker-compose -f compose/docker-compose.dev.yml up --build

test:
	pytest --cov=src --cov-fail-under=80

lint:
	ruff src tests
	black --check src tests

docker:
	docker build -t ghcr.io/${GITHUB_REPOSITORY}:${GITHUB_SHA} .

push:
	docker push ghcr.io/${GITHUB_REPOSITORY}:${GITHUB_SHA}
