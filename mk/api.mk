# ============================================================================
# Heracles - API Development
# ============================================================================
# Commands for developing and running the Python API

.PHONY: api api-install api-test api-lint api-format api-shell

# Start API development server (with hot reload)
api:
	$(call log_info,Starting API development server...)
	@cd $(API_DIR) && python -m uvicorn heracles_api.main:app \
		--reload \
		--host 0.0.0.0 \
		--port $(API_PORT) \
		--log-level debug

# Install API dependencies
api-install:
	$(call log_info,Installing API dependencies...)
	@cd $(API_DIR) && pip install -r requirements.txt
	@cd $(PLUGINS_DIR) && pip install -e .
	$(call log_success,API dependencies installed)

# Run API tests
api-test:
	$(call log_info,Running API tests...)
	@cd $(API_DIR) && python -m pytest -v --tb=short
	$(call log_success,API tests passed!)

# Run API tests with coverage
api-test-cov:
	$(call log_info,Running API tests with coverage...)
	@cd $(API_DIR) && python -m pytest -v --tb=short --cov=heracles_api --cov-report=html
	$(call log_success,Coverage report generated!)
	@echo "  📊 Report: $(API_DIR)/htmlcov/index.html"

# Lint API code
api-lint:
	$(call log_info,Linting API code...)
	@cd $(API_DIR) && python -m ruff check .
	@cd $(PLUGINS_DIR) && python -m ruff check .
	$(call log_success,API lint passed!)

# Format API code
api-format:
	$(call log_info,Formatting API code...)
	@cd $(API_DIR) && python -m ruff format .
	@cd $(PLUGINS_DIR) && python -m ruff format .
	$(call log_success,API code formatted!)

# Type check API code
api-typecheck:
	$(call log_info,Type checking API code...)
	@cd $(API_DIR) && python -m mypy heracles_api
	$(call log_success,API type check passed!)

# Open Python shell with API context
api-shell:
	$(call log_info,Opening Python shell...)
	@cd $(API_DIR) && python -c "from heracles_api.main import *; import IPython; IPython.embed()"
