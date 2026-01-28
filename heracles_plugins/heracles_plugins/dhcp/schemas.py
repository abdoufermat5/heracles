"""
DHCP Plugin Schemas
===================

Pydantic models for DHCP configuration data validation.

Object Types:
- service: Root DHCP service configuration
- shared_network: Shared network configuration
- subnet: Subnet with IP range and netmask
- pool: Dynamic IP address pool
- host: Host reservation with fixed IP/MAC
- group: Logical grouping of hosts
- class_: Client classification
- subclass: Subclass for client matching
- tsig_key: TSIG key for DNS updates
- dns_zone: DNS zone for dynamic updates
- failover_peer: Failover configuration

All DHCP objects support:
- cn (common name) - required
- dhcpStatements - configuration statements (multi-valued)
- dhcpOption - DHCP options (multi-valued)
- dhcpComments - description/comments
"""

from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# ============================================================================
# Enums
# ============================================================================

class DhcpObjectType(str, Enum):
    """DHCP object types supported by the plugin."""
    
    SERVICE = "service"
    SHARED_NETWORK = "shared-network"
    SUBNET = "subnet"
    POOL = "pool"
    HOST = "host"
    GROUP = "group"
    CLASS = "class"
    SUBCLASS = "subclass"
    TSIG_KEY = "tsig-key"
    DNS_ZONE = "dns-zone"
    FAILOVER_PEER = "failover-peer"
    
    @classmethod
    def get_object_class(cls, obj_type: "DhcpObjectType") -> str:
        """Get the LDAP objectClass for a DHCP object type."""
        mapping = {
            cls.SERVICE: "dhcpService",
            cls.SHARED_NETWORK: "dhcpSharedNetwork",
            cls.SUBNET: "dhcpSubnet",
            cls.POOL: "dhcpPool",
            cls.HOST: "dhcpHost",
            cls.GROUP: "dhcpGroup",
            cls.CLASS: "dhcpClass",
            cls.SUBCLASS: "dhcpSubClass",
            cls.TSIG_KEY: "dhcpTSigKey",
            cls.DNS_ZONE: "dhcpDnsZone",
            cls.FAILOVER_PEER: "dhcpFailOverPeer",
        }
        return mapping[obj_type]
    
    @classmethod
    def from_object_class(cls, object_class: str) -> Optional["DhcpObjectType"]:
        """Get the DhcpObjectType from an LDAP objectClass."""
        mapping = {
            "dhcpService": cls.SERVICE,
            "dhcpSharedNetwork": cls.SHARED_NETWORK,
            "dhcpSubnet": cls.SUBNET,
            "dhcpPool": cls.POOL,
            "dhcpHost": cls.HOST,
            "dhcpGroup": cls.GROUP,
            "dhcpClass": cls.CLASS,
            "dhcpSubClass": cls.SUBCLASS,
            "dhcpTSigKey": cls.TSIG_KEY,
            "dhcpDnsZone": cls.DNS_ZONE,
            "dhcpFailOverPeer": cls.FAILOVER_PEER,
        }
        return mapping.get(object_class)
    
    @classmethod
    def get_allowed_children(cls, obj_type: "DhcpObjectType") -> List["DhcpObjectType"]:
        """Get allowed child object types for a parent type."""
        mapping = {
            cls.SERVICE: [
                cls.SHARED_NETWORK, cls.SUBNET, cls.GROUP, cls.HOST,
                cls.CLASS, cls.TSIG_KEY, cls.DNS_ZONE, cls.FAILOVER_PEER
            ],
            cls.SHARED_NETWORK: [
                cls.SUBNET, cls.POOL, cls.TSIG_KEY, cls.DNS_ZONE, cls.FAILOVER_PEER
            ],
            cls.SUBNET: [
                cls.POOL, cls.GROUP, cls.HOST, cls.CLASS,
                cls.TSIG_KEY, cls.DNS_ZONE, cls.FAILOVER_PEER
            ],
            cls.GROUP: [cls.HOST],
            cls.CLASS: [cls.SUBCLASS],
            cls.POOL: [],
            cls.HOST: [],
            cls.SUBCLASS: [],
            cls.TSIG_KEY: [],
            cls.DNS_ZONE: [],
            cls.FAILOVER_PEER: [],
        }
        return mapping.get(obj_type, [])


