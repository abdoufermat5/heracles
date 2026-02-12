"""
API Consumer — automation scripts, CI/CD pipelines, integrations.

Simulates machine-to-machine API usage with fast request rates and
full lifecycle operations (create → configure → verify → cleanup).
"""

from locust import HttpUser, between, tag, task

from common.auth import AuthMixin
from common.helpers import pick, random_ip, random_string


class HeraclesAPIConsumer(AuthMixin, HttpUser):
    """Fast API consumer simulating automation / CI pipelines.

    Logs in as devuser (User Manager ACL policy — full user/group CRUD).
    """

    host = "https://api.heracles.local"
    wait_time = between(0.3, 1)
    weight = 1

    def on_start(self):
        self.setup_auth("devuser", "Devpassword123")

    # ── User lifecycle ─────────────────────────────────────────────────────

    @tag("users", "write")
    @task(3)
    def user_lifecycle(self):
        """Create user → activate POSIX → activate SSH → activate mail → cleanup."""
        uid = f"auto-{random_string(5)}"

        resp = self.auth_post(
            "/api/v1/users",
            json={
                "uid": uid,
                "cn": f"Auto {uid}",
                "sn": "Auto",
                "givenName": "Bot",
                "mail": f"{uid}@heracles.local",
                "password": "AutoPass123!",
            },
            name="/api/v1/users [lifecycle:create]",
        )
        if resp.status_code not in (200, 201):
            return

        # Activate POSIX
        self.auth_post(
            f"/api/v1/users/{uid}/posix",
            json={"loginShell": "/bin/bash", "homeDirectory": f"/home/{uid}"},
            name="/api/v1/users/{uid}/posix [lifecycle:activate]",
        )

        # Verify POSIX
        self.auth_get(
            f"/api/v1/users/{uid}/posix",
            name="/api/v1/users/{uid}/posix [lifecycle:verify]",
        )

        # Activate SSH
        self.auth_post(
            f"/api/v1/ssh/users/{uid}/activate",
            name="/api/v1/ssh/users/{uid}/activate [lifecycle]",
        )

        # Activate mail
        self.auth_post(
            f"/api/v1/mail/users/{uid}/activate",
            json={"mail": f"{uid}@heracles.local"},
            name="/api/v1/mail/users/{uid}/activate [lifecycle]",
        )

        # Cleanup
        self.auth_delete(
            f"/api/v1/users/{uid}",
            name="/api/v1/users/{uid} [lifecycle:delete]",
        )

    # ── DNS lifecycle ──────────────────────────────────────────────────────

    @tag("dns", "write")
    @task(2)
    def dns_record_lifecycle(self):
        """Create → list → delete a DNS A record."""
        name = f"lt-{random_string(4)}"
        ip = random_ip()
        zone = "heracles.local"

        resp = self.auth_post(
            f"/api/v1/dns/zones/{zone}/records",
            json={"name": name, "recordType": "A", "values": [ip]},
            name="/api/v1/dns/zones/{zone}/records [lifecycle:create]",
        )
        if resp.status_code in (200, 201):
            self.auth_get(
                f"/api/v1/dns/zones/{zone}/records",
                name="/api/v1/dns/zones/{zone}/records [lifecycle:list]",
            )
            self.auth_delete(
                f"/api/v1/dns/zones/{zone}/records/{name}/A?value={ip}",
                name="/api/v1/dns/zones/{zone}/records/{name}/{type} [lifecycle:delete]",
            )

    # ── Bulk reads ─────────────────────────────────────────────────────────

    @tag("systems")
    @task(2)
    def systems_browse_all_types(self):
        """Hit every system type endpoint."""
        for stype in ("servers", "workstations", "terminals", "printers", "phones"):
            self.auth_get(f"/api/v1/systems/{stype}", name=f"/api/v1/systems/{stype}")

    @tag("sudo")
    @task(1)
    def sudo_full_view(self):
        """Sudo roles + per-user lookups."""
        self.auth_get("/api/v1/sudo/roles", name="/api/v1/sudo/roles [api]")
        for uid in ("testuser", "opsuser"):
            self.auth_get(
                f"/api/v1/sudo/users/{uid}/roles",
                name="/api/v1/sudo/users/{uid}/roles [api]",
            )

    @tag("dhcp")
    @task(2)
    def dhcp_full_view(self):
        """DHCP service tree + subnets + hosts."""
        svc = "demo-dhcp-service"
        self.auth_get(f"/api/v1/dhcp/{svc}/tree", name="/api/v1/dhcp/{svc}/tree [api]")
        self.auth_get(f"/api/v1/dhcp/{svc}/subnets", name="/api/v1/dhcp/{svc}/subnets [api]")
        self.auth_get(f"/api/v1/dhcp/{svc}/hosts", name="/api/v1/dhcp/{svc}/hosts [api]")

    @tag("posix")
    @task(2)
    def posix_overview(self):
        """POSIX groups + mixed groups + next IDs."""
        self.auth_get("/api/v1/posix/groups", name="/api/v1/posix/groups [api]")
        self.auth_get("/api/v1/posix/mixed-groups", name="/api/v1/posix/mixed-groups [api]")
        self.auth_get("/api/v1/posix/next-ids", name="/api/v1/posix/next-ids [api]")

    # ── Health / monitoring ────────────────────────────────────────────────

    @tag("health")
    @task(5)
    def rapid_health(self):
        self.auth_get("/api/v1/health", name="/api/v1/health [api]")

    @tag("health")
    @task(2)
    def rapid_stats(self):
        self.auth_get("/api/v1/stats", name="/api/v1/stats [api]")
