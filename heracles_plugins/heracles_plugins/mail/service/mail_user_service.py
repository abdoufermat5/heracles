"""
Mail User Service
=================

Business logic for managing user mail accounts.
"""

from typing import Optional, List, Any, Dict
import re

import structlog

from heracles_api.plugins.base import TabService
from heracles_api.services.ldap_service import (
    LdapService,
    LdapNotFoundError,
)

from ..schemas import (
    MailAccountCreate,
    MailAccountRead,
    MailAccountUpdate,
    UserMailStatus,
    DeliveryMode,
)
from .base import MailValidationError, MailAlreadyExistsError


logger = structlog.get_logger(__name__)


class MailUserService(TabService):
    """
    Service for managing user mail accounts.

    Manages the hrcMailAccount objectClass and related attributes.

    LDAP Schema:
        objectClass: hrcMailAccount (auxiliary)
        attributes: mail, hrcMailServer, hrcMailQuota, hrcMailAlternateAddress,
                    hrcMailForwardingAddress, hrcMailDeliveryMode,
                    hrcVacationMessage, hrcVacationStart, hrcVacationStop
    """

    OBJECT_CLASS = "hrcMailAccount"

    MANAGED_ATTRIBUTES = [
        "mail",
        "hrcMailServer",
        "hrcMailQuota",
        "hrcMailAlternateAddress",
        "hrcMailForwardingAddress",
        "hrcMailDeliveryMode",
        "hrcVacationMessage",
        "hrcVacationStart",
        "hrcVacationStop",
    ]

    def __init__(
        self, ldap_service: LdapService, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize mail service."""
        self._ldap = ldap_service
        self._config = config or {}
        self._log = logger.bind(service="mail")

        # Configuration
        self._default_server = self._config.get("default_mail_server")
        self._default_quota = self._config.get("default_quota_mb", 1024)

    def get_base_dn(self) -> str:
        """Get the LDAP base DN for scope-based ACL checks."""
        return self._ldap.base_dn
        self._mail_domain = self._config.get("mail_domain")

    # ========================================================================
    # User Mail Status
    # ========================================================================

    async def get_user_mail_status(self, uid: str) -> UserMailStatus:
        """
        Get mail status for a user.

        Args:
            uid: User ID to check

        Returns:
            UserMailStatus with mail account information

        Raises:
            LdapNotFoundError: If user not found
        """
        user_dn = await self._find_user_dn(uid)

        entry = await self._ldap.get_by_dn(
            user_dn,
            attributes=["objectClass"] + self.MANAGED_ATTRIBUTES,
        )

        if not entry:
            raise LdapNotFoundError(f"User {uid} not found")

        # Check for mail objectClass
        object_classes = entry.get("objectClass", [])
        if isinstance(object_classes, str):
            object_classes = [object_classes]

        active = self.OBJECT_CLASS in object_classes

        data = None
        if active:
            data = self._entry_to_read(entry)

        return UserMailStatus(
            uid=uid,
            dn=user_dn,
            active=active,
            data=data,
        )

    # ========================================================================
    # Activate/Deactivate Mail
    # ========================================================================

    async def activate_mail(
        self, uid: str, data: MailAccountCreate
    ) -> UserMailStatus:
        """
        Activate mail account for a user.

        Args:
            uid: User ID
            data: Mail account configuration

        Returns:
            Updated UserMailStatus

        Raises:
            MailValidationError: If already active or validation fails
            MailAlreadyExistsError: If email already in use
        """
        user_dn = await self._find_user_dn(uid)

        # Check current status
        status = await self.get_user_mail_status(uid)

        if status.active:
            raise MailValidationError("Mail account already active")

        # Validate email uniqueness
        await self._validate_email_unique(data.mail, exclude_dn=user_dn)

        # Validate alternate addresses
        for addr in data.alternate_addresses:
            await self._validate_email_unique(addr, exclude_dn=user_dn)

        # Build modifications
        mods = {
            "objectClass": ("add", [self.OBJECT_CLASS]),
            "mail": ("replace", [data.mail]),
        }

        # Mail server
        server = data.mail_server or self._default_server
        if server:
            mods["hrcMailServer"] = ("replace", [server])

        # Quota
        quota = data.quota_mb if data.quota_mb is not None else self._default_quota
        if quota is not None:
            mods["hrcMailQuota"] = ("replace", [str(quota)])

        # Alternate addresses
        if data.alternate_addresses:
            mods["hrcMailAlternateAddress"] = ("replace", data.alternate_addresses)

        # Forwarding addresses
        if data.forwarding_addresses:
            mods["hrcMailForwardingAddress"] = ("replace", data.forwarding_addresses)

        await self._ldap.modify(user_dn, mods)

        self._log.info("mail_activated", uid=uid, mail=data.mail)

        return await self.get_user_mail_status(uid)

    async def deactivate_mail(self, uid: str) -> UserMailStatus:
        """
        Deactivate mail account for a user.

        Removes hrcMailAccount objectClass and all mail attributes.

        Args:
            uid: User ID

        Returns:
            Updated UserMailStatus
        """
        user_dn = await self._find_user_dn(uid)

        status = await self.get_user_mail_status(uid)

        if not status.active:
            self._log.info("mail_already_inactive", uid=uid)
            return status

        # Get current entry to see which attributes actually exist
        entry = await self._ldap.get_by_dn(
            user_dn,
            attributes=["objectClass"] + self.MANAGED_ATTRIBUTES,
        )

        # Remove objectClass and attributes
        mods = {
            "objectClass": ("delete", [self.OBJECT_CLASS]),
        }

        # Only delete attributes that actually exist (except mail which inetOrgPerson may use)
        for attr in self.MANAGED_ATTRIBUTES:
            if attr != "mail" and attr in entry and entry[attr]:
                mods[attr] = ("delete", None)

        await self._ldap.modify(user_dn, mods)

        self._log.info("mail_deactivated", uid=uid)

        return await self.get_user_mail_status(uid)

    # ========================================================================
    # Update Mail Account
    # ========================================================================

    async def update_mail(
        self, uid: str, data: MailAccountUpdate
    ) -> UserMailStatus:
        """
        Update mail account attributes.

        Args:
            uid: User ID
            data: Partial update data

        Returns:
            Updated UserMailStatus
        """
        user_dn = await self._find_user_dn(uid)

        status = await self.get_user_mail_status(uid)

        if not status.active:
            raise MailValidationError("Mail account not active")

        mods = {}

        # Primary email
        if data.mail is not None:
            await self._validate_email_unique(data.mail, exclude_dn=user_dn)
            mods["mail"] = ("replace", [data.mail])

        # Mail server
        if data.mail_server is not None:
            if data.mail_server:
                mods["hrcMailServer"] = ("replace", [data.mail_server])
            elif status.data and status.data.mail_server:
                mods["hrcMailServer"] = ("delete", None)

        # Quota
        if data.quota_mb is not None:
            mods["hrcMailQuota"] = ("replace", [str(data.quota_mb)])

        # Alternate addresses
        if data.alternate_addresses is not None:
            for addr in data.alternate_addresses:
                await self._validate_email_unique(addr, exclude_dn=user_dn)
            if data.alternate_addresses:
                mods["hrcMailAlternateAddress"] = ("replace", data.alternate_addresses)
            elif status.data and status.data.alternate_addresses:
                mods["hrcMailAlternateAddress"] = ("delete", None)

        # Forwarding addresses
        if data.forwarding_addresses is not None:
            if data.forwarding_addresses:
                mods["hrcMailForwardingAddress"] = (
                    "replace",
                    data.forwarding_addresses,
                )
            elif status.data and status.data.forwarding_addresses:
                mods["hrcMailForwardingAddress"] = ("delete", None)

        # Delivery mode and vacation
        if data.delivery_mode is not None or data.vacation_enabled is not None:
            current_data = status.data
            mode = (
                data.delivery_mode
                if data.delivery_mode is not None
                else current_data.delivery_mode
            )
            vacation = (
                data.vacation_enabled
                if data.vacation_enabled is not None
                else current_data.vacation_enabled
            )
            mode_flags = self._build_delivery_mode(mode, vacation)
            if mode_flags:
                mods["hrcMailDeliveryMode"] = ("replace", [mode_flags])
            elif status.data and (
                status.data.delivery_mode != DeliveryMode.NORMAL
                or status.data.vacation_enabled
            ):
                # Only delete if attribute exists in LDAP
                mods["hrcMailDeliveryMode"] = ("delete", None)

        # Vacation message
        if data.vacation_message is not None:
            if data.vacation_message:
                mods["hrcVacationMessage"] = ("replace", [data.vacation_message])
            elif status.data and status.data.vacation_message:
                mods["hrcVacationMessage"] = ("delete", None)

        # Vacation dates
        if data.vacation_start is not None:
            if data.vacation_start:
                mods["hrcVacationStart"] = ("replace", [data.vacation_start])
            elif status.data and status.data.vacation_start:
                mods["hrcVacationStart"] = ("delete", None)

        if data.vacation_end is not None:
            if data.vacation_end:
                mods["hrcVacationStop"] = ("replace", [data.vacation_end])
            elif status.data and status.data.vacation_end:
                mods["hrcVacationStop"] = ("delete", None)

        if mods:
            await self._ldap.modify(user_dn, mods)
            self._log.info("mail_updated", uid=uid, fields=list(mods.keys()))

        return await self.get_user_mail_status(uid)

    # ========================================================================
    # Helpers
    # ========================================================================

    async def _find_user_dn(self, uid: str) -> str:
        """Find user DN by UID.
        
        Searches from the base DN with subtree scope to support
        users in nested departments (e.g., ou=ChildDept,ou=ParentDept,dc=...).
        """
        from heracles_api.config import settings

        # Search from base DN to find users in any OU (including nested departments)
        # Default scope is SUBTREE, so we don't need to specify it
        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=f"(&(objectClass=inetOrgPerson)(uid={uid}))",
            attributes=["dn"],
            size_limit=1,
        )

        if not results:
            raise LdapNotFoundError(f"User not found: {uid}")

        return results[0].dn

    async def _validate_email_unique(
        self, email: str, exclude_dn: Optional[str] = None
    ) -> None:
        """Ensure email is not already in use."""
        from heracles_api.config import settings

        # Search for email in mail and hrcMailAlternateAddress
        filter_str = f"(|(mail={email})(hrcMailAlternateAddress={email}))"

        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=filter_str,
            attributes=["dn"],
        )

        for entry in results:
            if entry.dn != exclude_dn:
                raise MailAlreadyExistsError(email)

    def _entry_to_read(self, entry: Dict[str, Any]) -> MailAccountRead:
        """Convert LDAP entry to MailAccountRead."""
        # Parse delivery mode
        mode_str = entry.get("hrcMailDeliveryMode", "")
        if isinstance(mode_str, list):
            mode_str = mode_str[0] if mode_str else ""

        delivery_mode = self._parse_delivery_mode(mode_str)
        vacation_enabled = "V" in mode_str

        # Parse quota
        quota_str = entry.get("hrcMailQuota")
        if isinstance(quota_str, list):
            quota_str = quota_str[0] if quota_str else None
        quota_mb = int(quota_str) if quota_str else None

        # Get mail
        mail = entry.get("mail")
        if isinstance(mail, list):
            mail = mail[0] if mail else ""

        # Get server
        server = entry.get("hrcMailServer")
        if isinstance(server, list):
            server = server[0] if server else None

        # Get multi-valued attributes
        alternates = entry.get("hrcMailAlternateAddress", [])
        if isinstance(alternates, str):
            alternates = [alternates]

        forwards = entry.get("hrcMailForwardingAddress", [])
        if isinstance(forwards, str):
            forwards = [forwards]

        # Vacation
        vacation_msg = entry.get("hrcVacationMessage")
        if isinstance(vacation_msg, list):
            vacation_msg = vacation_msg[0] if vacation_msg else None

        vacation_start = entry.get("hrcVacationStart")
        if isinstance(vacation_start, list):
            vacation_start = vacation_start[0] if vacation_start else None

        vacation_end = entry.get("hrcVacationStop")
        if isinstance(vacation_end, list):
            vacation_end = vacation_end[0] if vacation_end else None

        return MailAccountRead(
            mail=mail,
            mailServer=server,
            quotaMb=quota_mb,
            alternateAddresses=alternates,
            forwardingAddresses=forwards,
            deliveryMode=delivery_mode,
            vacationEnabled=vacation_enabled,
            vacationMessage=vacation_msg,
            vacationStart=vacation_start,
            vacationEnd=vacation_end,
        )

    def _parse_delivery_mode(self, mode: str) -> DeliveryMode:
        """Parse delivery mode flags to enum."""
        if "I" in mode:
            return DeliveryMode.FORWARD_ONLY
        if "L" in mode:
            return DeliveryMode.LOCAL_ONLY
        return DeliveryMode.NORMAL

    def _build_delivery_mode(self, mode: DeliveryMode, vacation: bool) -> str:
        """Build delivery mode flag string."""
        flags = ""
        if mode == DeliveryMode.FORWARD_ONLY:
            flags += "I"
        elif mode == DeliveryMode.LOCAL_ONLY:
            flags += "L"
        if vacation:
            flags += "V"
        return flags

    # ========================================================================
    # TabService Interface
    # ========================================================================

    async def is_active(self, dn: str) -> bool:
        """Check if mail is active on the user."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            return False

        uid = match.group(1)
        try:
            status = await self.get_user_mail_status(uid)
            return status.active
        except Exception:
            return False

    async def read(self, dn: str) -> Optional[MailAccountRead]:
        """Read mail tab data from the object."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            return None

        uid = match.group(1)
        try:
            status = await self.get_user_mail_status(uid)
            return status.data
        except Exception:
            return None

    async def activate(self, dn: str, data: Any = None) -> MailAccountRead:
        """Activate mail on a user.

        Accepts a ``MailAccountCreate``, a raw dict (e.g. from a template
        plugin-activation config), or ``None``.

        Template configs use keys like ``mailDomain``, ``mailQuota``,
        ``mailServer`` — these are translated to the proper create-schema
        fields automatically.
        """
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")

        uid = match.group(1)

        if data is None:
            data = {}

        if isinstance(data, dict):
            # Translate template-style keys to MailAccountCreate fields
            create_dict: Dict[str, Any] = {}

            # Resolve mail address:
            #  1. Explicit "mail" in template config → use it
            #  2. Read from the user's existing LDAP entry (set via the user form)
            #  3. Auto-generate from uid + mailDomain (template key)
            #  4. Last resort: uid@default_domain
            if "mail" in data:
                create_dict["mail"] = data["mail"]
            else:
                # Try to read the user's existing mail from their LDAP entry
                existing_mail = None
                try:
                    entry = await self._ldap.get_by_dn(dn, attributes=["mail"])
                    if entry:
                        raw = entry.get("mail")
                        if isinstance(raw, list) and raw:
                            existing_mail = raw[0]
                        elif isinstance(raw, str) and raw:
                            existing_mail = raw
                except Exception:
                    pass

                if existing_mail:
                    create_dict["mail"] = existing_mail
                elif "mailDomain" in data:
                    create_dict["mail"] = f"{uid}@{data['mailDomain']}"
                else:
                    domain = self._config.get("default_mail_domain", "localdomain")
                    create_dict["mail"] = f"{uid}@{domain}"

            # Map template keys → create-schema aliases
            if "mailServer" in data:
                create_dict["mailServer"] = data["mailServer"]
            if "mailQuota" in data:
                create_dict["quotaMb"] = data["mailQuota"]
            elif "quotaMb" in data:
                create_dict["quotaMb"] = data["quotaMb"]
            if "alternateAddresses" in data:
                create_dict["alternateAddresses"] = data["alternateAddresses"]
            if "forwardingAddresses" in data:
                create_dict["forwardingAddresses"] = data["forwardingAddresses"]

            activate_data = MailAccountCreate(**create_dict)
        elif isinstance(data, MailAccountCreate):
            activate_data = data
        else:
            raise ValueError("Invalid activation data type")

        status = await self.activate_mail(uid, activate_data)
        return status.data

    async def deactivate(self, dn: str) -> bool:
        """Deactivate mail on a user."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")

        uid = match.group(1)
        await self.deactivate_mail(uid)
        return True

    async def update(self, dn: str, data: Any) -> MailAccountRead:
        """Update mail tab data."""
        match = re.search(r"uid=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid user DN")

        uid = match.group(1)

        if isinstance(data, dict):
            update_data = MailAccountUpdate(**data)
        elif isinstance(data, MailAccountUpdate):
            update_data = data
        else:
            raise ValueError("Invalid update data type")

        status = await self.update_mail(uid, update_data)
        return status.data

    # ========================================================================
    # Import / Export / Template extension points
    # ========================================================================

    @classmethod
    def get_import_fields(cls) -> list:
        from heracles_api.plugins.base import PluginFieldDefinition
        return [
            PluginFieldDefinition(name="mail", label="Email Address", required=True),
            PluginFieldDefinition(name="hrcMailServer", label="Mail Server"),
            PluginFieldDefinition(name="hrcMailQuota", label="Mail Quota"),
            PluginFieldDefinition(name="hrcMailAlternateAddress", label="Alternate Addresses"),
            PluginFieldDefinition(name="hrcMailForwardingAddress", label="Forwarding Address"),
        ]

    @classmethod
    def get_export_fields(cls) -> list:
        from heracles_api.plugins.base import PluginFieldDefinition
        return [
            PluginFieldDefinition(name="mail", label="Email Address"),
            PluginFieldDefinition(name="hrcMailServer", label="Mail Server"),
            PluginFieldDefinition(name="hrcMailQuota", label="Mail Quota (MB)"),
            PluginFieldDefinition(name="hrcMailAlternateAddress", label="Alternate Addresses"),
            PluginFieldDefinition(name="hrcMailForwardingAddress", label="Forwarding Address"),
            PluginFieldDefinition(name="hrcMailDeliveryMode", label="Delivery Mode"),
            PluginFieldDefinition(name="hrcVacationMessage", label="Vacation Message"),
            PluginFieldDefinition(name="hrcVacationStart", label="Vacation Start"),
            PluginFieldDefinition(name="hrcVacationStop", label="Vacation End"),
        ]

    @classmethod
    def get_template_fields(cls) -> list:
        from heracles_api.plugins.base import PluginTemplateField
        return [
            PluginTemplateField(
                key="mailDomain", label="Mail Domain",
                field_type="string", default_value="heracles.local",
                description="Domain for auto-generated email address",
            ),
            PluginTemplateField(
                key="mailQuota", label="Default Quota (MB)",
                field_type="integer", default_value=0,
                description="0 = unlimited",
            ),
            PluginTemplateField(
                key="mailServer", label="Mail Server",
                field_type="string",
                description="IMAP/POP server hostname",
            ),
        ]
