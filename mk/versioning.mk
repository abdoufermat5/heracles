# ============================================================================
#                         VERSIONING TARGETS
# ============================================================================
# Version management across all Heracles components
#
# Usage:
#   make version              - Show all component versions
#   make bump-api-patch       - Bump API patch version (0.8.0 -> 0.8.1)
#   make bump-api-minor       - Bump API minor version (0.8.0 -> 0.9.0)
#   make bump-api-major       - Bump API major version (0.8.0 -> 1.0.0)
#   make bump-ui-patch        - Same for UI
#   make bump-core-patch      - Same for Core
#   make bump-plugins-patch   - Same for Plugins package
#   make release-prep         - Prepare release (update dates, validate)
#   make changelog            - Show recent changelog entries
# ============================================================================

# Version files
API_VERSION_FILE := $(API_DIR)/heracles_api/__init__.py
UI_VERSION_FILE := $(UI_DIR)/package.json
CORE_VERSION_FILE := $(CORE_DIR)/Cargo.toml
PLUGINS_VERSION_FILE := $(PLUGINS_DIR)/pyproject.toml

# Extract current versions
.PHONY: version
version: ## Show all component versions
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║                    HERACLES VERSIONS                         ║"
	@echo "╠══════════════════════════════════════════════════════════════╣"
	@printf "║ %-15s │ %-42s ║\n" "Component" "Version"
	@echo "╠─────────────────┼────────────────────────────────────────────╣"
	@printf "║ %-15s │ %-42s ║\n" "heracles-api" "$$(grep -oP '__version__\s*=\s*"\K[^"]+' $(API_VERSION_FILE))"
	@printf "║ %-15s │ %-42s ║\n" "heracles-ui" "$$(grep -oP '"version":\s*"\K[^"]+' $(UI_VERSION_FILE))"
	@printf "║ %-15s │ %-42s ║\n" "heracles-core" "$$(grep -oP '^version\s*=\s*"\K[^"]+' $(CORE_VERSION_FILE))"
	@printf "║ %-15s │ %-42s ║\n" "heracles-plugins" "$$(grep -oP '^version\s*=\s*"\K[^"]+' $(PLUGINS_VERSION_FILE))"
	@echo "╚══════════════════════════════════════════════════════════════╝"

# Version extraction helpers
define get_api_version
$(shell grep -oP '__version__\s*=\s*"\K[^"]+' $(API_VERSION_FILE))
endef

define get_ui_version
$(shell grep -oP '"version":\s*"\K[^"]+' $(UI_VERSION_FILE))
endef

define get_core_version
$(shell grep -oP '^version\s*=\s*"\K[^"]+' $(CORE_VERSION_FILE))
endef

define get_plugins_version
$(shell grep -oP '^version\s*=\s*"\K[^"]+' $(PLUGINS_VERSION_FILE))
endef

# ============================================================================
# API Version Bumping
# ============================================================================

.PHONY: bump-api-patch bump-api-minor bump-api-major
bump-api-patch: ## Bump API patch version (0.8.0-beta -> 0.8.1-beta)
	@./scripts/bump-version.sh api patch

bump-api-minor: ## Bump API minor version (0.8.0-beta -> 0.9.0-beta)
	@./scripts/bump-version.sh api minor

bump-api-major: ## Bump API major version (0.8.0-beta -> 1.0.0)
	@./scripts/bump-version.sh api major

# ============================================================================
# UI Version Bumping
# ============================================================================

.PHONY: bump-ui-patch bump-ui-minor bump-ui-major
bump-ui-patch: ## Bump UI patch version
	@./scripts/bump-version.sh ui patch

bump-ui-minor: ## Bump UI minor version
	@./scripts/bump-version.sh ui minor

bump-ui-major: ## Bump UI major version
	@./scripts/bump-version.sh ui major

# ============================================================================
# Core Version Bumping
# ============================================================================

.PHONY: bump-core-patch bump-core-minor bump-core-major
bump-core-patch: ## Bump Core patch version
	@./scripts/bump-version.sh core patch

bump-core-minor: ## Bump Core minor version
	@./scripts/bump-version.sh core minor

bump-core-major: ## Bump Core major version
	@./scripts/bump-version.sh core major

# ============================================================================
# Plugins Version Bumping
# ============================================================================

.PHONY: bump-plugins-patch bump-plugins-minor bump-plugins-major
bump-plugins-patch: ## Bump Plugins package patch version
	@./scripts/bump-version.sh plugins patch

bump-plugins-minor: ## Bump Plugins package minor version
	@./scripts/bump-version.sh plugins minor

bump-plugins-major: ## Bump Plugins package major version
	@./scripts/bump-version.sh plugins major

# ============================================================================
# Synchronized Version Bumping (all components at once)
# ============================================================================

.PHONY: bump-all-patch bump-all-minor bump-all-major
bump-all-patch: ## Bump patch version for all components
	@./scripts/bump-version.sh api patch
	@./scripts/bump-version.sh ui patch
	@./scripts/bump-version.sh plugins patch
	@echo "✓ All components bumped to new patch version"
	@$(MAKE) version

bump-all-minor: ## Bump minor version for all components
	@./scripts/bump-version.sh api minor
	@./scripts/bump-version.sh ui minor
	@./scripts/bump-version.sh plugins minor
	@echo "✓ All components bumped to new minor version"
	@$(MAKE) version

bump-all-major: ## Bump major version for all components (removes pre-release suffix)
	@./scripts/bump-version.sh api major
	@./scripts/bump-version.sh ui major
	@./scripts/bump-version.sh core major
	@./scripts/bump-version.sh plugins major
	@echo "✓ All components bumped to new major version"
	@$(MAKE) version

# ============================================================================
# Release Preparation
# ============================================================================

.PHONY: release-prep release-validate tag-release
release-prep: ## Prepare for release (validate, update dates)
	@echo "📋 Preparing release..."
	@$(MAKE) release-validate
	@echo "📅 Update CHANGELOG dates..."
	@date_today=$$(date +%Y-%m-%d); \
	for changelog in $(API_DIR)/CHANGELOG.md $(UI_DIR)/CHANGELOG.md $(CORE_DIR)/CHANGELOG.md $(PLUGINS_DIR)/CHANGELOG.md; do \
		if [ -f "$$changelog" ]; then \
			sed -i "s/\[Unreleased\]/[Unreleased]\n\n## [$$($(MAKE) -s version-api)] - $$date_today/" "$$changelog" 2>/dev/null || true; \
		fi; \
	done
	@echo "✓ Release preparation complete"
	@$(MAKE) version

release-validate: ## Validate versions are ready for release
	@echo "🔍 Validating versions..."
	@api_ver=$(call get_api_version); \
	ui_ver=$(call get_ui_version); \
	plugins_ver=$(call get_plugins_version); \
	errors=0; \
	if [ -z "$$api_ver" ]; then echo "❌ API version not found"; errors=1; fi; \
	if [ -z "$$ui_ver" ]; then echo "❌ UI version not found"; errors=1; fi; \
	if [ -z "$$plugins_ver" ]; then echo "❌ Plugins version not found"; errors=1; fi; \
	if [ "$$errors" -eq 1 ]; then exit 1; fi; \
	echo "✓ All versions found"

tag-release: ## Create git tags for all components
	@echo "🏷️  Creating release tags..."
	@api_ver=$(call get_api_version); \
	ui_ver=$(call get_ui_version); \
	core_ver=$(call get_core_version); \
	plugins_ver=$(call get_plugins_version); \
	git tag -a "heracles-api/v$$api_ver" -m "Release heracles-api v$$api_ver"; \
	git tag -a "heracles-ui/v$$ui_ver" -m "Release heracles-ui v$$ui_ver"; \
	git tag -a "heracles-core/v$$core_ver" -m "Release heracles-core v$$core_ver"; \
	git tag -a "heracles-plugins/v$$plugins_ver" -m "Release heracles-plugins v$$plugins_ver"; \
	echo "✓ Tags created:"; \
	echo "  - heracles-api/v$$api_ver"; \
	echo "  - heracles-ui/v$$ui_ver"; \
	echo "  - heracles-core/v$$core_ver"; \
	echo "  - heracles-plugins/v$$plugins_ver"

# ============================================================================
# Changelog
# ============================================================================

.PHONY: changelog
changelog: ## Show recent changelog entries
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "                     RECENT CHANGES"
	@echo "═══════════════════════════════════════════════════════════════"
	@for component in api ui core plugins; do \
		case $$component in \
			api) file="$(API_DIR)/CHANGELOG.md" ;; \
			ui) file="$(UI_DIR)/CHANGELOG.md" ;; \
			core) file="$(CORE_DIR)/CHANGELOG.md" ;; \
			plugins) file="$(PLUGINS_DIR)/CHANGELOG.md" ;; \
		esac; \
		if [ -f "$$file" ]; then \
			echo ""; \
			echo "📦 heracles-$$component:"; \
			head -50 "$$file" | tail -45; \
		fi; \
	done

# Helper targets for getting individual versions (for scripting)
.PHONY: version-api version-ui version-core version-plugins
version-api:
	@echo $(call get_api_version)

version-ui:
	@echo $(call get_ui_version)

version-core:
	@echo $(call get_core_version)

version-plugins:
	@echo $(call get_plugins_version)
