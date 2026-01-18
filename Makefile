# Heracles Development Makefile
# =============================

.PHONY: help dev dev-infra stop clean test test-rust test-api lint format build

# Default target
help:
	@echo "Heracles Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Infrastructure:"
	@echo "  make dev-infra     - Start LDAP, PostgreSQL, Redis (minimal setup)"
	@echo "  make dev           - Start full development environment"
	@echo "  make stop          - Stop all services"
	@echo "  make clean         - Stop and remove all volumes"
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
	@echo ""

# ===========================================
# Infrastructure
# ===========================================

# Start minimal infrastructure (LDAP, PostgreSQL, Redis)
dev-infra:
	docker compose up -d ldap postgres redis phpldapadmin
	@echo ""
	@echo "Infrastructure started!"
	@echo "  - LDAP:          ldap://localhost:389"
	@echo "  - phpLDAPadmin:  http://localhost:8080"
	@echo "  - PostgreSQL:    localhost:5432"
	@echo "  - Redis:         localhost:6379"
	@echo ""
	@echo "LDAP Admin: cn=admin,dc=heracles,dc=local / admin_secret"

# Start full development environment
dev:
	docker compose --profile full up -d
	@echo ""
	@echo "Full environment started!"
	@echo "  - API:           http://localhost:8000"
	@echo "  - UI:            http://localhost:5173"
	@echo "  - phpLDAPadmin:  http://localhost:8080"

# Stop all services
stop:
	docker compose --profile full down

# Clean all volumes
clean:
	docker compose --profile full down -v
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
# Code Quality
# ===========================================

# Run all linters
lint: lint-rust lint-python

lint-rust:
	cd heracles-core && cargo clippy -- -D warnings

lint-python:
	cd heracles-api && ruff check .
	cd heracles-api && mypy heracles_api

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
build: build-rust

# Build heracles-core
build-rust:
	cd heracles-core && cargo build --release

# Build Python wheel
build-wheel:
	cd heracles-core && maturin build --release

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
