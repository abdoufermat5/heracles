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

# ============================================================================
# Vagrant Demo Environment
# ============================================================================

VAGRANT_DIR := demo

.PHONY: demo-up demo-down demo-status demo-ssh-server demo-ssh-workstation demo-provision demo-clean

# Start demo VMs
demo-up:
	$(call log_info,Starting Vagrant demo VMs...)
	@cd demo && vagrant up
	$(call log_success,Demo VMs started!)
	$(call log_info,VMs available:)
	@echo "  - server1:      192.168.56.10"
	@echo "  - workstation1: 192.168.56.11"
	@echo ""
	@echo "SSH commands:"
	@echo "  make demo-ssh-server"
	@echo "  make demo-ssh-workstation"

# Stop demo VMs
demo-down:
	$(call log_info,Stopping Vagrant demo VMs...)
	@cd demo && vagrant halt
	$(call log_success,Demo VMs stopped!)

# Show demo VM status
demo-status:
	@cd demo && vagrant status

# SSH into server1
demo-ssh-server:
	@cd demo && vagrant ssh server1

# SSH into workstation1
demo-ssh-workstation:
	@cd demo && vagrant ssh workstation1

# Re-provision VMs (rerun setup scripts)
demo-provision:
	$(call log_info,Re-provisioning Vagrant demo VMs...)
	@cd demo && vagrant provision
	$(call log_success,Demo VMs re-provisioned!)

# Destroy and recreate VMs
demo-clean:
	$(call log_warning,Destroying Vagrant demo VMs...)
	@cd demo && vagrant destroy -f 2>/dev/null || true
	@rm -rf demo/keys 2>/dev/null || true
	$(call log_success,Demo VMs and keys removed!)

# Generate SSH keys for demo
demo-keys:
	$(call log_info,Generating demo SSH keys...)
	@cd demo && ./scripts/generate-keys.sh
	$(call log_success,Demo SSH keys generated!)

# Setup demo users via API
demo-users:
	$(call log_info,Setting up demo users via API...)
	@cd demo && ./scripts/setup-demo-users.sh
	$(call log_success,Demo users configured!)

# Full demo setup: infra + bootstrap + schemas + VMs + users
demo: dev-infra
	$(call log_info,Setting up complete demo environment...)
	@sleep 5
	@$(MAKE) bootstrap || true
	@$(MAKE) ldap-schemas || true
	@$(MAKE) demo-keys
	@$(MAKE) demo-up
	@sleep 10
	@$(MAKE) demo-users
	$(call log_success,Demo environment ready!)
