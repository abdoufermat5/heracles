# Heracles Development Makefile
# =============================

.PHONY: help dev dev-infra prod stop clean test test-rust test-api lint format build bootstrap ui ui-install ui-build api api-install

# Default target
help:
	@echo "Heracles Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Infrastructure:"
	@echo "  make dev-infra     - Start LDAP, PostgreSQL, Redis (minimal setup)"
	@echo "  make dev           - Start full development environment (Docker)"
	@echo "  make prod          - Start production environment"
	@echo "  make bootstrap     - Initialize LDAP with base structure"
	@echo "  make stop          - Stop all services"
	@echo "  make clean         - Stop and remove all volumes"
	@echo ""
	@echo "Local Development:"
	@echo "  make api           - Run API server locally"
	@echo "  make api-install   - Install API dependencies"
	@echo "  make ui            - Run UI dev server locally (bun)"
	@echo "  make ui-install    - Install UI dependencies (bun)"
	@echo "  make ui-build      - Build UI for production"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-rust     - Run Rust tests only"
	@echo "  make test-api      - Run API tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          - Run linters"
	@echo "  make format        - Format code"
	@echo ""
	@echo "Build:"
	@echo "  make build         - Build all components"
	@echo "  make build-rust    - Build heracles-core"
	@echo "  make build-ui      - Build UI"
	@echo ""

# ===========================================
# Infrastructure
# ===========================================

# Start minimal infrastructure (LDAP, PostgreSQL, Redis)
dev-infra:
	docker compose up -d ldap postgres redis phpldapadmin
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo ""
	@echo "Infrastructure started!"
	@echo "  - LDAP:          ldap://localhost:389"
	@echo "  - phpLDAPadmin:  http://localhost:8080"
	@echo "  - PostgreSQL:    localhost:5432"
	@echo "  - Redis:         localhost:6379"
	@echo ""
	@echo "LDAP Admin: cn=admin,dc=heracles,dc=local / admin_secret"
	@echo ""
	@echo "💡 Run 'make bootstrap' to initialize LDAP structure"

# Initialize LDAP with base structure
bootstrap:
	@./scripts/ldap-bootstrap.sh

# Start full development environment
dev:
	docker compose --profile full up -d
	@echo ""
	@echo "Full environment started!"
	@echo "  - API:           http://localhost:8000"
	@echo "  - UI:            http://localhost:3000"
	@echo "  - phpLDAPadmin:  http://localhost:8080"

# Start production environment
prod:
	docker compose --profile prod up -d --build
	@echo ""
	@echo "Production environment started!"
	@echo "  - UI:            http://localhost:80"
	@echo "  - API:           http://localhost:8000"

# Stop all services
stop:
	docker compose --profile full --profile prod down

# Clean all volumes
clean:
	docker compose --profile full --profile prod down -v
	@echo "All volumes removed"

# ===========================================
# Testing
# ===========================================

# Run all tests
test: test-rust test-api

# Run Rust tests
test-rust:
	cd heracles-core && cargo test --no-default-features

# Run API tests
test-api:
	cd heracles-api && python -m pytest tests/ -v

# ===========================================
# API Development
# ===========================================

# Run API server locally (requires pip install)
api:
	@chmod +x heracles-api/run-dev.sh
	@cd heracles-api && ./run-dev.sh

# Install API dependencies locally
api-install:
	pip install -r heracles-api/requirements.txt

# ===========================================
# UI Development
# ===========================================

# Run UI dev server locally (requires bun)
ui:
	cd heracles-ui && bun run dev

# Install UI dependencies locally
ui-install:
	cd heracles-ui && bun install

# Build UI for production
ui-build:
	cd heracles-ui && bun run build

# Run UI type checking
ui-typecheck:
	cd heracles-ui && bun run tsc -b

# =========================================== 
# Code Quality
# ===========================================

# Run all linters
lint: lint-rust lint-python lint-ui

lint-rust:
	cd heracles-core && cargo clippy -- -D warnings

lint-python:
	cd heracles-api && ruff check .
	cd heracles-api && mypy heracles_api

lint-ui:
	cd heracles-ui && bun run lint

# Format all code
format: format-rust format-python

format-rust:
	cd heracles-core && cargo fmt

format-python:
	cd heracles-api && black heracles_api tests
	cd heracles-api && ruff check --fix .

# ===========================================
# Build
# ===========================================

# Build all components
build: build-rust build-ui

# Build heracles-core
build-rust:
	cd heracles-core && cargo build --release

# Build Python wheel
build-wheel:
	cd heracles-core && maturin build --release

# Build UI
build-ui:
	cd heracles-ui && bun run build

# ===========================================
# Development Utilities
# ===========================================

# Show LDAP tree
ldap-tree:
	docker exec heracles-ldap ldapsearch -x -H ldap://localhost -b "dc=heracles,dc=local" -D "cn=admin,dc=heracles,dc=local" -w admin_secret "(objectClass=*)" dn

# Connect to PostgreSQL
psql:
	docker exec -it heracles-postgres psql -U heracles -d heracles

# Connect to Redis CLI
redis-cli:
	docker exec -it heracles-redis redis-cli -a redis_secret

# Watch Rust tests
watch-rust:
	cd heracles-core && cargo watch -x test

# API dev server (local, not Docker)
api-dev:
	cd heracles-api && uvicorn heracles_api.main:app --reload --host 0.0.0.0 --port 8000
