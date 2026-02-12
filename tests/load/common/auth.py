"""
JWT authentication mixin with automatic token refresh.

Follows Locust best practices:
- Uses on_start for login (called once per user instance)
- Uses catch_response for granular error reporting
- Proactive token refresh before expiry
- Reactive 401 retry (single attempt)

See: https://docs.locust.io/en/stable/writing-a-locustfile.html
"""

import time
import urllib3
from typing import Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Refresh 5 minutes before expiry to avoid edge-case 401s
_REFRESH_MARGIN_SECONDS = 300


class AuthMixin:
    """
    Mixin for Locust HttpUser classes providing JWT auth with auto-refresh.

    Usage:
        class MyUser(AuthMixin, HttpUser):
            def on_start(self):
                self.setup_auth()

            @task
            def my_task(self):
                self.auth_get("/api/v1/users")
    """

    _token: str = ""
    _token_expiry: float = 0.0
    _username: str = "hrc-admin"
    _password: str = "hrc-admin-secret"

    def setup_auth(
        self,
        username: str = "hrc-admin",
        password: str = "hrc-admin-secret",
    ) -> bool:
        """Initialize authentication. Call this from on_start()."""
        self._username = username
        self._password = password
        # Disable SSL verification for self-signed dev certs
        self.client.verify = False
        return self._do_login()

    # Keep backward compat
    login = setup_auth

    def _do_login(self) -> bool:
        """Perform the actual login request."""
        with self.client.post(
            "/api/v1/auth/login",
            json={"username": self._username, "password": self._password},
            name="/api/v1/auth/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self._token = data.get("access_token", data.get("accessToken", ""))
                expires_in = data.get("expires_in", data.get("expiresIn", 3600))
                self._token_expiry = time.monotonic() + expires_in
                self.client.headers.update({"Authorization": f"Bearer {self._token}"})
                resp.success()
                return True
            else:
                resp.failure(f"Login failed: {resp.status_code}")
                return False

    def _ensure_token(self) -> None:
        """Refresh the token if it's near expiry."""
        if time.monotonic() >= self._token_expiry - _REFRESH_MARGIN_SECONDS:
            self._do_login()

    def _auth_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Generic authenticated request with token refresh and 401 retry."""
        self._ensure_token()
        fn = getattr(self.client, method)
        resp = fn(url, **kwargs)
        if resp.status_code == 401:
            if self._do_login():
                resp = fn(url, **kwargs)
        return resp

    def auth_get(self, url: str, **kwargs: Any) -> Any:
        """GET with automatic token refresh and 401 retry."""
        return self._auth_request("get", url, **kwargs)

    def auth_post(self, url: str, **kwargs: Any) -> Any:
        """POST with automatic token refresh and 401 retry."""
        return self._auth_request("post", url, **kwargs)

    def auth_put(self, url: str, **kwargs: Any) -> Any:
        """PUT with automatic token refresh and 401 retry."""
        return self._auth_request("put", url, **kwargs)

    def auth_patch(self, url: str, **kwargs: Any) -> Any:
        """PATCH with automatic token refresh and 401 retry."""
        return self._auth_request("patch", url, **kwargs)

    def auth_delete(self, url: str, **kwargs: Any) -> Any:
        """DELETE with automatic token refresh and 401 retry."""
        return self._auth_request("delete", url, **kwargs)
