# ============================================================================
# Heracles - Demo Environment (Vagrant)
# ============================================================================

# Default to Libvirt (KVM) instead of VirtualBox
export VAGRANT_DEFAULT_PROVIDER ?= libvirt
.PHONY: demo demo-up demo-down demo-ssh demo-clean demo-provision

# Full demo setup: containers + bootstrap + VMs + users
demo: up
	@echo "Setting up demo environment..."
	@sleep 5
	@./scripts/ldap-bootstrap.sh all
	@echo "🌱 Seeding default configuration..."
	@$(COMPOSE) exec api python -m heracles_api.core.seed
	@cd $(DEMO_DIR) && ./scripts/generate-keys.sh 2>/dev/null || true
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant up"
	@sleep 10
	@cd $(DEMO_DIR) && ./scripts/setup-demo-users.sh 2>/dev/null || true
	@echo ""
	@echo "Demo ready!"
	@echo "   VMs: server1 (192.168.56.10), workstation1 (192.168.56.11)"
	@echo "   SSH: make demo-ssh vm=server1"

# Start VMs only
demo-up:
	@echo "Starting demo VMs..."
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant up"
	@echo "VMs started"

# Stop VMs
demo-down:
	@echo "Stopping demo VMs..."
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant halt"
	@echo "VMs stopped"

# SSH into a VM (make demo-ssh vm=server1)
demo-ssh:
ifndef vm
	@echo "Usage: make demo-ssh vm=<name>"
	@echo "VMs: server1, workstation1, ns1, dhcp1"
else
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant ssh $(vm)"
endif

# Re-provision VMs
demo-provision:
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant provision"

# Destroy VMs and keys
demo-clean:
	@echo "Destroying demo VMs..."
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant destroy -f" 2>/dev/null || true
	@rm -rf $(DEMO_DIR)/keys 2>/dev/null || true
	@echo "Demo cleaned"

# Show VM status
demo-status:
	@cd $(DEMO_DIR) && sg libvirt -c "vagrant status"