class TsigKeyAlgorithm(str, Enum):
    """TSIG key algorithms."""
    
    HMAC_MD5 = "hmac-md5"
    HMAC_SHA1 = "hmac-sha1"
    HMAC_SHA256 = "hmac-sha256"
    HMAC_SHA512 = "hmac-sha512"


# ============================================================================
# Validators
# ============================================================================

def validate_ip_address(ip: str) -> str:
    """Validate and normalize an IP address."""
    ip = ip.strip()
    
    # Basic IPv4 validation
    ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
    
    if re.match(ipv4_pattern, ip):
        octets = ip.split(".")
        if all(0 <= int(o) <= 255 for o in octets):
            return ip
        raise ValueError(f"Invalid IPv4 address: {ip}")
    
    raise ValueError(f"Invalid IP address format: {ip}")


def validate_ip_range(ip_range: str) -> str:
    """Validate an IP range (start end or single IP)."""
    ip_range = ip_range.strip()
    parts = ip_range.split()
    
    if len(parts) == 1:
        # Single IP
        validate_ip_address(parts[0])
    elif len(parts) == 2:
        # Range: start end
        validate_ip_address(parts[0])
        validate_ip_address(parts[1])
    else:
        raise ValueError(f"Invalid IP range format: {ip_range}")
    
    return ip_range


def validate_mac_address(mac: str) -> str:
    """Validate and normalize a MAC address to 'ethernet XX:XX:XX:XX:XX:XX' format."""
    mac = mac.strip()
    
    # Handle 'ethernet XX:XX:XX:XX:XX:XX' format
    if mac.lower().startswith("ethernet "):
        mac_part = mac[9:].strip()
    else:
        mac_part = mac
    
    # Normalize to colon-separated format
    mac_clean = re.sub(r"[:-]", "", mac_part).upper()
    
    if not re.match(r"^[0-9A-F]{12}$", mac_clean):
        raise ValueError(f"Invalid MAC address format: {mac}")
    
    # Format as 'ethernet XX:XX:XX:XX:XX:XX'
    mac_formatted = ":".join(mac_clean[i:i+2] for i in range(0, 12, 2))
    return f"ethernet {mac_formatted}"


def validate_netmask(netmask: int) -> int:
    """Validate netmask (CIDR notation, 0-32)."""
    if not 0 <= netmask <= 32:
        raise ValueError(f"Netmask must be between 0 and 32, got {netmask}")
    return netmask


# ============================================================================
# Base Schemas
# ============================================================================

class DhcpBase(BaseModel):
    """Base attributes for all DHCP objects."""
    
    dhcp_statements: List[str] = Field(
        default_factory=list,
        alias="dhcpStatements",
        description="DHCP configuration statements",
    )
    dhcp_options: List[str] = Field(
        default_factory=list,
        alias="dhcpOption",
        description="DHCP options to send to clients",
    )
    comments: Optional[str] = Field(
        default=None,
        alias="dhcpComments",
        max_length=1024,
        description="Comments/description",
    )
    
    @field_validator("dhcp_statements", "dhcp_options", mode="before")
    @classmethod
    def ensure_list(cls, v):
        """Ensure value is a list."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Service Schemas
# ============================================================================

class DhcpServiceCreate(DhcpBase):
    """Schema for creating a DHCP service (root configuration)."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Service name (e.g., 'main-dhcp')",
    )
    dhcp_primary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpPrimaryDN",
        description="DN of the primary DHCP server",
    )
    dhcp_secondary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpSecondaryDN",
        description="DN of the secondary DHCP server",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate service name."""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError("Service name must start with alphanumeric and contain only alphanumeric, underscore, or hyphen")
        return v


class DhcpServiceUpdate(DhcpBase):
    """Schema for updating a DHCP service."""
    
    dhcp_primary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpPrimaryDN",
    )
    dhcp_secondary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpSecondaryDN",
    )


class DhcpServiceRead(DhcpBase):
    """Schema for reading a DHCP service."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Service name")
    dhcp_primary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpPrimaryDN",
    )
    dhcp_secondary_dn: Optional[str] = Field(
        default=None,
        alias="dhcpSecondaryDN",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SERVICE,
        alias="objectType",
    )


