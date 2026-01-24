# ============================================================================
# Heracles - Configuration
# ============================================================================
# Common variables and settings used across all makefiles

# Load environment from .env file if it exists
-include .env
export

# Project directories
PROJECT_ROOT := $(dir $(lastword $(MAKEFILE_LIST)))/..
API_DIR := heracles-api
UI_DIR := heracles-ui
CORE_DIR := heracles-core
PLUGINS_DIR := heracles_plugins

# Docker settings
DOCKER_COMPOSE := docker compose
DOCKER_PROFILE_FULL := --profile full
DOCKER_PROFILE_PROD := --profile prod

# LDAP settings (defaults, can be overridden by .env)
LDAP_BASE_DN ?= dc=heracles,dc=local
LDAP_ADMIN_DN ?= cn=admin,$(LDAP_BASE_DN)
LDAP_ADMIN_PW ?= admin_secret

# Port settings (defaults, can be overridden by .env)
API_PORT ?= 8000
UI_PORT ?= 3000
LDAP_PORT ?= 389
POSTGRES_PORT ?= 5432
REDIS_PORT ?= 6379
PHPLDAPADMIN_PORT ?= 8080

# Colors for output
COLOR_RESET := \033[0m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m
COLOR_CYAN := \033[36m

# Helper function for colored output
define log_info
	@echo "$(COLOR_CYAN)ℹ $(1)$(COLOR_RESET)"
endef

define log_success
	@echo "$(COLOR_GREEN)✓ $(1)$(COLOR_RESET)"
endef

define log_warning
	@echo "$(COLOR_YELLOW)⚠ $(1)$(COLOR_RESET)"
endef
