"""
Group Factory
=============

Factory for creating group test data.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GroupFactory:
    """
    Factory for creating group test data.

    Usage:
        # Create a standard LDAP group
        group = GroupFactory.create()

        # Create with members
        group = GroupFactory.create(cn="devs", members=["user1", "user2"])

        # Create a POSIX group
        group = GroupFactory.create_posix()

        # Create a mixed group
        group = GroupFactory.create_mixed()
    """

    cn: str = ""
    description: str = ""
    members: List[str] = field(default_factory=list)
    member_uids: List[str] = field(default_factory=list)
    gid_number: Optional[int] = None
    object_classes: List[str] = field(default_factory=lambda: ["groupOfNames", "top"])

    _counter: int = field(default=0, repr=False)

    @classmethod
    def create(cls, **kwargs) -> "GroupFactory":
        """Create a standard LDAP group."""
        cls._counter = getattr(cls, "_counter", 0) + 1
        counter = cls._counter

        defaults = {
            "cn": f"group{counter}",
            "description": f"Test Group {counter}",
            "members": [],
        }
        defaults.update(kwargs)

        return cls(**defaults)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> List["GroupFactory"]:
        """Create multiple groups."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_posix(cls, gid_number: int = None, **kwargs) -> "GroupFactory":
        """Create a POSIX group."""
        cls._counter = getattr(cls, "_counter", 0) + 1
        counter = cls._counter

        cn = kwargs.get("cn", f"posixgroup{counter}")
        gid = gid_number or (10000 + counter)

        defaults = {
            "cn": cn,
            "description": f"POSIX Group {counter}",
            "gid_number": gid,
            "member_uids": [],
            "object_classes": ["posixGroup", "top"],
        }
        defaults.update(kwargs)

        return cls(**defaults)

    @classmethod
    def create_mixed(cls, gid_number: int = None, **kwargs) -> "GroupFactory":
        """Create a mixed group (groupOfNames + posixGroupAux)."""
        cls._counter = getattr(cls, "_counter", 0) + 1
        counter = cls._counter

        cn = kwargs.get("cn", f"mixedgroup{counter}")
        gid = gid_number or (10000 + counter)

        defaults = {
            "cn": cn,
            "description": f"Mixed Group {counter}",
            "gid_number": gid,
            "members": [],
            "member_uids": [],
            "object_classes": ["groupOfNames", "posixGroupAux", "top"],
        }
        defaults.update(kwargs)

        return cls(**defaults)

    @classmethod
    def create_admins(cls, **kwargs) -> "GroupFactory":
        """Create an admins group."""
        defaults = {
            "cn": "admins",
            "description": "Administrators",
            "members": ["admin"],
        }
        defaults.update(kwargs)

        return cls.create(**defaults)

    @property
    def dn(self) -> str:
        """Generate DN for this group."""
        return f"cn={self.cn},ou=groups,dc=heracles,dc=local"

    @property
    def member_dns(self) -> List[str]:
        """Generate member DNs."""
        return [
            f"uid={m},ou=people,dc=heracles,dc=local"
            for m in self.members
        ]

    def to_dict(self) -> dict:
        """Convert to dictionary (API request format)."""
        data = {
            "cn": self.cn,
            "description": self.description,
        }
        if self.members:
            data["members"] = self.members
        if self.gid_number:
            data["gidNumber"] = self.gid_number

        return data

    def to_ldap_dict(self) -> dict:
        """Convert to LDAP entry format."""
        data = {
            "dn": self.dn,
            "cn": [self.cn],
            "description": [self.description] if self.description else [],
            "objectClass": self.object_classes,
        }

        if "groupOfNames" in self.object_classes:
            data["member"] = self.member_dns or ["cn=placeholder,dc=heracles,dc=local"]

        if self.gid_number:
            data["gidNumber"] = [str(self.gid_number)]

        if self.member_uids:
            data["memberUid"] = self.member_uids

        return data
