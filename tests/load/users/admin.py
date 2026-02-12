"""
Admin User — full CRUD across core API + all 7 plugins.

Simulates an IT administrator performing day-to-day identity management.
"""

import random

from locust import HttpUser, between, tag, task

from common.auth import AuthMixin
from common.helpers import pick, random_string


class HeraclesAdminUser(AuthMixin, HttpUser):
    """IT admin exercising all API features including writes.

    Logs in as hrc-admin (Superadmin ACL policy — full CRUD).
    """

    host = "https://api.heracles.local"
    wait_time = between(1, 3)
    weight = 2

    def on_start(self):
        self.setup_auth("hrc-admin", "hrc-admin-secret")

    # ── Auth ───────────────────────────────────────────────────────────────

    @tag("auth")
    @task(2)
    def get_me(self):
        self.auth_get("/api/v1/auth/me", name="/api/v1/auth/me")

    # ── Health / Dashboard ─────────────────────────────────────────────────

    @tag("health")
    @task(3)
    def health_check(self):
        self.auth_get("/api/v1/health")

    @tag("health")
    @task(5)
    def dashboard_stats(self):
        self.auth_get("/api/v1/stats")

    @tag("health")
    @task(1)
    def version(self):
        self.auth_get("/api/v1/version")

    # ── Users ──────────────────────────────────────────────────────────────

    @tag("users")
    @task(10)
    def list_users(self):
        page = random.randint(1, 3)
        self.auth_get(
            f"/api/v1/users?page={page}&page_size=20",
            name="/api/v1/users [list]",
        )

    @tag("users")
    @task(5)
    def search_users(self):
        self.auth_get(
            f"/api/v1/users?search={random_string(3)}",
            name="/api/v1/users [search]",
        )

    @tag("users")
    @task(3)
    def get_user(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/users/{uid}", name="/api/v1/users/{uid}")

    @tag("users", "write")
    @task(1)
    def create_and_delete_user(self):
        uid = f"lt-{random_string(6)}"
        resp = self.auth_post(
            "/api/v1/users",
            json={
                "uid": uid,
                "cn": f"Load Test {uid}",
                "sn": "LoadTest",
                "givenName": "LT",
                "mail": f"{uid}@heracles.local",
                "password": "TestPassword123!",
            },
            name="/api/v1/users [create]",
        )
        if resp.status_code in (200, 201):
            self.auth_delete(f"/api/v1/users/{uid}", name="/api/v1/users/{uid} [delete]")

    @tag("users")
    @task(2)
    def get_user_lock_status(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/users/{uid}/locked", name="/api/v1/users/{uid}/locked")

    # ── Groups ─────────────────────────────────────────────────────────────

    @tag("groups")
    @task(8)
    def list_groups(self):
        self.auth_get("/api/v1/groups?page=1&page_size=20", name="/api/v1/groups [list]")

    @tag("groups")
    @task(3)
    def search_groups(self):
        self.auth_get(
            f"/api/v1/groups?search={random_string(3)}",
            name="/api/v1/groups [search]",
        )

    @tag("groups")
    @task(2)
    def get_group(self):
        cn = pick("developers", "operations")
        self.auth_get(f"/api/v1/groups/{cn}", name="/api/v1/groups/{cn}")

    # ── Roles ──────────────────────────────────────────────────────────────

    @tag("roles")
    @task(3)
    def list_roles(self):
        self.auth_get("/api/v1/roles?page=1&page_size=20", name="/api/v1/roles [list]")

    # ── Departments ────────────────────────────────────────────────────────

    @tag("departments")
    @task(3)
    def list_departments(self):
        self.auth_get("/api/v1/departments")

    @tag("departments")
    @task(2)
    def department_tree(self):
        self.auth_get("/api/v1/departments/tree")

    # ── ACL ────────────────────────────────────────────────────────────────

    @tag("acl")
    @task(3)
    def list_acl_policies(self):
        self.auth_get("/api/v1/acl/policies", name="/api/v1/acl/policies")

    @tag("acl")
    @task(2)
    def list_acl_permissions(self):
        self.auth_get("/api/v1/acl/permissions")

    @tag("acl")
    @task(2)
    def my_permissions(self):
        self.auth_get("/api/v1/acl/me/permissions")

    @tag("acl")
    @task(1)
    def list_acl_assignments(self):
        self.auth_get("/api/v1/acl/assignments")

    # ── Audit ──────────────────────────────────────────────────────────────

    @tag("audit")
    @task(4)
    def list_audit_logs(self):
        self.auth_get("/api/v1/audit/logs?pageSize=20", name="/api/v1/audit/logs")

    @tag("audit")
    @task(2)
    def search_audit_logs(self):
        action = pick("user_created", "group_created", "login_success")
        self.auth_get(
            f"/api/v1/audit/logs?pageSize=10&action={action}",
            name="/api/v1/audit/logs [filtered]",
        )

    # ── Templates ──────────────────────────────────────────────────────────

    @tag("templates")
    @task(3)
    def list_templates(self):
        self.auth_get("/api/v1/templates")

    @tag("templates")
    @task(1)
    def template_plugin_fields(self):
        self.auth_get("/api/v1/templates/plugin-fields?object_type=user")

    # ── Import/Export ──────────────────────────────────────────────────────

    @tag("import-export")
    @task(1)
    def export_fields(self):
        obj_type = pick("user", "group")
        self.auth_get(
            f"/api/v1/import-export/fields/{obj_type}",
            name="/api/v1/import-export/fields/{type}",
        )

    # ── Plugins ────────────────────────────────────────────────────────────

    @tag("plugins")
    @task(2)
    def list_plugins(self):
        self.auth_get("/api/v1/plugins")

    @tag("plugins")
    @task(2)
    def get_tabs(self):
        obj_type = pick("user", "group")
        self.auth_get(f"/api/v1/tabs/{obj_type}", name="/api/v1/tabs/{type}")

    # ── Config ─────────────────────────────────────────────────────────────

    @tag("config")
    @task(2)
    def get_config(self):
        self.auth_get("/api/v1/config")

    @tag("config")
    @task(1)
    def get_config_categories(self):
        self.auth_get("/api/v1/config/categories")

    @tag("config")
    @task(1)
    def get_plugin_configs(self):
        self.auth_get("/api/v1/config/plugins")

    # ── POSIX Plugin ───────────────────────────────────────────────────────

    @tag("posix")
    @task(3)
    def posix_user_status(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/users/{uid}/posix", name="/api/v1/users/{uid}/posix")

    @tag("posix")
    @task(2)
    def posix_user_groups(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(
            f"/api/v1/users/{uid}/posix/groups",
            name="/api/v1/users/{uid}/posix/groups",
        )

    @tag("posix")
    @task(3)
    def list_posix_groups(self):
        self.auth_get("/api/v1/posix/groups", name="/api/v1/posix/groups")

    @tag("posix")
    @task(2)
    def list_mixed_groups(self):
        self.auth_get("/api/v1/posix/mixed-groups", name="/api/v1/posix/mixed-groups")

    @tag("posix")
    @task(1)
    def posix_next_ids(self):
        self.auth_get("/api/v1/posix/next-ids")

    @tag("posix")
    @task(1)
    def posix_shells(self):
        self.auth_get("/api/v1/posix/shells")

    # ── SSH Plugin ─────────────────────────────────────────────────────────

    @tag("ssh")
    @task(2)
    def ssh_user_status(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/ssh/users/{uid}", name="/api/v1/ssh/users/{uid}")

    @tag("ssh")
    @task(2)
    def ssh_user_keys(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/ssh/users/{uid}/keys", name="/api/v1/ssh/users/{uid}/keys")

    # ── Sudo Plugin ────────────────────────────────────────────────────────

    @tag("sudo")
    @task(3)
    def list_sudo_roles(self):
        self.auth_get("/api/v1/sudo/roles", name="/api/v1/sudo/roles")

    @tag("sudo")
    @task(2)
    def sudo_roles_for_user(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/sudo/users/{uid}/roles", name="/api/v1/sudo/users/{uid}/roles")

    @tag("sudo")
    @task(1)
    def sudo_roles_for_host(self):
        host = pick("server1", "workstation1", "ALL")
        self.auth_get(f"/api/v1/sudo/hosts/{host}/roles", name="/api/v1/sudo/hosts/{host}/roles")

    # ── Systems Plugin ─────────────────────────────────────────────────────

    @tag("systems")
    @task(3)
    def list_systems(self):
        self.auth_get("/api/v1/systems?page=1&page_size=20", name="/api/v1/systems [list]")

    @tag("systems")
    @task(2)
    def list_servers(self):
        self.auth_get("/api/v1/systems/servers", name="/api/v1/systems/servers")

    @tag("systems")
    @task(2)
    def list_workstations(self):
        self.auth_get("/api/v1/systems/workstations", name="/api/v1/systems/workstations")

    @tag("systems")
    @task(1)
    def system_hostnames(self):
        self.auth_get("/api/v1/systems/hostnames")

    # ── DNS Plugin ─────────────────────────────────────────────────────────

    @tag("dns")
    @task(3)
    def list_dns_zones(self):
        self.auth_get("/api/v1/dns/zones", name="/api/v1/dns/zones")

    @tag("dns")
    @task(2)
    def get_dns_zone(self):
        self.auth_get("/api/v1/dns/zones/heracles.local", name="/api/v1/dns/zones/{zone}")

    @tag("dns")
    @task(3)
    def list_dns_records(self):
        self.auth_get(
            "/api/v1/dns/zones/heracles.local/records",
            name="/api/v1/dns/zones/{zone}/records",
        )

    # ── DHCP Plugin ────────────────────────────────────────────────────────

    @tag("dhcp")
    @task(2)
    def list_dhcp_services(self):
        self.auth_get("/api/v1/dhcp", name="/api/v1/dhcp [list]")

    @tag("dhcp")
    @task(2)
    def dhcp_service_detail(self):
        self.auth_get("/api/v1/dhcp/demo-dhcp-service", name="/api/v1/dhcp/{service}")

    @tag("dhcp")
    @task(2)
    def dhcp_service_tree(self):
        self.auth_get("/api/v1/dhcp/demo-dhcp-service/tree", name="/api/v1/dhcp/{service}/tree")

    @tag("dhcp")
    @task(2)
    def list_dhcp_subnets(self):
        self.auth_get(
            "/api/v1/dhcp/demo-dhcp-service/subnets",
            name="/api/v1/dhcp/{service}/subnets",
        )

    @tag("dhcp")
    @task(2)
    def list_dhcp_hosts(self):
        self.auth_get(
            "/api/v1/dhcp/demo-dhcp-service/hosts",
            name="/api/v1/dhcp/{service}/hosts",
        )

    @tag("dhcp")
    @task(1)
    def list_dhcp_shared_networks(self):
        self.auth_get(
            "/api/v1/dhcp/demo-dhcp-service/shared-networks",
            name="/api/v1/dhcp/{service}/shared-networks",
        )

    @tag("dhcp")
    @task(1)
    def list_dhcp_groups(self):
        self.auth_get(
            "/api/v1/dhcp/demo-dhcp-service/groups",
            name="/api/v1/dhcp/{service}/groups",
        )

    # ── Mail Plugin ────────────────────────────────────────────────────────

    @tag("mail")
    @task(2)
    def mail_user_status(self):
        uid = pick("testuser", "devuser", "opsuser")
        self.auth_get(f"/api/v1/mail/users/{uid}", name="/api/v1/mail/users/{uid}")

    @tag("mail")
    @task(2)
    def mail_group_status(self):
        cn = pick("developers", "operations")
        self.auth_get(f"/api/v1/mail/groups/{cn}", name="/api/v1/mail/groups/{cn}")
