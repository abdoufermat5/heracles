# ============================================================================
# Heracles - Help
# ============================================================================

.PHONY: help
.DEFAULT_GOAL := help

help:
	@echo ""
	@echo "╔═══════════════════════════════════════════════════════════╗"
	@echo "║                        HERACLES                           ║"
	@echo "║                  Identity Management                      ║"
	@echo "╚═══════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "DOCKER"
	@echo "   make up              Start all services"
	@echo "   make up-infra        Start infrastructure only"
	@echo "   make down            Stop all services"
	@echo "   make logs            View logs (s=api for specific)"
	@echo "   make build           Build images"
	@echo "   make rebuild         Rebuild without cache"
	@echo "   make clean           Remove containers & volumes"
	@echo ""
	@echo "SETUP"
	@echo "   make bootstrap       Initialize LDAP structure"
	@echo "   make schemas         Load LDAP schemas"
	@echo ""
	@echo "SHELLS"
	@echo "   make shell s=<svc>   Shell into service"
	@echo "   make shell-db        PostgreSQL shell"
	@echo "   make shell-redis     Redis CLI"
	@echo "   make shell-ldap      LDAP search"
	@echo ""
	@echo "DEMO (Vagrant)"
	@echo "   make demo            Full demo setup"
	@echo "   make demo-up         Start VMs"
	@echo "   make demo-down       Stop VMs"
	@echo "   make demo-ssh vm=X   SSH into VM"
	@echo "   make demo-status     Show VM status"
	@echo "   make demo-clean      Destroy VMs"
	@echo ""
