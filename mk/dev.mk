# ============================================================================
# Heracles - Development Workflow
# ============================================================================
# Combined commands for common development workflows

.PHONY: dev-api dev-ui install test lint format check

# Start API development (infra + API server)
dev-api: dev-infra
	$(call log_info,Waiting for infrastructure...)
	@sleep 3
	@$(MAKE) api

# Start UI development (assumes API is running elsewhere)
dev-ui:
	@$(MAKE) ui

# Install all dependencies
install: api-install ui-install plugins-install
	$(call log_success,All dependencies installed!)

# Run all tests
test: api-test plugins-test ui-test core-test
	$(call log_success,All tests passed!)

# Lint all code
lint: api-lint plugins-lint ui-lint core-lint
	$(call log_success,All linting passed!)

# Format all code
format: api-format plugins-format ui-format core-format
	$(call log_success,All code formatted!)

# Full check (lint + typecheck + test)
check: lint api-typecheck ui-typecheck plugins-typecheck test
	$(call log_success,All checks passed!)

# Quick check (lint only, no tests)
check-quick: lint
	$(call log_success,Quick check passed!)

# Build everything for production
build: ui-build core-release
	$(call log_success,Production build complete!)
