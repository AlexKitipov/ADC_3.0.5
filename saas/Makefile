.PHONY: help setup test lint format dev test-api test-web build-web compose-config smoke-api

help:
	@echo "ADC SaaS developer commands"
	@echo "  make setup   Install project dependencies (to be implemented)"
	@echo "  make dev     Start local development services"
	@echo "  make test    Run test suites"
	@echo "  make test-api       Run backend pytest suite"
	@echo "  make test-web       Run frontend Vitest suite"
	@echo "  make build-web      Build frontend production bundle"
	@echo "  make compose-config Validate Docker Compose configuration"
	@echo "  make smoke-api      Run API smoke flow against API_URL"
	@echo "  make lint    Run linters"
	@echo "  make format  Format source files"

setup:
	@echo "Dependency setup will be added with backend/frontend implementation PRs."

dev:
	docker compose up --build

test: test-api test-web

test-api:
	cd apps/api && python -m pytest

test-web:
	cd apps/web && npm test -- --run

build-web:
	cd apps/web && npm run build

compose-config:
	docker compose config

smoke-api:
	./scripts/smoke-api.sh

lint:
	@echo "Linters will be wired after tool configs are added."

format:
	@echo "Formatters will be wired after tool configs are added."
