"""
User Factory
============

Factory for creating user test data.
"""

from dataclasses import dataclass, field


@dataclass
class UserFactory:
    """
    Factory for creating user test data.

    Usage:
        # Create a single user
        user = UserFactory.create()

        # Create with custom attributes
        user = UserFactory.create(uid="custom", mail="custom@example.com")

        # Create multiple users
        users = UserFactory.create_batch(5)

        # Create a POSIX user
        user = UserFactory.create_posix()
    """

    uid: str = ""
    cn: str = ""
    sn: str = "User"
    given_name: str = "Test"
    mail: str = ""
    telephone: str | None = None
    title: str | None = None
    description: str | None = None
    uid_number: int | None = None
    gid_number: int | None = None
    home_directory: str | None = None
    login_shell: str | None = None
    object_classes: list[str] = field(default_factory=lambda: ["inetOrgPerson"])

    _counter: int = field(default=0, repr=False)

    @classmethod
    def create(cls, **kwargs) -> "UserFactory":
        """Create a user with generated or custom attributes."""
        cls._counter = getattr(cls, "_counter", 0) + 1
        counter = cls._counter

        defaults = {
            "uid": f"user{counter}",
            "cn": f"Test User {counter}",
            "sn": "User",
            "given_name": "Test",
            "mail": f"user{counter}@example.com",
        }
        defaults.update(kwargs)

        return cls(**defaults)

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list["UserFactory"]:
        """Create multiple users."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_posix(cls, uid_number: int = None, gid_number: int = None, **kwargs) -> "UserFactory":
        """Create a user with POSIX attributes."""
        cls._counter = getattr(cls, "_counter", 0) + 1
        counter = cls._counter

        uid = kwargs.get("uid", f"posixuser{counter}")
        uid_num = uid_number or (10000 + counter)
        gid_num = gid_number or uid_num

        defaults = {
            "uid": uid,
            "cn": f"POSIX User {counter}",
            "sn": "User",
            "given_name": "POSIX",
            "mail": f"{uid}@example.com",
            "uid_number": uid_num,
            "gid_number": gid_num,
            "home_directory": f"/home/{uid}",
            "login_shell": "/bin/bash",
            "object_classes": ["inetOrgPerson", "posixAccount", "shadowAccount"],
        }
        defaults.update(kwargs)

        return cls(**defaults)

    @classmethod
    def create_admin(cls, **kwargs) -> "UserFactory":
        """Create an admin user."""
        defaults = {
            "uid": "admin",
            "cn": "Administrator",
            "sn": "Admin",
            "given_name": "System",
            "mail": "admin@example.com",
        }
        defaults.update(kwargs)

        return cls.create(**defaults)

    @property
    def dn(self) -> str:
        """Generate DN for this user."""
        return f"uid={self.uid},ou=people,dc=heracles,dc=local"

    def to_dict(self) -> dict:
        """Convert to dictionary (API request format)."""
        data = {
            "uid": self.uid,
            "cn": self.cn,
            "sn": self.sn,
        }
        if self.given_name:
            data["givenName"] = self.given_name
        if self.mail:
            data["mail"] = self.mail
        if self.telephone:
            data["telephoneNumber"] = self.telephone
        if self.title:
            data["title"] = self.title
        if self.description:
            data["description"] = self.description

        return data

    def to_ldap_dict(self) -> dict:
        """Convert to LDAP entry format."""
        data = {
            "dn": self.dn,
            "uid": [self.uid],
            "cn": [self.cn],
            "sn": [self.sn],
            "objectClass": self.object_classes,
        }
        if self.given_name:
            data["givenName"] = [self.given_name]
        if self.mail:
            data["mail"] = [self.mail]
        if self.telephone:
            data["telephoneNumber"] = [self.telephone]
        if self.uid_number:
            data["uidNumber"] = [str(self.uid_number)]
        if self.gid_number:
            data["gidNumber"] = [str(self.gid_number)]
        if self.home_directory:
            data["homeDirectory"] = [self.home_directory]
        if self.login_shell:
            data["loginShell"] = [self.login_shell]

        return data