class DhcpServiceListItem(BaseModel):
    """Schema for service in list responses."""
    
    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SERVICE,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Subnet Schemas
# ============================================================================

class SubnetCreate(DhcpBase):
    """Schema for creating a DHCP subnet."""
    
    cn: str = Field(
        ...,
        description="Network address (e.g., '192.168.1.0')",
    )
    dhcp_netmask: int = Field(
        ...,
        ge=0,
        le=32,
        alias="dhcpNetMask",
        description="Subnet mask length (CIDR notation)",
    )
    dhcp_range: List[str] = Field(
        default_factory=list,
        alias="dhcpRange",
        description="IP ranges (e.g., ['192.168.1.100 192.168.1.200'])",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate network address."""
        return validate_ip_address(v)
    
    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        return [validate_ip_range(r) for r in v]


class SubnetUpdate(DhcpBase):
    """Schema for updating a DHCP subnet."""
    
    dhcp_netmask: Optional[int] = Field(
        default=None,
        ge=0,
        le=32,
        alias="dhcpNetMask",
    )
    dhcp_range: Optional[List[str]] = Field(
        default=None,
        alias="dhcpRange",
    )
    
    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            return None
        if isinstance(v, str):
            v = [v]
        return [validate_ip_range(r) for r in v]


class SubnetRead(DhcpBase):
    """Schema for reading a DHCP subnet."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Network address")
    dhcp_netmask: int = Field(..., alias="dhcpNetMask")
    dhcp_range: List[str] = Field(
        default_factory=list,
        alias="dhcpRange",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
        description="Parent object DN",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SUBNET,
        alias="objectType",
    )


class SubnetListItem(BaseModel):
    """Schema for subnet in list responses."""
    
    dn: str
    cn: str
    dhcp_netmask: int = Field(..., alias="dhcpNetMask")
    dhcp_range: List[str] = Field(default_factory=list, alias="dhcpRange")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SUBNET,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Pool Schemas
# ============================================================================

class PoolCreate(DhcpBase):
    """Schema for creating a DHCP pool."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Pool name",
    )
    dhcp_range: List[str] = Field(
        ...,
        min_length=1,
        alias="dhcpRange",
        description="IP ranges (required)",
    )
    dhcp_permit_list: List[str] = Field(
        default_factory=list,
        alias="dhcpPermitList",
        description="Permit list (allow/deny rules)",
    )
    
    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            raise ValueError("At least one IP range is required")
        if isinstance(v, str):
            v = [v]
        if len(v) == 0:
            raise ValueError("At least one IP range is required")
        return [validate_ip_range(r) for r in v]


class PoolUpdate(DhcpBase):
    """Schema for updating a DHCP pool."""
    
    dhcp_range: Optional[List[str]] = Field(
        default=None,
        alias="dhcpRange",
    )
    dhcp_permit_list: Optional[List[str]] = Field(
        default=None,
        alias="dhcpPermitList",
    )
    
    @field_validator("dhcp_range", mode="before")
    @classmethod
    def validate_ranges(cls, v):
        """Validate IP ranges."""
        if v is None:
            return None
        if isinstance(v, str):
            v = [v]
        return [validate_ip_range(r) for r in v]


class PoolRead(DhcpBase):
    """Schema for reading a DHCP pool."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Pool name")
    dhcp_range: List[str] = Field(..., alias="dhcpRange")
    dhcp_permit_list: List[str] = Field(
        default_factory=list,
        alias="dhcpPermitList",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.POOL,
        alias="objectType",
    )


class PoolListItem(BaseModel):
    """Schema for pool in list responses."""
    
    dn: str
    cn: str
    dhcp_range: List[str] = Field(..., alias="dhcpRange")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.POOL,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Host Schemas
