# ============================================================================
# Heracles - UI Development
# ============================================================================
# Commands for developing and building the React UI

.PHONY: ui ui-install ui-build ui-lint ui-format ui-test

# Start UI development server (with hot reload)
ui:
	$(call log_info,Starting UI development server...)
	@cd $(UI_DIR) && bun run dev --host 0.0.0.0 --port $(UI_PORT)

# Install UI dependencies
ui-install:
	$(call log_info,Installing UI dependencies...)
	@cd $(UI_DIR) && bun install
	$(call log_success,UI dependencies installed)

# Build UI for production
ui-build:
	$(call log_info,Building UI for production...)
	@cd $(UI_DIR) && bun run build
	$(call log_success,UI build complete!)
	@echo "  📦 Output: $(UI_DIR)/dist"

# Preview production build
ui-preview:
	$(call log_info,Previewing production build...)
	@cd $(UI_DIR) && bun run preview --host 0.0.0.0 --port $(UI_PORT)

# Lint UI code
ui-lint:
	$(call log_info,Linting UI code...)
	@cd $(UI_DIR) && bun run lint
	$(call log_success,UI lint passed!)

# Format UI code
ui-format:
	$(call log_info,Formatting UI code...)
	@cd $(UI_DIR) && bun run format
	$(call log_success,UI code formatted!)

# Type check UI code
ui-typecheck:
	$(call log_info,Type checking UI code...)
	@cd $(UI_DIR) && bun run typecheck
	$(call log_success,UI type check passed!)

# Run UI tests
ui-test:
	$(call log_info,Running UI tests...)
	@cd $(UI_DIR) && bun run test
	$(call log_success,UI tests passed!)

# Run UI tests with coverage
ui-test-cov:
	$(call log_info,Running UI tests with coverage...)
	@cd $(UI_DIR) && bun run test:coverage
	$(call log_success,Coverage report generated!)
