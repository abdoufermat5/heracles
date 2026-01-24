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

# Stop all services
stop:
	$(call log_info,Stopping all services...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) $(DOCKER_PROFILE_PROD) down
	$(call log_success,All services stopped)

# Clean all volumes
clean:
	$(call log_warning,Removing all containers and volumes...)
	$(DOCKER_COMPOSE) $(DOCKER_PROFILE_FULL) $(DOCKER_PROFILE_PROD) down -v
	$(call log_success,All volumes removed)

# View logs
logs:
	$(DOCKER_COMPOSE) logs -f

logs-api:
	$(DOCKER_COMPOSE) logs -f api

logs-ui:
	$(DOCKER_COMPOSE) logs -f ui

logs-ldap:
	$(DOCKER_COMPOSE) logs -f ldap
