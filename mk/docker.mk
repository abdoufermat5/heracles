# ============================================================================
# Heracles - Docker Infrastructure
# ============================================================================
# Commands for managing Docker-based infrastructure

.PHONY: dev-infra dev prod stop clean bootstrap logs

# Start minimal infrastructure (LDAP, PostgreSQL, Redis)
dev-infra:
	$(call log_info,Starting infrastructure services...)
	$(DOCKER_COMPOSE) up -d ldap postgres redis phpldapadmin
	@echo ""
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo ""
	$(call log_success,Infrastructure started!)
	@echo ""
	@echo "  📂 LDAP:          ldap://localhost:$(LDAP_PORT)"
	@echo "  🔧 phpLDAPadmin:  http://localhost:$(PHPLDAPADMIN_PORT)"
	@echo "  🐘 PostgreSQL:    localhost:$(POSTGRES_PORT)"
	@echo "  🔴 Redis:         localhost:$(REDIS_PORT)"
	@echo ""
	@echo "  LDAP Admin: $(LDAP_ADMIN_DN) / $(LDAP_ADMIN_PW)"
	@echo ""
	@echo "💡 Run 'make bootstrap' to initialize LDAP structure"

# Initialize LDAP with base structure
bootstrap:
	$(call log_info,Bootstrapping LDAP structure...)
	@./scripts/ldap-bootstrap.sh
	$(call log_success,LDAP bootstrap complete!)

# Load custom LDAP schemas (heracles-aux, openssh-lpk, sudo)
ldap-schemas:
	$(call log_info,Loading custom LDAP schemas...)
	@./scripts/ldap-load-schemas.sh
	$(call log_success,LDAP schemas loaded!)

# List available and loaded LDAP schemas
ldap-schemas-list:
	@./scripts/ldap-load-schemas.sh --list

# Start full development environment (all services in Docker)
dev:
	$(call log_info,Starting full development environment...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) up -d
	@echo ""
	$(call log_success,Full environment started!)
	@echo ""
	@echo "  🚀 API:           http://localhost:$(API_PORT)"
	@echo "  🖥️  UI:            http://localhost:$(UI_PORT)"
	@echo "  🔧 phpLDAPadmin:  http://localhost:$(PHPLDAPADMIN_PORT)"

# Start production environment
prod:
	$(call log_info,Starting production environment...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_PROD) up -d --build
	@echo ""
	$(call log_success,Production environment started!)
	@echo ""
	@echo "  🖥️  UI:   http://localhost:80"
	@echo "  🚀 API:  http://localhost:$(API_PORT)"

# Stop all services (Docker + Vagrant)
stop:
	$(call log_info,Stopping all services...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) $(DOCKER_PROFILE_PROD) down
	@if [ -f demo/Vagrantfile ] && command -v vagrant >/dev/null 2>&1; then \
		echo "Stopping Vagrant VMs..."; \
		cd demo && vagrant halt 2>/dev/null || true; \
	fi
	$(call log_success,All services stopped!)

# Stop Docker only
stop-docker:
	$(call log_info,Stopping Docker services...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) $(DOCKER_PROFILE_PROD) down
	$(call log_success,Docker services stopped!)

# Clean everything (Docker + Vagrant + build artifacts)
clean:
	$(call log_warning,Removing all containers, volumes, VMs and build artifacts...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) $(DOCKER_PROFILE_PROD) down -v 2>/dev/null || true
	@if [ -f demo/Vagrantfile ] && command -v vagrant >/dev/null 2>&1; then \
		echo "Destroying Vagrant VMs..."; \
		cd demo && vagrant destroy -f 2>/dev/null || true; \
	fi
	@rm -rf demo/keys 2>/dev/null || true
	$(call log_success,All cleaned!)

# Clean Docker only
clean-docker:
	$(call log_warning,Removing all Docker containers and volumes...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) $(DOCKER_PROFILE_PROD) down -v
	$(call log_success,Docker volumes removed!)

# ===========================================
# Build Commands
# ===========================================

# Build all Docker images
docker-build:
	$(call log_info,Building all Docker images...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) build
	$(call log_success,All images built!)

# Build API image
docker-build-api:
	$(call log_info,Building API Docker image...)
	$(DOCKER_COMPOSE) build api
	$(call log_success,API image built!)

# Build UI image
docker-build-ui:
	$(call log_info,Building UI Docker image...)
	$(DOCKER_COMPOSE) build ui
	$(call log_success,UI image built!)

# Rebuild all images (no cache)
docker-rebuild:
	$(call log_info,Rebuilding all Docker images (no cache)...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) build --no-cache
	$(call log_success,All images rebuilt!)

# Rebuild and restart services
docker-rebuild-restart: docker-rebuild
	$(call log_info,Restarting services with new images...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) up -d
	$(call log_success,Services restarted!)

# Pull latest base images
docker-pull:
	$(call log_info,Pulling latest base images...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) pull
	$(call log_success,Images pulled!)

# ===========================================
# Logs
# ===========================================

# View logs
logs:
	$(DOCKER_COMPOSE) logs -f

logs-api:
	$(DOCKER_COMPOSE) logs -f api

logs-ui:
	$(DOCKER_COMPOSE) logs -f ui

logs-ldap:
	$(DOCKER_COMPOSE) logs -f ldap
