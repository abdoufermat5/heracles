# ============================================================================
# Heracles - Setup & Installation
# ============================================================================

.PHONY: setup install quick-start env-check pki

# Full interactive setup (wizard)
setup: ## Interactive setup wizard — configure, build, and start Heracles
	@bash scripts/install.sh

# Alias for setup
install: setup ## Alias for 'make setup'

# Quick start (skip wizard, use defaults or existing .env)
quick-start: env-check up-infra _wait-infra bootstrap schemas up seed ## Quick non-interactive start
	@echo ""
	@echo "✅ Heracles is running!"
	@echo "   UI:  http://localhost:$(UI_PORT)"
	@echo "   API: http://localhost:$(API_PORT)/api/v1"

# Check .env exists
env-check:
	@if [ ! -f .env ]; then \
		echo "⚠️  No .env file found."; \
		if [ -f .env.production.example ]; then \
			echo "   Creating .env from .env.production.example..."; \
			cp .env.production.example .env; \
			echo "   ⚠️  Edit .env and set all [CHANGE] values before production use!"; \
		else \
			echo "   Run 'make setup' for the interactive wizard."; \
			exit 1; \
		fi \
	fi

# Wait for infrastructure to be ready
_wait-infra:
	@echo "⏳ Waiting for infrastructure..."
	@for i in $$(seq 1 30); do \
		docker compose exec -T postgres pg_isready -q 2>/dev/null && break; \
		sleep 2; \
	done
	@echo "✅ Infrastructure ready"

# Generate dev TLS certificates
pki:
	@echo "🔐 Generating development TLS certificates..."
	@mkdir -p pki
	@if [ -x scripts/dev-pki/generate.sh ]; then \
		bash scripts/dev-pki/generate.sh; \
	else \
		echo "   Generating self-signed cert..."; \
		openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
			-keyout pki/server.key -out pki/server.crt \
			-subj "/CN=heracles.local/O=Heracles" 2>/dev/null; \
	fi
	@echo "✅ TLS certificates ready (pki/)"

# Full release readiness check (tests + builds + changelogs)
release-check: ## Full release readiness check (tests, builds, changelogs)
	@echo "🔍 Release Validation"
	@echo "─────────────────────"
	@echo ""
	@echo "📋 Versions:"
	@$(MAKE) --no-print-directory version
	@echo ""
	@echo "🧪 Running tests..."
	@docker compose exec -T api sh -c "PYTHONPATH=/app pytest --tb=short -q" 2>/dev/null && \
		echo "✅ API tests passed" || echo "❌ API tests failed"
	@cd $(CORE_DIR) && cargo test --quiet 2>/dev/null && \
		echo "✅ Core tests passed" || echo "❌ Core tests failed"
	@echo ""
	@echo "🐳 Docker build check..."
	@docker compose --profile full build --quiet 2>/dev/null && \
		echo "✅ Docker images build OK" || echo "❌ Docker build failed"
	@echo ""
	@echo "📝 Checking changelogs..."
	@for comp in $(API_DIR) $(UI_DIR) $(CORE_DIR) $(PLUGINS_DIR); do \
		if [ -f "$$comp/CHANGELOG.md" ]; then \
			echo "  ✅ $$comp/CHANGELOG.md exists"; \
		else \
			echo "  ❌ $$comp/CHANGELOG.md missing"; \
		fi; \
	done
	@echo ""
	@echo "✅ Release validation complete"