# ============================================================================

class HostCreate(DhcpBase):
    """Schema for creating a DHCP host reservation."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Hostname",
    )
    dhcp_hw_address: str = Field(
        ...,
        alias="dhcpHWAddress",
        description="Hardware address (MAC)",
    )
    fixed_address: Optional[str] = Field(
        default=None,
        alias="fixedAddress",
        description="Fixed IP address (stored in dhcpStatements)",
    )
    system_dn: Optional[str] = Field(
        default=None,
        alias="systemDn",
        description="DN of linked system (from systems plugin)",
    )
    
    @field_validator("dhcp_hw_address")
    @classmethod
    def validate_hw_address(cls, v):
        """Validate and normalize hardware address."""
        return validate_mac_address(v)
    
    @field_validator("fixed_address")
    @classmethod
    def validate_fixed_address(cls, v):
        """Validate fixed IP address."""
        if v is not None:
            return validate_ip_address(v)
        return v
    
    @model_validator(mode="after")
    def add_fixed_address_statement(self):
        """Add fixed-address to dhcpStatements if provided."""
        if self.fixed_address:
            statement = f"fixed-address {self.fixed_address}"
            if statement not in self.dhcp_statements:
                self.dhcp_statements.append(statement)
        return self


class HostUpdate(DhcpBase):
    """Schema for updating a DHCP host."""
    
    dhcp_hw_address: Optional[str] = Field(
        default=None,
        alias="dhcpHWAddress",
    )
    fixed_address: Optional[str] = Field(
        default=None,
        alias="fixedAddress",
    )
    system_dn: Optional[str] = Field(
        default=None,
        alias="systemDn",
    )
    
    @field_validator("dhcp_hw_address")
    @classmethod
    def validate_hw_address(cls, v):
        """Validate and normalize hardware address."""
        if v is not None:
            return validate_mac_address(v)
        return v
    
    @field_validator("fixed_address")
    @classmethod
    def validate_fixed_address(cls, v):
        """Validate fixed IP address."""
        if v is not None:
            return validate_ip_address(v)
        return v


class HostRead(DhcpBase):
    """Schema for reading a DHCP host."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Hostname")
    dhcp_hw_address: Optional[str] = Field(
        default=None,
        alias="dhcpHWAddress",
    )
    fixed_address: Optional[str] = Field(
        default=None,
        alias="fixedAddress",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    system_dn: Optional[str] = Field(
        default=None,
        alias="systemDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.HOST,
        alias="objectType",
    )


class HostListItem(BaseModel):
    """Schema for host in list responses."""
    
    dn: str
    cn: str
    dhcp_hw_address: Optional[str] = Field(default=None, alias="dhcpHWAddress")
    fixed_address: Optional[str] = Field(default=None, alias="fixedAddress")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.HOST,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Shared Network Schemas
# ============================================================================

class SharedNetworkCreate(DhcpBase):
    """Schema for creating a DHCP shared network."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Shared network name",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate shared network name."""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError("Name must start with alphanumeric and contain only alphanumeric, underscore, or hyphen")
        return v


class SharedNetworkUpdate(DhcpBase):
    """Schema for updating a DHCP shared network."""
    pass


class SharedNetworkRead(DhcpBase):
    """Schema for reading a DHCP shared network."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Shared network name")
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SHARED_NETWORK,
        alias="objectType",
    )


class SharedNetworkListItem(BaseModel):
    """Schema for shared network in list responses."""
    
    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SHARED_NETWORK,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Group Schemas
# ============================================================================

class GroupCreate(DhcpBase):
    """Schema for creating a DHCP group."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Group name",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate group name."""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError("Name must start with alphanumeric and contain only alphanumeric, underscore, or hyphen")
        return v


class GroupUpdate(DhcpBase):
    """Schema for updating a DHCP group."""
    pass


class GroupRead(DhcpBase):
    """Schema for reading a DHCP group."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Group name")
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.GROUP,
        alias="objectType",
    )


class GroupListItem(BaseModel):
    """Schema for group in list responses."""
    
    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.GROUP,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Class Schemas
