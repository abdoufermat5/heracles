# ============================================================================
# Heracles - Rust Core
# ============================================================================
# Commands for building and testing the Rust core library

.PHONY: core core-build core-test core-lint core-clean

# Build Rust core library (debug)
core:
	$(call log_info,Building Rust core library...)
	@cd $(CORE_DIR) && cargo build
	$(call log_success,Rust core built!)

# Build Rust core library (release)
core-release:
	$(call log_info,Building Rust core library (release)...)
	@cd $(CORE_DIR) && cargo build --release
	$(call log_success,Rust core release built!)

# Run Rust core tests
core-test:
	$(call log_info,Running Rust core tests...)
	@cd $(CORE_DIR) && cargo test
	$(call log_success,Rust core tests passed!)

# Lint Rust code
core-lint:
	$(call log_info,Linting Rust core...)
	@cd $(CORE_DIR) && cargo clippy -- -D warnings
	$(call log_success,Rust lint passed!)

# Format Rust code
core-format:
	$(call log_info,Formatting Rust code...)
	@cd $(CORE_DIR) && cargo fmt
	$(call log_success,Rust code formatted!)

# Check Rust formatting
core-format-check:
	$(call log_info,Checking Rust formatting...)
	@cd $(CORE_DIR) && cargo fmt --check
	$(call log_success,Rust formatting OK!)

# Clean Rust build artifacts
core-clean:
	$(call log_info,Cleaning Rust build artifacts...)
	@cd $(CORE_DIR) && cargo clean
	$(call log_success,Rust build cleaned!)

# Generate Rust documentation
core-doc:
	$(call log_info,Generating Rust documentation...)
	@cd $(CORE_DIR) && cargo doc --open
	$(call log_success,Documentation generated!)
