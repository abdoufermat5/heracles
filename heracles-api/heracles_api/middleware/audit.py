"""
Audit Middleware
================

Automatically logs **all** mutating API operations (POST, PUT, PATCH, DELETE)
to the audit_logs table.  Uses a catch-all approach: every request on an
unsafe method is audited unless it appears in a short explicit skip-list.

Entity type and ID are *inferred* from the URL path via a best-effort
two-pass strategy:

1. A small table of **exact overrides** for paths that need a custom action
   (login, logout, password change, export …).
2. A generic parser that extracts entity_type and entity_id from the path
   segments (``/api/v1/<entity_type>[/<entity_id>][/<sub>…]``).

This means new endpoints are automatically captured without needing to add
a regex for each one.
"""

import json
import re

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = structlog.get_logger(__name__)

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# ---------------------------------------------------------------------------
# Paths / prefixes to SKIP entirely (noise, health, docs)
# ---------------------------------------------------------------------------

_SKIP_PATHS: set[str] = {
    "/api/v1/auth/refresh",
    "/api/health",
    "/api/v1/health",
}

_SKIP_PREFIXES: tuple[str, ...] = (
    "/api/docs",
    "/api/redoc",
    "/api/openapi",
)

# ---------------------------------------------------------------------------
# HTTP method → default action
# ---------------------------------------------------------------------------

_METHOD_ACTION: dict[str, str] = {
    "POST": "create",
    "PUT": "update",
    "PATCH": "update",
    "DELETE": "delete",
}

# ---------------------------------------------------------------------------
# Explicit action overrides  (path regex → entity_type, action)
# Checked first; only needed for paths whose *action* differs from the
# HTTP-method default (login, logout, password_change, export, import …).
# ---------------------------------------------------------------------------

_ACTION_OVERRIDES: list[tuple[re.Pattern, str, str]] = [
    # Auth
    (re.compile(r"^/api/v1/auth/login$"), "session", "login"),
    (re.compile(r"^/api/v1/auth/logout(-all)?$"), "session", "logout"),
    (re.compile(r"^/api/v1/auth/password/change$"), "user", "password_change"),
    (re.compile(r"^/api/v1/auth/password/reset/request$"), "user", "password_reset_request"),
    # User password / lock / unlock
    (re.compile(r"^/api/v1/users/([^/]+)/password$"), "user", "password_change"),
    (re.compile(r"^/api/v1/users/([^/]+)/lock$"), "user", "lock"),
    (re.compile(r"^/api/v1/users/([^/]+)/unlock$"), "user", "unlock"),
    # Import / export
    (re.compile(r"^/api/v1/import-export/export$"), "entry", "export"),
    (re.compile(r"^/api/v1/import-export/import(?:/(?:preview|csv|ldif))?$"), "entry", "import"),
    # SSH
    (re.compile(r"^/api/v1/ssh/users/([^/]+)/activate$"), "ssh", "activate"),
    (re.compile(r"^/api/v1/ssh/users/([^/]+)/deactivate$"), "ssh", "deactivate"),
    # Mail
    (re.compile(r"^/api/v1/mail/(?:users|groups)/([^/]+)/activate$"), "mail", "activate"),
    (re.compile(r"^/api/v1/mail/(?:users|groups)/([^/]+)/deactivate$"), "mail", "deactivate"),
    # POSIX user
    (re.compile(r"^/api/v1/users/([^/]+)/posix(?:/.*)?$"), "posix", None),
    # Config
    (re.compile(r"^/api/v1/config/plugins/([^/]+)/enable$"), "plugin", "enable"),
    (re.compile(r"^/api/v1/config/plugins/([^/]+)/disable$"), "plugin", "disable"),
    (re.compile(r"^/api/v1/config/rdn/check$"), "config", "rdn_check"),
    (re.compile(r"^/api/v1/config/rdn/migrate$"), "config", "rdn_migrate"),
    # Template preview
    (re.compile(r"^/api/v1/templates/([^/]+)/preview$"), "template", "preview"),
    # Systems validate
    (re.compile(r"^/api/v1/systems/validate-hosts$"), "system", "validate"),
    # Sudo defaults
    (re.compile(r"^/api/v1/sudo/defaults$"), "sudo_defaults", None),
]


# ---------------------------------------------------------------------------
# Generic path parser
# ---------------------------------------------------------------------------

# Segments that are "sub-resources" rather than entity types or ids
_SUB_ACTIONS = {
    "members",
    "member-uids",
    "keys",
    "records",
    "subnets",
    "pools",
    "hosts",
    "shared-networks",
    "groups",
    "classes",
    "tsig-keys",
    "dns-zones",
    "failover-peers",
    "attr-rules",
}

# Segments that look like an entity type (alpha + hyphens/underscores)
_ENTITY_SEGMENT_RE = re.compile(r"^[a-z][a-z0-9_-]+$")


