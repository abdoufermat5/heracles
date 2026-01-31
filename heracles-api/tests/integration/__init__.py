"""
Integration Tests
=================

Integration tests with real services.

These tests require running external services:
- LDAP (OpenLDAP)
- Redis
- PostgreSQL

Run with: pytest tests/integration/ -v

Note: Make sure services are running before executing these tests.
Use `make up-infra` to start required infrastructure.
"""