# ============================================================================

class DhcpClassCreate(DhcpBase):
    """Schema for creating a DHCP class."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Class name",
    )
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v):
        """Validate class name."""
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
            raise ValueError("Name must start with alphanumeric and contain only alphanumeric, underscore, or hyphen")
        return v


class DhcpClassUpdate(DhcpBase):
    """Schema for updating a DHCP class."""
    pass


class DhcpClassRead(DhcpBase):
    """Schema for reading a DHCP class."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Class name")
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.CLASS,
        alias="objectType",
    )


class DhcpClassListItem(BaseModel):
    """Schema for class in list responses."""
    
    dn: str
    cn: str
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.CLASS,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# SubClass Schemas
# ============================================================================

class SubClassCreate(DhcpBase):
    """Schema for creating a DHCP subclass."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Subclass name",
    )
    dhcp_class_data: Optional[str] = Field(
        default=None,
        alias="dhcpClassData",
        description="Class data for client matching",
    )


class SubClassUpdate(DhcpBase):
    """Schema for updating a DHCP subclass."""
    
    dhcp_class_data: Optional[str] = Field(
        default=None,
        alias="dhcpClassData",
    )


class SubClassRead(DhcpBase):
    """Schema for reading a DHCP subclass."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Subclass name")
    dhcp_class_data: Optional[str] = Field(
        default=None,
        alias="dhcpClassData",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.SUBCLASS,
        alias="objectType",
    )


# ============================================================================
# TSIG Key Schemas
# ============================================================================

class TsigKeyCreate(DhcpBase):
    """Schema for creating a TSIG key."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Key name",
    )
    dhcp_key_algorithm: TsigKeyAlgorithm = Field(
        ...,
        alias="dhcpKeyAlgorithm",
        description="TSIG key algorithm",
    )
    dhcp_key_secret: str = Field(
        ...,
        min_length=1,
        alias="dhcpKeySecret",
        description="TSIG key secret (base64 encoded)",
    )


class TsigKeyUpdate(DhcpBase):
    """Schema for updating a TSIG key."""
    
    dhcp_key_algorithm: Optional[TsigKeyAlgorithm] = Field(
        default=None,
        alias="dhcpKeyAlgorithm",
    )
    dhcp_key_secret: Optional[str] = Field(
        default=None,
        alias="dhcpKeySecret",
    )


class TsigKeyRead(DhcpBase):
    """Schema for reading a TSIG key."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Key name")
    dhcp_key_algorithm: TsigKeyAlgorithm = Field(..., alias="dhcpKeyAlgorithm")
    # Secret is not returned for security
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.TSIG_KEY,
        alias="objectType",
    )


class TsigKeyListItem(BaseModel):
    """Schema for TSIG key in list responses."""
    
    dn: str
    cn: str
    dhcp_key_algorithm: TsigKeyAlgorithm = Field(..., alias="dhcpKeyAlgorithm")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.TSIG_KEY,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# DNS Zone Schemas
# ============================================================================

class DnsZoneCreate(DhcpBase):
    """Schema for creating a DNS zone for dynamic updates."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Zone name (FQDN)",
    )
    dhcp_dns_zone_server: str = Field(
        ...,
        alias="dhcpDnsZoneServer",
        description="DNS server for this zone",
    )
    dhcp_key_dn: Optional[str] = Field(
        default=None,
        alias="dhcpKeyDN",
        description="DN of TSIG key for secure updates",
    )


class DnsZoneUpdate(DhcpBase):
    """Schema for updating a DNS zone."""
    
    dhcp_dns_zone_server: Optional[str] = Field(
        default=None,
        alias="dhcpDnsZoneServer",
    )
    dhcp_key_dn: Optional[str] = Field(
        default=None,
        alias="dhcpKeyDN",
    )


class DnsZoneRead(DhcpBase):
    """Schema for reading a DNS zone."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Zone name")
    dhcp_dns_zone_server: str = Field(..., alias="dhcpDnsZoneServer")
    dhcp_key_dn: Optional[str] = Field(
        default=None,
        alias="dhcpKeyDN",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.DNS_ZONE,
        alias="objectType",
    )


