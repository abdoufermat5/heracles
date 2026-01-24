"""
E2E Tests Package
=================

End-to-end tests for Heracles plugins.

To run E2E tests:
    RUN_E2E_TESTS=1 pytest tests/e2e/ -v

Prerequisites:
    - Docker infrastructure running (make dev-infra)
    - LDAP bootstrapped (make bootstrap)
    - API running (make api)
    - Test user exists with password set
"""
