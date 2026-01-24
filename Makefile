# ============================================================================
#                              HERACLES MAKEFILE
# ============================================================================
# Identity Management System
#
# Usage: make help
# ============================================================================

# Include configuration first
include mk/config.mk

# Include module makefiles
include mk/docker.mk
include mk/api.mk
include mk/ui.mk
include mk/core.mk
include mk/plugins.mk
include mk/dev.mk
include mk/help.mk

# Legacy alias targets for backward compatibility
test-rust: core-test
test-api: api-test
build-rust: core
build-ui-legacy: ui-build

# Legacy lint targets
lint-rust: core-lint
lint-python: api-lint plugins-lint
lint-ui: ui-lint

# Legacy format targets
format-rust: core-format
format-python: api-format plugins-format

# ===========================================
# Development Utilities
# ===========================================

# Show LDAP tree
ldap-tree:
	docker exec heracles-ldap ldapsearch -x -H ldap://localhost -b "$(LDAP_BASE_DN)" -D "$(LDAP_ADMIN_DN)" -w "$(LDAP_ADMIN_PASSWORD)" "(objectClass=*)" dn

# Connect to PostgreSQL
psql:
	docker exec -it heracles-postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)

# Connect to Redis CLI
redis-cli:
	docker exec -it heracles-redis redis-cli -a $(REDIS_PASSWORD)

# Watch Rust tests
watch-rust:
	cd heracles-core && cargo watch -x test
