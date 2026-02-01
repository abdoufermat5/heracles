"""
SSH Plugin Definition
=====================

Main plugin class that registers SSH key management functionality.
"""

from typing import Any, Dict, List, Optional

from heracles_api.plugins.base import (
    ConfigField,
    ConfigFieldOption,
    ConfigFieldType,
    ConfigFieldValidation,
    ConfigSection,
    Plugin,
    PluginInfo,
    TabDefinition,
)

from .schemas import (
    SSHKeyCreate,
    SSHKeyRead,
    UserSSHStatus,
)
from .service import SSHService
from .routes import router


class SSHPlugin(Plugin):
    """
    SSH key management plugin.
    
    Provides SSH public key management via the ldapPublicKey objectClass.
    
    Compatible with OpenSSH LDAP integration (AuthorizedKeysCommand).
    
    Configuration:
        - allowed_key_types: List of allowed SSH key types
        - min_key_bits: Minimum key size in bits
        - require_comment: Require a comment/label for keys
        - max_keys_per_user: Maximum keys per user (0 = unlimited)
    """
    
    @staticmethod
    def info() -> PluginInfo:
        """Return plugin metadata."""
        return PluginInfo(
            name="ssh",
            version="1.0.0",
            description="SSH public key management (ldapPublicKey)",
            author="Heracles Team",
            object_types=["user"],
            object_classes=["ldapPublicKey"],
            dependencies=[],  # No hard dependencies
            optional_dependencies=["posix"],  # Works better with POSIX users
            required_config=[],
            priority=25,  # After POSIX
        )
    
    @staticmethod
    def tabs() -> List[TabDefinition]:
        """Define tabs provided by this plugin."""
        return [
            TabDefinition(
                id="ssh",
                label="SSH Keys",
                icon="key",
                object_type="user",
                activation_filter="(objectClass=inetOrgPerson)",
                schema_file="schema_ssh.json",
                service_class=SSHService,
                create_schema=SSHKeyCreate,
                read_schema=SSHKeyRead,
                update_schema=None,  # Keys are add/remove only
                required=False,  # Optional tab for users
            ),
        ]
    
    @staticmethod
    def config_schema() -> List[ConfigSection]:
        """
        Define configuration schema for SSH plugin.
        
        Returns:
            List of configuration sections with fields.
        """
        return [
            ConfigSection(
                id="key_types",
                label="Allowed Key Types",
                description="Configure which SSH key types are allowed",
                fields=[
                    ConfigField(
                        key="allowed_key_types",
                        label="Allowed Key Types",
                        description="SSH key types that can be added",
                        field_type=ConfigFieldType.MULTISELECT,
                        default_value=["ssh-rsa", "ssh-ed25519", "ecdsa-sha2-nistp256", "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521"],
                        options=[
                            ConfigFieldOption(value="ssh-rsa", label="RSA (ssh-rsa)"),
                            ConfigFieldOption(value="ssh-ed25519", label="Ed25519 (ssh-ed25519)"),
                            ConfigFieldOption(value="ecdsa-sha2-nistp256", label="ECDSA P-256"),
                            ConfigFieldOption(value="ecdsa-sha2-nistp384", label="ECDSA P-384"),
                            ConfigFieldOption(value="ecdsa-sha2-nistp521", label="ECDSA P-521"),
                            ConfigFieldOption(value="ssh-dss", label="DSA (ssh-dss) - Deprecated"),
                            ConfigFieldOption(value="sk-ssh-ed25519@openssh.com", label="Ed25519-SK (Security Key)"),
                            ConfigFieldOption(value="sk-ecdsa-sha2-nistp256@openssh.com", label="ECDSA-SK (Security Key)"),
                        ],
                    ),
                    ConfigField(
                        key="reject_dsa_keys",
                        label="Reject DSA Keys",
                        description="Reject DSA keys regardless of allowed types (DSA is deprecated)",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
            ConfigSection(
                id="key_security",
                label="Key Security",
                description="Security requirements for SSH keys",
                fields=[
                    ConfigField(
                        key="min_rsa_bits",
                        label="Minimum RSA Key Size",
                        description="Minimum RSA key size in bits",
                        field_type=ConfigFieldType.SELECT,
                        default_value=2048,
                        options=[
                            ConfigFieldOption(value=1024, label="1024 bits (Insecure)"),
                            ConfigFieldOption(value=2048, label="2048 bits"),
                            ConfigFieldOption(value=3072, label="3072 bits"),
                            ConfigFieldOption(value=4096, label="4096 bits"),
                        ],
                    ),
                    ConfigField(
                        key="validate_key_format",
                        label="Validate Key Format",
                        description="Validate SSH key format and structure",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                    ConfigField(
                        key="check_key_fingerprint",
                        label="Check Duplicate Fingerprints",
                        description="Prevent adding duplicate keys based on fingerprint",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=True,
                    ),
                ],
            ),
            ConfigSection(
                id="limits",
                label="Limits",
                description="Key management limits",
                fields=[
                    ConfigField(
                        key="max_keys_per_user",
                        label="Maximum Keys Per User",
                        description="Maximum number of SSH keys per user (0 = unlimited)",
                        field_type=ConfigFieldType.INTEGER,
                        default_value=10,
                        validation=ConfigFieldValidation(
                            min_value=0,
                            max_value=100,
                        ),
                    ),
                    ConfigField(
                        key="require_comment",
                        label="Require Key Comment",
                        description="Require a comment/label for all SSH keys",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                ],
            ),
            ConfigSection(
                id="display",
                label="Display Settings",
                description="How SSH keys are displayed in the UI",
                fields=[
                    ConfigField(
                        key="show_full_key",
                        label="Show Full Key",
                        description="Show full public key in list views (vs truncated)",
                        field_type=ConfigFieldType.BOOLEAN,
                        default_value=False,
                    ),
                    ConfigField(
                        key="fingerprint_hash",
                        label="Fingerprint Hash",
                        description="Hash algorithm for key fingerprints",
                        field_type=ConfigFieldType.SELECT,
                        default_value="SHA256",
                        options=[
                            ConfigFieldOption(value="SHA256", label="SHA-256"),
                            ConfigFieldOption(value="MD5", label="MD5 (Legacy)"),
                        ],
                    ),
                ],
            ),
        ]
    
    @staticmethod
    def default_config() -> Dict[str, Any]:
        """
        Return default configuration values.
        
        Returns:
            Dictionary of default configuration values.
        """
        return {
            # Key types
            "allowed_key_types": [
                "ssh-rsa",
                "ssh-ed25519",
                "ecdsa-sha2-nistp256",
                "ecdsa-sha2-nistp384",
                "ecdsa-sha2-nistp521",
            ],
            "reject_dsa_keys": True,
            # Key security
            "min_rsa_bits": 2048,
            "validate_key_format": True,
            "check_key_fingerprint": True,
            # Limits
            "max_keys_per_user": 10,
            "require_comment": False,
            # Display
            "show_full_key": False,
            "fingerprint_hash": "SHA256",
        }
    
    @staticmethod
    def validate_config_business_rules(config: Dict[str, Any]) -> Optional[str]:
        """
        Validate configuration business rules.
        
        Args:
            config: Configuration dictionary to validate.
            
        Returns:
            Error message if validation fails, None otherwise.
        """
        # Check that at least one key type is allowed
        allowed_types = config.get("allowed_key_types", [])
        if not allowed_types:
            return "At least one SSH key type must be allowed"
        
        # Warn if DSA is in allowed types but reject_dsa_keys is True
        reject_dsa = config.get("reject_dsa_keys", True)
        if reject_dsa and "ssh-dss" in allowed_types:
            # This is just a configuration inconsistency, not an error
            pass
        
        return None

    def on_config_change(
        self,
        old_config: Dict[str, Any],
        new_config: Dict[str, Any],
        changed_keys: List[str],
    ) -> None:
        """
        Handle configuration changes.
        
        Args:
            old_config: Previous configuration.
            new_config: New configuration.
            changed_keys: List of changed configuration keys.
        """
        self.logger.info(f"SSH plugin configuration updated: {changed_keys}")
        
        # Log security-related changes
        if "allowed_key_types" in changed_keys:
            self.logger.info(
                f"Allowed key types changed: {new_config.get('allowed_key_types')}"
            )
        
        if "min_rsa_bits" in changed_keys:
            self.logger.info(
                f"Min RSA bits changed: {new_config.get('min_rsa_bits')}"
            )
    
    def on_activate(self) -> None:
        """Called when plugin is activated."""
        allowed_types = self.get_config_value("allowed_key_types", [])
        self.logger.info(f"SSH plugin activated (allowed types: {allowed_types})")
    
    def on_deactivate(self) -> None:
        """Called when plugin is deactivated."""
        self.logger.info("SSH plugin deactivated")

    @staticmethod
    def routes() -> List[Any]:
        """Return API routers for SSH endpoints."""
        return [router]
