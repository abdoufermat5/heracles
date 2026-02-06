"""
Mail Group Service
==================

Business logic for managing group mailing lists.
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
    MailGroupCreate,
    MailGroupRead,
    MailGroupUpdate,
    GroupMailStatus,
)
from .base import MailValidationError, MailAlreadyExistsError


logger = structlog.get_logger(__name__)


class MailGroupService(TabService):
    """
    Service for managing group mailing lists.

    Manages the hrcGroupMail objectClass and related attributes.

    LDAP Schema:
        objectClass: hrcGroupMail (auxiliary)
        attributes: mail, hrcMailServer, hrcMailAlternateAddress,
                    hrcMailForwardingAddress, hrcGroupMailLocalOnly,
                    hrcMailMaxSize
    """

    OBJECT_CLASS = "hrcGroupMail"

    MANAGED_ATTRIBUTES = [
        "mail",
        "hrcMailServer",
        "hrcMailAlternateAddress",
        "hrcMailForwardingAddress",
        "hrcGroupMailLocalOnly",
        "hrcMailMaxSize",
    ]

    def __init__(
        self, ldap_service: LdapService, config: Optional[Dict[str, Any]] = None
    ):
        """Initialize group mail service."""
        self._ldap = ldap_service
        self._config = config or {}
        self._log = logger.bind(service="mail-group")

        self._default_server = self._config.get("default_mail_server")

    def get_base_dn(self) -> str:
        """Get the LDAP base DN for scope-based ACL checks."""
        return self._ldap.base_dn

    # ========================================================================
    # Group Mail Status
    # ========================================================================

    async def get_group_mail_status(self, cn: str) -> GroupMailStatus:
        """
        Get mail status for a group.

        Args:
            cn: Group CN to check

        Returns:
            GroupMailStatus with mailing list information
        """
        group_dn = await self._find_group_dn(cn)

        entry = await self._ldap.get_by_dn(
            group_dn,
            attributes=["objectClass", "member", "memberUid"] + self.MANAGED_ATTRIBUTES,
        )

        if not entry:
            raise LdapNotFoundError(f"Group {cn} not found")

        # Check for mail objectClass
        object_classes = entry.get("objectClass", [])
        if isinstance(object_classes, str):
            object_classes = [object_classes]

        active = self.OBJECT_CLASS in object_classes

        data = None
        if active:
            data = await self._entry_to_read(entry)

        return GroupMailStatus(
            cn=cn,
            dn=group_dn,
            active=active,
            data=data,
        )

    # ========================================================================
    # Activate/Deactivate Group Mail
    # ========================================================================

    async def activate_mail(
        self, cn: str, data: MailGroupCreate
    ) -> GroupMailStatus:
        """
        Activate mailing list for a group.

        Args:
            cn: Group CN
            data: Mailing list configuration

        Returns:
            Updated GroupMailStatus
        """
        group_dn = await self._find_group_dn(cn)

        status = await self.get_group_mail_status(cn)

        if status.active:
            raise MailValidationError("Mailing list already active")

        # Validate email uniqueness
        await self._validate_email_unique(data.mail, exclude_dn=group_dn)

        for addr in data.alternate_addresses:
            await self._validate_email_unique(addr, exclude_dn=group_dn)

        # Build modifications
        mods = {
            "objectClass": ("add", [self.OBJECT_CLASS]),
            "mail": ("replace", [data.mail]),
        }

        # Mail server
        server = data.mail_server or self._default_server
        if server:
            mods["hrcMailServer"] = ("replace", [server])

        # Alternate addresses
        if data.alternate_addresses:
            mods["hrcMailAlternateAddress"] = ("replace", data.alternate_addresses)

        # Forwarding addresses
        if data.forwarding_addresses:
            mods["hrcMailForwardingAddress"] = ("replace", data.forwarding_addresses)

        # Local only
        if data.local_only:
            mods["hrcGroupMailLocalOnly"] = ("replace", ["TRUE"])

        # Max message size
        if data.max_message_size_kb is not None:
            mods["hrcMailMaxSize"] = ("replace", [str(data.max_message_size_kb)])

        await self._ldap.modify(group_dn, mods)

        self._log.info("group_mail_activated", cn=cn, mail=data.mail)

        return await self.get_group_mail_status(cn)

    async def deactivate_mail(self, cn: str) -> GroupMailStatus:
        """
        Deactivate mailing list for a group.

        Args:
            cn: Group CN

        Returns:
            Updated GroupMailStatus
        """
        group_dn = await self._find_group_dn(cn)

        status = await self.get_group_mail_status(cn)

        if not status.active:
            self._log.info("group_mail_already_inactive", cn=cn)
            return status

        # Get current entry to see which attributes actually exist
        entry = await self._ldap.get_by_dn(
            group_dn,
            attributes=["objectClass"] + self.MANAGED_ATTRIBUTES,
        )

        # Remove objectClass and attributes
        mods = {
            "objectClass": ("delete", [self.OBJECT_CLASS]),
        }

        # Only delete attributes that actually exist (except mail which may be used elsewhere)
        for attr in self.MANAGED_ATTRIBUTES:
            if attr != "mail" and attr in entry and entry[attr]:
                mods[attr] = ("delete", None)

        await self._ldap.modify(group_dn, mods)

        self._log.info("group_mail_deactivated", cn=cn)

        return await self.get_group_mail_status(cn)

    # ========================================================================
    # Update Group Mail
    # ========================================================================

    async def update_mail(
        self, cn: str, data: MailGroupUpdate
    ) -> GroupMailStatus:
        """
        Update mailing list attributes.

        Args:
            cn: Group CN
            data: Partial update data

        Returns:
            Updated GroupMailStatus
        """
        group_dn = await self._find_group_dn(cn)

        status = await self.get_group_mail_status(cn)

        if not status.active:
            raise MailValidationError("Mailing list not active")

        mods = {}

        # Primary email
        if data.mail is not None:
            await self._validate_email_unique(data.mail, exclude_dn=group_dn)
            mods["mail"] = ("replace", [data.mail])

        # Mail server
        if data.mail_server is not None:
            if data.mail_server:
                mods["hrcMailServer"] = ("replace", [data.mail_server])
            elif status.data and status.data.mail_server:
                mods["hrcMailServer"] = ("delete", None)

        # Alternate addresses
        if data.alternate_addresses is not None:
            for addr in data.alternate_addresses:
                await self._validate_email_unique(addr, exclude_dn=group_dn)
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

        # Local only
        if data.local_only is not None:
            if data.local_only:
                mods["hrcGroupMailLocalOnly"] = ("replace", ["TRUE"])
            elif status.data and status.data.local_only:
                mods["hrcGroupMailLocalOnly"] = ("delete", None)

        # Max message size
        if data.max_message_size_kb is not None:
            if data.max_message_size_kb > 0:
                mods["hrcMailMaxSize"] = ("replace", [str(data.max_message_size_kb)])
            elif status.data and status.data.max_message_size_kb:
                mods["hrcMailMaxSize"] = ("delete", None)

        if mods:
            await self._ldap.modify(group_dn, mods)
            self._log.info("group_mail_updated", cn=cn, fields=list(mods.keys()))

        return await self.get_group_mail_status(cn)

    # ========================================================================
    # Helpers
    # ========================================================================

    async def _find_group_dn(self, cn: str) -> str:
        """Find group DN by CN.
        
        Searches from the base DN with subtree scope to support
        groups in nested departments (e.g., ou=ChildDept,ou=ParentDept,dc=...).
        """
        from heracles_api.config import settings

        # Search from base DN to find groups in any OU (including nested departments)
        # Default scope is SUBTREE, so we don't need to specify it
        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=f"(&(objectClass=groupOfNames)(cn={cn}))",
            attributes=["dn"],
            size_limit=1,
        )

        if not results:
            raise LdapNotFoundError(f"Group not found: {cn}")

        return results[0].dn

    async def _validate_email_unique(
        self, email: str, exclude_dn: Optional[str] = None
    ) -> None:
        """Ensure email is not already in use."""
        from heracles_api.config import settings

        filter_str = f"(|(mail={email})(hrcMailAlternateAddress={email}))"

        results = await self._ldap.search(
            search_base=settings.LDAP_BASE_DN,
            search_filter=filter_str,
            attributes=["dn"],
        )

        for entry in results:
            if entry.dn != exclude_dn:
                raise MailAlreadyExistsError(email)

    async def _entry_to_read(self, entry: Dict[str, Any]) -> MailGroupRead:
        """Convert LDAP entry to MailGroupRead."""
        # Get mail
        mail = entry.get("mail")
        if isinstance(mail, list):
            mail = mail[0] if mail else ""

        # Get server
        server = entry.get("hrcMailServer")
        if isinstance(server, list):
            server = server[0] if server else None

        # Multi-valued
        alternates = entry.get("hrcMailAlternateAddress", [])
        if isinstance(alternates, str):
            alternates = [alternates]

        forwards = entry.get("hrcMailForwardingAddress", [])
        if isinstance(forwards, str):
            forwards = [forwards]

        # Local only - default to False if attribute doesn't exist
        local_only_str = entry.get("hrcGroupMailLocalOnly")
        if isinstance(local_only_str, list):
            local_only_str = local_only_str[0] if local_only_str else None
        local_only = bool(local_only_str and local_only_str.upper() == "TRUE")

        # Max size
        max_size_str = entry.get("hrcMailMaxSize")
        if isinstance(max_size_str, list):
            max_size_str = max_size_str[0] if max_size_str else None
        max_size = int(max_size_str) if max_size_str else None

        # Get member emails
        member_emails = await self._get_member_emails(entry)

        return MailGroupRead(
            mail=mail,
            mailServer=server,
            alternateAddresses=alternates,
            forwardingAddresses=forwards,
            localOnly=local_only,
            maxMessageSizeKb=max_size,
            memberEmails=member_emails,
        )

    async def _get_member_emails(self, entry: Dict[str, Any]) -> List[str]:
        """Get email addresses of group members."""
        emails = []

        # Get member DNs (groupOfNames style)
        members = entry.get("member", [])
        if isinstance(members, str):
            members = [members]

        for member_dn in members:
            try:
                member_entry = await self._ldap.get_by_dn(
                    member_dn,
                    attributes=["mail"],
                )
                if member_entry:
                    mail = member_entry.get("mail")
                    if isinstance(mail, list):
                        mail = mail[0] if mail else None
                    if mail:
                        emails.append(mail)
            except Exception:
                continue

        # Get memberUid (posixGroup style)
        member_uids = entry.get("memberUid", [])
        if isinstance(member_uids, str):
            member_uids = [member_uids]

        if member_uids:
            from heracles_api.config import settings

            # Search from base DN to find users in any OU (including nested departments)
            for uid in member_uids:
                try:
                    results = await self._ldap.search(
                        search_base=settings.LDAP_BASE_DN,
                        search_filter=f"(&(objectClass=inetOrgPerson)(uid={uid}))",
                        attributes=["mail"],
                        size_limit=1,
                    )
                    if results:
                        mail = results[0].get("mail")
                        if isinstance(mail, list):
                            mail = mail[0] if mail else None
                        if mail and mail not in emails:
                            emails.append(mail)
                except Exception:
                    continue

        return emails

    # ========================================================================
    # TabService Interface
    # ========================================================================

    async def is_active(self, dn: str) -> bool:
        """Check if mailing list is active on the group."""
        match = re.search(r"cn=([^,]+)", dn)
        if not match:
            return False

        cn = match.group(1)
        try:
            status = await self.get_group_mail_status(cn)
            return status.active
        except Exception:
            return False

    async def read(self, dn: str) -> Optional[MailGroupRead]:
        """Read mail tab data from the group."""
        match = re.search(r"cn=([^,]+)", dn)
        if not match:
            return None

        cn = match.group(1)
        try:
            status = await self.get_group_mail_status(cn)
            return status.data
        except Exception:
            return None

    async def activate(self, dn: str, data: Any = None) -> MailGroupRead:
        """Activate mailing list on a group."""
        match = re.search(r"cn=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid group DN")

        cn = match.group(1)

        if data is None:
            raise ValueError("Mailing list activation data required")

        if isinstance(data, dict):
            activate_data = MailGroupCreate(**data)
        elif isinstance(data, MailGroupCreate):
            activate_data = data
        else:
            raise ValueError("Invalid activation data type")

        status = await self.activate_mail(cn, activate_data)
        return status.data

    async def deactivate(self, dn: str) -> bool:
        """Deactivate mailing list on a group."""
        match = re.search(r"cn=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid group DN")

        cn = match.group(1)
        await self.deactivate_mail(cn)
        return True

    async def update(self, dn: str, data: Any) -> MailGroupRead:
        """Update mailing list data."""
        match = re.search(r"cn=([^,]+)", dn)
        if not match:
            raise ValueError("Invalid group DN")

        cn = match.group(1)

        if isinstance(data, dict):
            update_data = MailGroupUpdate(**data)
        elif isinstance(data, MailGroupUpdate):
            update_data = data
        else:
            raise ValueError("Invalid update data type")

        status = await self.update_mail(cn, update_data)
        return status.data
