# ============================================================================
# Heracles - Docker
# ============================================================================

.PHONY: up down logs clean build bootstrap schemas shell

# Start all services
up:
	@echo "🚀 Starting Heracles..."
	@$(COMPOSE) --profile full up -d
	@echo ""
	@echo "✅ Services running:"
	@echo "   API:  http://localhost:$(API_PORT)"
	@echo "   UI:   http://localhost:$(UI_PORT)"
	@echo "   LDAP: http://localhost:8080 (phpLDAPadmin)"

# Start infrastructure only (no API/UI)
up-infra:
	@echo "🔧 Starting infrastructure..."
	@$(COMPOSE) up -d ldap postgres redis phpldapadmin
	@echo "✅ Infrastructure ready"

# Stop all services
down:
	@echo "⏹️  Stopping services..."
	@$(COMPOSE) --profile full --profile prod down
	@echo "✅ Stopped"

# View logs (optionally: make logs s=api)
logs:
ifdef s
	@$(COMPOSE) logs -f $(s)
else
	@$(COMPOSE) logs -f
endif

# Remove containers and volumes
clean:
	@echo "🧹 Cleaning Docker..."
	@$(COMPOSE) --profile full --profile prod down -v 2>/dev/null || true
	@echo "✅ Cleaned"

# Build/rebuild images
build:
	@echo "🔨 Building images..."
	@$(COMPOSE) --profile full build
	@echo "✅ Built"

# Rebuild without cache
rebuild:
	@echo "🔨 Rebuilding images (no cache)..."
	@$(COMPOSE) --profile full build --no-cache
	@echo "✅ Rebuilt"

# Initialize LDAP structure
bootstrap:
	@echo "📦 Bootstrapping LDAP..."
	@./scripts/ldap-bootstrap.sh init
	@echo "✅ LDAP initialized"

# Load LDAP schemas
schemas:
	@echo "📋 Loading schemas..."
	@./scripts/ldap-bootstrap.sh schemas
	@echo "✅ Schemas loaded"

# Shell into a container (make shell s=api)
shell:
ifndef s
	@echo "Usage: make shell s=<service>"
	@echo "Services: api, ui, ldap, postgres, redis"
else
	@$(COMPOSE) exec $(s) sh -c 'bash 2>/dev/null || sh'
endif

# Quick access shells
shell-db:
	@$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-heracles} -d $${POSTGRES_DB:-heracles}

shell-redis:
	@$(COMPOSE) exec redis redis-cli -a $${REDIS_PASSWORD:-redis_secret}

shell-ldap:
	@$(COMPOSE) exec ldap ldapsearch -x -H ldap://localhost -b "$(LDAP_BASE_DN)" -D "$(LDAP_ADMIN_DN)" -w "$(LDAP_ADMIN_PW)" "(objectClass=*)" dn