class DnsZoneListItem(BaseModel):
    """Schema for DNS zone in list responses."""
    
    dn: str
    cn: str
    dhcp_dns_zone_server: str = Field(..., alias="dhcpDnsZoneServer")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.DNS_ZONE,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Failover Peer Schemas
# ============================================================================

class FailoverPeerCreate(DhcpBase):
    """Schema for creating a failover peer configuration."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Failover peer name",
    )
    dhcp_failover_primary_server: str = Field(
        ...,
        alias="dhcpFailOverPrimaryServer",
        description="Primary server IP or hostname",
    )
    dhcp_failover_secondary_server: str = Field(
        ...,
        alias="dhcpFailOverSecondaryServer",
        description="Secondary server IP or hostname",
    )
    dhcp_failover_primary_port: int = Field(
        ...,
        ge=1,
        le=65535,
        alias="dhcpFailOverPrimaryPort",
        description="Primary server failover port",
    )
    dhcp_failover_secondary_port: int = Field(
        ...,
        ge=1,
        le=65535,
        alias="dhcpFailOverSecondaryPort",
        description="Secondary server failover port",
    )
    dhcp_failover_response_delay: Optional[int] = Field(
        default=None,
        ge=1,
        alias="dhcpFailOverResponseDelay",
        description="Response delay in seconds",
    )
    dhcp_failover_unacked_updates: Optional[int] = Field(
        default=None,
        ge=1,
        alias="dhcpFailOverUnackedUpdates",
        description="Unacked updates count",
    )
    dhcp_max_client_lead_time: Optional[int] = Field(
        default=None,
        ge=1,
        alias="dhcpMaxClientLeadTime",
        description="Max client lead time (MCLT) in seconds",
    )
    dhcp_failover_split: Optional[int] = Field(
        default=None,
        ge=0,
        le=256,
        alias="dhcpFailOverSplit",
        description="Split value (0-256)",
    )
    dhcp_failover_load_balance_time: Optional[int] = Field(
        default=None,
        ge=0,
        alias="dhcpFailOverLoadBalanceTime",
        description="Load balance cutoff time in seconds",
    )


class FailoverPeerUpdate(DhcpBase):
    """Schema for updating a failover peer."""
    
    dhcp_failover_primary_server: Optional[str] = Field(
        default=None,
        alias="dhcpFailOverPrimaryServer",
    )
    dhcp_failover_secondary_server: Optional[str] = Field(
        default=None,
        alias="dhcpFailOverSecondaryServer",
    )
    dhcp_failover_primary_port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        alias="dhcpFailOverPrimaryPort",
    )
    dhcp_failover_secondary_port: Optional[int] = Field(
        default=None,
        ge=1,
        le=65535,
        alias="dhcpFailOverSecondaryPort",
    )
    dhcp_failover_response_delay: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverResponseDelay",
    )
    dhcp_failover_unacked_updates: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverUnackedUpdates",
    )
    dhcp_max_client_lead_time: Optional[int] = Field(
        default=None,
        alias="dhcpMaxClientLeadTime",
    )
    dhcp_failover_split: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverSplit",
    )
    dhcp_failover_load_balance_time: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverLoadBalanceTime",
    )


class FailoverPeerRead(DhcpBase):
    """Schema for reading a failover peer."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Failover peer name")
    dhcp_failover_primary_server: str = Field(..., alias="dhcpFailOverPrimaryServer")
    dhcp_failover_secondary_server: str = Field(..., alias="dhcpFailOverSecondaryServer")
    dhcp_failover_primary_port: int = Field(..., alias="dhcpFailOverPrimaryPort")
    dhcp_failover_secondary_port: int = Field(..., alias="dhcpFailOverSecondaryPort")
    dhcp_failover_response_delay: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverResponseDelay",
    )
    dhcp_failover_unacked_updates: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverUnackedUpdates",
    )
    dhcp_max_client_lead_time: Optional[int] = Field(
        default=None,
        alias="dhcpMaxClientLeadTime",
    )
    dhcp_failover_split: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverSplit",
    )
    dhcp_failover_load_balance_time: Optional[int] = Field(
        default=None,
        alias="dhcpFailOverLoadBalanceTime",
    )
    parent_dn: Optional[str] = Field(
        default=None,
        alias="parentDn",
    )
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.FAILOVER_PEER,
        alias="objectType",
    )


