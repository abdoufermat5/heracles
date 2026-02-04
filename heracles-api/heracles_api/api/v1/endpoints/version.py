"""
Version Endpoint
================

Exposes version information for all Heracles components.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from heracles_api import __version__ as api_version


router = APIRouter(prefix="/version", tags=["Version"])


class PluginVersionInfo(BaseModel):
    """Version info for a single plugin."""

    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version (semver)")
    minimum_api_version: Optional[str] = Field(
        None, description="Minimum API version required"
    )


class ComponentVersions(BaseModel):
    """Version information for all Heracles components."""

    api: str = Field(..., description="Heracles API version")
    core: Optional[str] = Field(None, description="Heracles Core (Rust) version")
    ui: Optional[str] = Field(
        None, description="Heracles UI version (set by frontend)"
    )
    plugins_package: Optional[str] = Field(
        None, description="Heracles plugins package version"
    )
    plugins: List[PluginVersionInfo] = Field(
        default_factory=list, description="Individual plugin versions"
    )
    supported_api_versions: List[str] = Field(
        default_factory=lambda: ["v1"], description="Supported API versions"
    )


def _get_core_version() -> Optional[str]:
    """Get heracles-core version if available."""
    try:
        import heracles_core

        return getattr(heracles_core, "__version__", None)
    except ImportError:
        return None


def _get_plugins_package_version() -> Optional[str]:
    """Get heracles_plugins package version."""
    try:
        from importlib.metadata import version

        return version("heracles_plugins")
    except Exception:
        # Fallback: try to import and check for __version__
        try:
            import heracles_plugins

            return getattr(heracles_plugins, "__version__", None)
        except ImportError:
            return None


def _get_loaded_plugins() -> List[PluginVersionInfo]:
    """Get version info for all loaded plugins."""
    plugins = []
    try:
        from heracles_api.plugins.registry import plugin_registry

        for plugin_name, plugin_instance in plugin_registry._plugins.items():
            info = plugin_instance.info()
            plugins.append(
                PluginVersionInfo(
                    name=info.name,
                    version=info.version,
                    minimum_api_version=getattr(info, "minimum_api_version", None),
                )
            )
    except Exception:
        pass
    return plugins


@router.get("", response_model=ComponentVersions)
async def get_versions() -> ComponentVersions:
    """
    Get version information for all Heracles components.

    Returns version strings for:
    - API backend
    - Core Rust library (if available)
    - Plugins package
    - Individual loaded plugins

    This endpoint is public (no authentication required) to allow
    clients to check compatibility before authenticating.
    """
    return ComponentVersions(
        api=api_version,
        core=_get_core_version(),
        plugins_package=_get_plugins_package_version(),
        plugins=_get_loaded_plugins(),
        supported_api_versions=["v1"],
    )


@router.get("/compatibility")
async def check_compatibility(
    client_version: Optional[str] = None,
    client_type: Optional[str] = None,
) -> Dict:
    """
    Check if a client version is compatible with this API.

    Args:
        client_version: The client's version string (e.g., "0.8.0-beta")
        client_type: The client type ("ui", "cli", "sdk")

    Returns:
        Compatibility status and any warnings.
    """
    from packaging import version as pkg_version

    result = {
        "compatible": True,
        "api_version": api_version,
        "warnings": [],
        "errors": [],
    }

    if not client_version:
        result["warnings"].append("No client version provided, cannot verify compatibility")
        return result

    try:
        # Parse versions (strip -alpha, -beta, -rc suffixes for comparison)
        api_base = api_version.split("-")[0]
        client_base = client_version.split("-")[0]

        api_ver = pkg_version.parse(api_base)
        client_ver = pkg_version.parse(client_base)

        # Major version mismatch is incompatible
        if api_ver.major != client_ver.major:
            result["compatible"] = False
            result["errors"].append(
                f"Major version mismatch: API {api_version}, client {client_version}"
            )
        # Minor version: warn if client is newer
        elif client_ver.minor > api_ver.minor:
            result["warnings"].append(
                f"Client version ({client_version}) is newer than API ({api_version}). "
                "Some features may not be available."
            )
        # Client is older: may miss features
        elif client_ver.minor < api_ver.minor:
            result["warnings"].append(
                f"Client version ({client_version}) is older than API ({api_version}). "
                "Consider upgrading for new features."
            )

    except Exception as e:
        result["warnings"].append(f"Could not parse versions: {e}")

    return result
