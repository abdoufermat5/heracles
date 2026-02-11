# ============================================================================
#                              HERACLES
# ============================================================================
# Identity Management System - run "make help" for commands
# ============================================================================

# Load .env if exists
-include .env
export

# Directories
API_DIR := heracles-api
UI_DIR := heracles-ui
CORE_DIR := heracles-core
PLUGINS_DIR := heracles_plugins
DEMO_DIR := demo

# Docker
COMPOSE := docker compose

# Ports (override in .env)
API_PORT ?= 8000
UI_PORT ?= 3000
LDAP_PORT ?= 389
POSTGRES_PORT ?= 5432
REDIS_PORT ?= 6379

# LDAP (override in .env)
LDAP_BASE_DN ?= dc=heracles,dc=local
LDAP_ADMIN_DN ?= cn=admin,$(LDAP_BASE_DN)
LDAP_ADMIN_PW ?= admin_secret

# Include modules
include mk/docker.mk
include mk/setup.mk
include mk/demo.mk
include mk/versioning.mk
include mk/help.mk