def _parse_path(path: str) -> tuple[str, str | None, str | None]:
    """
    Best-effort extraction of (entity_type, entity_id, action_override)
    from an arbitrary ``/api/v1/…`` path.

    Strategy:
    1. Try the explicit _ACTION_OVERRIDES table (returns on first match).
    2. Fall back to generic segment parsing.
    """
    # --- Pass 1: explicit overrides ---
    for pattern, etype, action in _ACTION_OVERRIDES:
        m = pattern.match(path)
        if m:
            eid = m.group(1) if m.lastindex and m.lastindex >= 1 else None
            return etype, eid, action

    # --- Pass 2: generic parser ---
    # Strip /api/v1/ prefix and split
    stripped = path.removeprefix("/api/v1/").rstrip("/")
    if not stripped:
        return "unknown", None, None

    parts = stripped.split("/")

    entity_type: str = parts[0]  # e.g. "users", "groups", "dhcp", "dns"
    entity_id: str | None = None

    # Normalise common plurals → singular
    entity_type = _singularise(entity_type)

    # Walk remaining segments to extract entity_id and refine entity_type
    i = 1
    while i < len(parts):
        seg = parts[i]

        if seg in _SUB_ACTIONS:
            # e.g. …/members, …/subnets  →  record as sub_type
            sub = _singularise(seg)
            entity_type = f"{entity_type}_{sub}"
            i += 1
            # Next segment after a sub-action is likely the sub-entity id
            if i < len(parts):
                entity_id = parts[i]
                i += 1
        elif _ENTITY_SEGMENT_RE.match(seg) and (i + 1 < len(parts) or seg in _SUB_ACTIONS):
            # Looks like a nested type (e.g. …/zones/{name}/records)
            entity_type = _singularise(seg)
            i += 1
        else:
            # Assume it's an entity_id
            if entity_id is None:
                entity_id = seg
            i += 1

    return entity_type, entity_id, None


_SINGULAR_MAP: dict[str, str] = {
    "users": "user",
    "groups": "group",
    "roles": "role",
    "departments": "department",
    "policies": "acl_policy",
    "assignments": "acl_assignment",
    "templates": "template",
    "zones": "dns_zone",
    "records": "dns_record",
    "systems": "system",
    "members": "member",
    "member-uids": "member",
    "keys": "ssh_key",
    "subnets": "dhcp_subnet",
    "pools": "dhcp_pool",
    "hosts": "dhcp_host",
    "shared-networks": "dhcp_shared_network",
    "classes": "dhcp_class",
    "tsig-keys": "dhcp_tsig_key",
    "dns-zones": "dhcp_dns_zone",
    "failover-peers": "dhcp_failover_peer",
    "attr-rules": "acl_attr_rule",
    "mixed-groups": "posix_mixed_group",
}


def _singularise(segment: str) -> str:
    """Map a URL segment to a singular entity type name."""
    if segment in _SINGULAR_MAP:
        return _SINGULAR_MAP[segment]
    # Generic: strip trailing 's' if present (users→user, etc.)
    if segment.endswith("s") and len(segment) > 3:
        return segment[:-1]
    return segment


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_client_ip(request: Request) -> str | None:
    """Best-effort client IP extraction."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _decode_jwt_claims(token: str) -> dict | None:
    """Decode JWT payload without verification (used only to read sub/uid)."""
    try:
        import base64

        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Catch-all audit middleware.

    Every POST/PUT/PATCH/DELETE that is not in the explicit skip-list is
    logged.  Entity type and ID are inferred from the URL.  The current
    user is read from the JWT ``access_token`` cookie.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only audit unsafe methods
        if request.method not in UNSAFE_METHODS:
            return await call_next(request)

        path = request.url.path

        # Skip noise
        if path in _SKIP_PATHS or path.startswith(_SKIP_PREFIXES):
            return await call_next(request)

        # Execute the actual handler
        response: Response = await call_next(request)

        # Fire-and-forget audit logging (both successes and failures)
        try:
            await self._log(request, response, path)
        except Exception as exc:
            logger.warning("audit_middleware_error", path=path, error=str(exc))

        return response

    async def _log(
        self,
        request: Request,
        response: Response,
        path: str,
    ) -> None:
        """Extract context and delegate to AuditService."""
        from heracles_api.services.audit_service import get_audit_service

        try:
            audit = get_audit_service()
        except RuntimeError:
            return

        # Parse entity info from URL
        entity_type, entity_id, action_override = _parse_path(path)
        action = action_override or _METHOD_ACTION.get(request.method, request.method.lower())

        # Current user from JWT cookie
        actor_dn: str | None = None
        actor_name: str | None = None
        token = request.cookies.get("access_token")
        if token:
            claims = _decode_jwt_claims(token)
            if claims:
                actor_dn = claims.get("sub")
                actor_name = claims.get("uid")

        # For login, actor info comes from the response body if available
        if action == "login" and not actor_dn:
            actor_dn = "anonymous"
            actor_name = None

        if not actor_dn:
            return

        ip_address = _get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        audit_status = "success" if response.status_code < 400 else "failure"

        await audit.log_action(
            actor_dn=actor_dn,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=audit_status,
            error_message=(f"HTTP {response.status_code}" if audit_status == "failure" else None),
        )
