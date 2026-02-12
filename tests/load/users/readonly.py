"""
Read-Only User — browsing and viewing only.

Simulates typical staff members browsing the Heracles UI.
This is the most common persona in real enterprise deployments (weight 5).
"""

import random

from locust import HttpUser, between, tag, task

from common.auth import AuthMixin
from common.helpers import pick, random_string


class HeraclesReadOnlyUser(AuthMixin, HttpUser):
    """Read-only user simulating typical UI browsing patterns.

    Logs in as testuser (Viewer ACL policy — read-only access).
    """

    host = "https://api.heracles.local"
    wait_time = between(1, 4)
    weight = 5  # Most users are readers

    def on_start(self):
        self.setup_auth("testuser", "Testpassword123")

    # ── Core browsing ──────────────────────────────────────────────────────

    @tag("users")
    @task(10)
    def browse_users(self):
        page = random.randint(1, 5)
        self.auth_get(
            f"/api/v1/users?page={page}&page_size=50",
            name="/api/v1/users [browse]",
        )

    @tag("users")
    @task(4)
    def view_user_detail(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/users/{uid}", name="/api/v1/users/{uid} [view]")

    @tag("users")
    @task(3)
    def search_users(self):
        self.auth_get(
            f"/api/v1/users?search={random_string(3)}",
            name="/api/v1/users [search]",
        )

    @tag("groups")
    @task(5)
    def browse_groups(self):
        self.auth_get("/api/v1/groups", name="/api/v1/groups [browse]")

    @tag("groups")
    @task(2)
    def view_group(self):
        cn = pick("developers", "operations")
        self.auth_get(f"/api/v1/groups/{cn}", name="/api/v1/groups/{cn} [view]")

    @tag("audit")
    @task(3)
    def view_audit(self):
        self.auth_get("/api/v1/audit/logs?pageSize=50", name="/api/v1/audit/logs [browse]")

    @tag("health")
    @task(3)
    def dashboard(self):
        self.auth_get("/api/v1/stats")

    @tag("departments")
    @task(3)
    def browse_departments(self):
        self.auth_get("/api/v1/departments/tree")

    @tag("roles")
    @task(2)
    def browse_roles(self):
        self.auth_get("/api/v1/roles", name="/api/v1/roles [browse]")

    # ── Plugin browsing ────────────────────────────────────────────────────

    @tag("posix")
    @task(3)
    def browse_posix_groups(self):
        self.auth_get("/api/v1/posix/groups", name="/api/v1/posix/groups [browse]")

    @tag("posix")
    @task(2)
    def view_posix_user(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/users/{uid}/posix", name="/api/v1/users/{uid}/posix [view]")

    @tag("systems")
    @task(3)
    def browse_systems(self):
        self.auth_get("/api/v1/systems", name="/api/v1/systems [browse]")

    @tag("systems")
    @task(2)
    def browse_servers(self):
        self.auth_get("/api/v1/systems/servers", name="/api/v1/systems/servers [browse]")

    @tag("dns")
    @task(3)
    def browse_dns(self):
        self.auth_get("/api/v1/dns/zones", name="/api/v1/dns/zones [browse]")

    @tag("dns")
    @task(2)
    def browse_dns_records(self):
        self.auth_get(
            "/api/v1/dns/zones/heracles.local/records",
            name="/api/v1/dns/zones/{zone}/records [browse]",
        )

    @tag("dhcp")
    @task(2)
    def browse_dhcp(self):
        self.auth_get("/api/v1/dhcp", name="/api/v1/dhcp [browse]")

    @tag("dhcp")
    @task(2)
    def browse_dhcp_tree(self):
        self.auth_get(
            "/api/v1/dhcp/demo-dhcp-service/tree",
            name="/api/v1/dhcp/{service}/tree [browse]",
        )

    @tag("sudo")
    @task(2)
    def browse_sudo(self):
        self.auth_get("/api/v1/sudo/roles", name="/api/v1/sudo/roles [browse]")

    @tag("ssh")
    @task(2)
    def browse_ssh_keys(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/ssh/users/{uid}/keys", name="/api/v1/ssh/users/{uid}/keys [browse]")

    @tag("mail")
    @task(2)
    def browse_mail(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/mail/users/{uid}", name="/api/v1/mail/users/{uid} [browse]")

    # ── Meta / Config ──────────────────────────────────────────────────────

    @tag("config")
    @task(1)
    def view_config(self):
        self.auth_get("/api/v1/config")

    @tag("plugins")
    @task(1)
    def view_plugins(self):
        self.auth_get("/api/v1/plugins")

    @tag("auth")
    @task(1)
    def view_me(self):
        self.auth_get("/api/v1/auth/me", name="/api/v1/auth/me [browse]")
