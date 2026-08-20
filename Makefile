.PHONY: help up down logs tf-init tf-apply tf-destroy test-unit test-integration test lint format clean

help:
	@echo "Event-Mesh Cloud Platform Commands:"
	@echo "  make up               - Start LocalStack in background"
	@echo "  make down             - Stop LocalStack"
	@echo "  make logs             - View LocalStack container logs"
	@echo "  make tf-init          - Initialize Terraform for local environment"
	@echo "  make tf-apply         - Apply Terraform infrastructure on LocalStack"
	@echo "  make tf-destroy       - Destroy LocalStack infrastructure"
	@echo "  make test-unit        - Run fast unit tests"
	@echo "  make test-integration - Run end-to-end integration tests against LocalStack"
	@echo "  make test             - Run all tests with coverage report"
	@echo "  make lint             - Run Ruff and formatting checks"
	@echo "  make format           - Auto-format code with Ruff"
	@echo "  make clean            - Remove cache and temporary files"

up:
	docker compose up -d
	@echo "Waiting for LocalStack to be ready..."
	@docker compose exec -T localstack curl -s http://localhost:4566/_localstack/health || true

down:
	docker compose down

logs:
	docker compose logs -f localstack

tf-init:
	cd infra/terraform/environments/local && terraform init

tf-apply:
	cd infra/terraform/environments/local && terraform apply -auto-approve

tf-destroy:
	cd infra/terraform/environments/local && terraform destroy -auto-approve

test-unit:
	pytest tests/unit -v -m unit

test-integration:
	pytest tests/integration -v -m integration

test:
	pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf .coverage htmlcov/
