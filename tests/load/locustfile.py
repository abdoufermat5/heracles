"""
Heracles — Load Testing with Locust
=====================================

Usage:
  uv pip install locust
  locust -f tests/load/locustfile.py --host http://localhost:8000

Web UI will be at http://localhost:8089
"""

import json
import random
import string

from locust import HttpUser, between, task


def random_string(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


class HeraclesUser(HttpUser):
    """Simulates a typical Heracles admin user."""

    wait_time = between(1, 3)
    token: str = ""

    def on_start(self):
        """Login and obtain JWT token."""
        resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "username": "hrc-admin",
                "password": "admin_secret",
            },
        )
        if resp.status_code == 200:
            # Token is set via HttpOnly cookie, requests session handles it
            pass
        else:
            self.environment.runner.quit()

    # ── User Operations ────────────────────────────────────────────────────

    @task(10)
    def list_users(self):
        self.client.get("/api/v1/users?page=1&page_size=20")

    @task(5)
    def search_users(self):
        self.client.get(f"/api/v1/users?search={random_string(3)}")

    @task(2)
    def create_user(self):
        uid = f"loadtest-{random_string(6)}"
        self.client.post(
            "/api/v1/users",
            json={
                "uid": uid,
                "cn": f"Load Test {uid}",
                "sn": "Test",
                "givenName": "Load",
                "mail": f"{uid}@example.com",
                "userPassword": "TestPassword123!",
            },
            name="/api/v1/users [create]",
        )

    # ── Group Operations ───────────────────────────────────────────────────

    @task(8)
    def list_groups(self):
        self.client.get("/api/v1/groups?page=1&page_size=20")

    @task(3)
    def list_departments(self):
        self.client.get("/api/v1/departments")

    # ── Audit ──────────────────────────────────────────────────────────────

    @task(4)
    def list_audit_logs(self):
        self.client.get("/api/v1/audit/logs?pageSize=20")

    # ── Templates ──────────────────────────────────────────────────────────

    @task(3)
    def list_templates(self):
        self.client.get("/api/v1/templates")

    # ── Health & Dashboard ──────────────────────────────────────────────────

    @task(6)
    def dashboard_stats(self):
        self.client.get("/api/v1/stats")

    @task(2)
    def health_check(self):
        self.client.get("/api/v1/health")

    # ── ACL ────────────────────────────────────────────────────────────────

    @task(3)
    def list_acl_policies(self):
        self.client.get("/api/v1/acl/policies")

    @task(2)
    def list_plugins(self):
        self.client.get("/api/v1/plugins")


class HeraclesReadOnlyUser(HttpUser):
    """Simulates a read-only user browsing the system."""

    wait_time = between(2, 5)
    weight = 3  # 3x more read-only users than admin users

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={
                "username": "hrc-admin",
                "password": "admin_secret",
            },
        )

    @task(10)
    def browse_users(self):
        self.client.get("/api/v1/users?page=1&page_size=50")

    @task(5)
    def browse_groups(self):
        self.client.get("/api/v1/groups")

    @task(3)
    def view_audit(self):
        self.client.get("/api/v1/audit/logs?pageSize=50")

    @task(2)
    def dashboard(self):
        self.client.get("/api/v1/stats")