class FailoverPeerListItem(BaseModel):
    """Schema for failover peer in list responses."""
    
    dn: str
    cn: str
    dhcp_failover_primary_server: str = Field(..., alias="dhcpFailOverPrimaryServer")
    dhcp_failover_secondary_server: str = Field(..., alias="dhcpFailOverSecondaryServer")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    object_type: DhcpObjectType = Field(
        default=DhcpObjectType.FAILOVER_PEER,
        alias="objectType",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Tree/Hierarchy Schemas
# ============================================================================

class DhcpTreeNode(BaseModel):
    """Node in the DHCP configuration tree."""
    
    dn: str
    cn: str
    object_type: DhcpObjectType = Field(..., alias="objectType")
    comments: Optional[str] = Field(default=None, alias="dhcpComments")
    children: List["DhcpTreeNode"] = Field(default_factory=list)
    
    model_config = {"populate_by_name": True}


class DhcpTreeResponse(BaseModel):
    """Full DHCP configuration tree response."""
    
    service: DhcpTreeNode


# ============================================================================
# List Response Schemas
# ============================================================================

class DhcpServiceListResponse(BaseModel):
    """Paginated list of DHCP services."""
    
    items: List[DhcpServiceListItem]
    total: int
    page: int = 1
    page_size: int = 50


class SubnetListResponse(BaseModel):
    """Paginated list of subnets."""
    
    items: List[SubnetListItem]
    total: int
    page: int = 1
    page_size: int = 50


class PoolListResponse(BaseModel):
    """Paginated list of pools."""
    
    items: List[PoolListItem]
    total: int
    page: int = 1
    page_size: int = 50


class HostListResponse(BaseModel):
    """Paginated list of hosts."""
    
    items: List[HostListItem]
    total: int
    page: int = 1
    page_size: int = 50


class SharedNetworkListResponse(BaseModel):
    """Paginated list of shared networks."""
    
    items: List[SharedNetworkListItem]
    total: int
    page: int = 1
    page_size: int = 50


class GroupListResponse(BaseModel):
    """Paginated list of groups."""
    
    items: List[GroupListItem]
    total: int
    page: int = 1
    page_size: int = 50


class DhcpClassListResponse(BaseModel):
    """Paginated list of classes."""
    
    items: List[DhcpClassListItem]
    total: int
    page: int = 1
    page_size: int = 50


class TsigKeyListResponse(BaseModel):
    """Paginated list of TSIG keys."""
    
    items: List[TsigKeyListItem]
    total: int
    page: int = 1
    page_size: int = 50


class DnsZoneListResponse(BaseModel):
    """Paginated list of DNS zones."""
    
    items: List[DnsZoneListItem]
    total: int
    page: int = 1
    page_size: int = 50


class FailoverPeerListResponse(BaseModel):
    """Paginated list of failover peers."""
    
    items: List[FailoverPeerListItem]
    total: int
    page: int = 1
    page_size: int = 50


# ============================================================================
# Generic DHCP Object Schemas
# ============================================================================

class DhcpObjectCreate(BaseModel):
    """Generic schema for creating any DHCP object."""
    
    cn: str
    object_type: DhcpObjectType = Field(..., alias="objectType")
    parent_dn: str = Field(..., alias="parentDn")
    attributes: dict = Field(default_factory=dict)
    
    model_config = {"populate_by_name": True}


class DhcpObjectRead(BaseModel):
    """Generic schema for reading any DHCP object."""
    
    dn: str
    cn: str
    object_type: DhcpObjectType = Field(..., alias="objectType")
    parent_dn: Optional[str] = Field(default=None, alias="parentDn")
    attributes: dict = Field(default_factory=dict)
    
    model_config = {"populate_by_name": True}
