# ============================================================================
# Heracles - Plugins Development
# ============================================================================
# Commands for managing plugins (POSIX, etc.)

.PHONY: plugins-install plugins-test plugins-lint plugins-format

# Install plugins in development mode
plugins-install:
	$(call log_info,Installing plugins in development mode...)
	@cd $(PLUGINS_DIR) && pip install -e ".[dev]"
	$(call log_success,Plugins installed!)

# Run plugins tests
plugins-test:
	$(call log_info,Running plugins tests...)
	@cd $(PLUGINS_DIR) && python -m pytest -v --tb=short
	$(call log_success,Plugins tests passed!)

# Lint plugins code
plugins-lint:
	$(call log_info,Linting plugins code...)
	@cd $(PLUGINS_DIR) && python -m ruff check .
	$(call log_success,Plugins lint passed!)

# Format plugins code
plugins-format:
	$(call log_info,Formatting plugins code...)
	@cd $(PLUGINS_DIR) && python -m ruff format .
	$(call log_success,Plugins code formatted!)

# Type check plugins
plugins-typecheck:
	$(call log_info,Type checking plugins...)
	@cd $(PLUGINS_DIR) && python -m mypy heracles_plugins
	$(call log_success,Plugins type check passed!)
