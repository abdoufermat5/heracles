"""
Systems Plugin Schemas
======================

Pydantic models for system data validation.

System Types:
    - server: Physical or virtual servers
    - workstation: User workstations
    - terminal: Thin clients/terminals
    - printer: Network printers
    - component: Network devices (switches, routers, etc.)
    - phone: IP phones
    - mobile: Mobile phones

All types support:
    - cn (common name) - required
    - description - optional
    - ipHostNumber - IP addresses (multi-valued)
    - macAddress - MAC addresses (multi-valued)
    - l (location) - optional
    - hrcMode - lock mode ("locked"/"unlocked")
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
import re


# ============================================================================
# Enums
# ============================================================================

class SystemType(str, Enum):
    """System types supported by the plugin."""
    
    SERVER = "server"
    WORKSTATION = "workstation"
    TERMINAL = "terminal"
    PRINTER = "printer"
    COMPONENT = "component"
    PHONE = "phone"
    MOBILE = "mobile"
    
    @classmethod
    def get_object_class(cls, system_type: "SystemType") -> str:
        """Get the LDAP objectClass for a system type."""
        mapping = {
            cls.SERVER: "hrcServer",
            cls.WORKSTATION: "hrcWorkstation",
            cls.TERMINAL: "hrcTerminal",
            cls.PRINTER: "hrcPrinter",
            cls.COMPONENT: "device",
            cls.PHONE: "hrcPhone",
            cls.MOBILE: "hrcMobilePhone",
        }
        return mapping[system_type]
    
    @classmethod
    def get_rdn(cls, system_type: "SystemType") -> str:
        """Get the relative DN (OU) for a system type."""
        mapping = {
            cls.SERVER: "ou=servers",
            cls.WORKSTATION: "ou=workstations",
            cls.TERMINAL: "ou=terminals",
            cls.PRINTER: "ou=printers",
            cls.COMPONENT: "ou=components",
            cls.PHONE: "ou=phones",
            cls.MOBILE: "ou=mobile",
        }
        return mapping[system_type]
    
    @classmethod
    def from_object_class(cls, object_class: str) -> Optional["SystemType"]:
        """Get the SystemType from an LDAP objectClass."""
        mapping = {
            "hrcServer": cls.SERVER,
            "hrcWorkstation": cls.WORKSTATION,
            "hrcTerminal": cls.TERMINAL,
            "hrcPrinter": cls.PRINTER,
            "device": cls.COMPONENT,
            "hrcPhone": cls.PHONE,
            "hrcMobilePhone": cls.MOBILE,
        }
        return mapping.get(object_class)


class LockMode(str, Enum):
    """System lock mode."""
    
    LOCKED = "locked"
    UNLOCKED = "unlocked"


# ============================================================================
# Base Schemas
# ============================================================================

class SystemBase(BaseModel):
    """Base attributes for all system types."""
    
    description: Optional[str] = Field(
        default=None,
        max_length=1024,
        description="Description of this system",
    )
    ip_addresses: List[str] = Field(
        default_factory=list,
        alias="ipHostNumber",
        description="IP addresses (multi-valued)",
    )
    mac_addresses: List[str] = Field(
        default_factory=list,
        alias="macAddress",
        description="MAC addresses (multi-valued)",
    )
    location: Optional[str] = Field(
        default=None,
        alias="l",
        max_length=256,
        description="Physical location",
    )
    mode: Optional[LockMode] = Field(
        default=None,
        alias="hrcMode",
        description="Lock mode (locked/unlocked)",
    )
    
    @field_validator("ip_addresses", mode="before")
    @classmethod
    def validate_ip_addresses(cls, v):
        """Validate and normalize IP addresses."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        
        validated = []
        for ip in v:
            ip = ip.strip()
            if not ip:
                continue
            
            # Basic IPv4 validation
            ipv4_pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
            # Basic IPv6 validation (simplified)
            ipv6_pattern = r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$"
            
            if re.match(ipv4_pattern, ip):
                # Validate each octet
                octets = ip.split(".")
                if all(0 <= int(o) <= 255 for o in octets):
                    validated.append(ip)
                else:
                    raise ValueError(f"Invalid IPv4 address: {ip}")
            elif re.match(ipv6_pattern, ip) or "::" in ip:
                validated.append(ip)
            else:
                raise ValueError(f"Invalid IP address format: {ip}")
        
        return validated
    
    @field_validator("mac_addresses", mode="before")
    @classmethod
    def validate_mac_addresses(cls, v):
        """Validate and normalize MAC addresses."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        
        validated = []
        for mac in v:
            mac = mac.strip().upper()
            if not mac:
                continue
            
            # Normalize to colon-separated format
            # Accept: 00:11:22:33:44:55, 00-11-22-33-44-55, 001122334455
            mac_clean = re.sub(r"[:-]", "", mac)
            
            if not re.match(r"^[0-9A-F]{12}$", mac_clean):
                raise ValueError(f"Invalid MAC address format: {mac}")
            
            # Format as colon-separated
            mac_formatted = ":".join(
                mac_clean[i:i+2] for i in range(0, 12, 2)
            )
            validated.append(mac_formatted)
        
        return validated
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Printer-Specific Fields
# ============================================================================

class PrinterFields(BaseModel):
    """Additional fields for printers."""
    
    labeled_uri: Optional[str] = Field(
        default=None,
        alias="labeledURI",
        description="Printer URI (e.g., ipp://printer.example.com/printers/printer1)",
    )
    windows_inf_file: Optional[str] = Field(
        default=None,
        alias="hrcPrinterWindowsInfFile",
        description="Path to Windows INF file",
    )
    windows_driver_dir: Optional[str] = Field(
        default=None,
        alias="hrcPrinterWindowsDriverDir",
        description="Path to Windows driver directory",
    )
    windows_driver_name: Optional[str] = Field(
        default=None,
        alias="hrcPrinterWindowsDriverName",
        description="Windows driver name",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Phone-Specific Fields
# ============================================================================

class PhoneFields(BaseModel):
    """Additional fields for phones."""
    
    telephone_number: Optional[str] = Field(
        default=None,
        alias="telephoneNumber",
        description="Telephone number",
    )
    serial_number: Optional[str] = Field(
        default=None,
        alias="serialNumber",
        description="Device serial number",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Mobile-Specific Fields
# ============================================================================

class MobileFields(PhoneFields):
    """Additional fields for mobile phones."""
    
    imei: Optional[str] = Field(
        default=None,
        alias="hrcMobileIMEI",
        description="IMEI number",
    )
    operating_system: Optional[str] = Field(
        default=None,
        alias="hrcMobileOS",
        description="Mobile operating system",
    )
    puk: Optional[str] = Field(
        default=None,
        alias="hrcMobilePUK",
        description="PUK code",
    )
    
    @field_validator("imei")
    @classmethod
    def validate_imei(cls, v):
        """Validate IMEI format (15 digits)."""
        if v is None:
            return None
        v = v.strip()
        if not re.match(r"^\d{15}$", v):
            raise ValueError("IMEI must be exactly 15 digits")
        return v
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Component-Specific Fields
# ============================================================================

class ComponentFields(BaseModel):
    """Additional fields for components (uses standard 'device' objectClass)."""
    
    serial_number: Optional[str] = Field(
        default=None,
        alias="serialNumber",
        description="Device serial number",
    )
    owner: Optional[str] = Field(
        default=None,
        alias="owner",
        description="DN of the device owner",
    )
    
    model_config = {"populate_by_name": True}


# ============================================================================
# Create Schema
# ============================================================================

class SystemCreate(SystemBase):
    """Schema for creating a new system."""
    
    cn: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Common name (system identifier/hostname)",
    )
    system_type: SystemType = Field(
        ...,
        alias="systemType",
        description="Type of system to create",
    )
    
    # Optional type-specific fields
    # Printer
    labeled_uri: Optional[str] = Field(default=None, alias="labeledURI")
    windows_inf_file: Optional[str] = Field(default=None, alias="hrcPrinterWindowsInfFile")
    windows_driver_dir: Optional[str] = Field(default=None, alias="hrcPrinterWindowsDriverDir")
    windows_driver_name: Optional[str] = Field(default=None, alias="hrcPrinterWindowsDriverName")
    
    # Phone/Mobile
    telephone_number: Optional[str] = Field(default=None, alias="telephoneNumber")
    serial_number: Optional[str] = Field(default=None, alias="serialNumber")
    
    # Mobile only
    imei: Optional[str] = Field(default=None, alias="hrcMobileIMEI")
    operating_system: Optional[str] = Field(default=None, alias="hrcMobileOS")
    puk: Optional[str] = Field(default=None, alias="hrcMobilePUK")
    
    # Component only
    owner: Optional[str] = Field(default=None, alias="owner")
    
    @field_validator("cn")
    @classmethod
    def validate_cn(cls, v: str) -> str:
        """Validate CN format (hostname-like)."""
        v = v.strip()
        # Allow hostnames: letters, numbers, hyphens (not at start/end)
        if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", v):
            raise ValueError(
                "CN must be a valid hostname (alphanumeric, hyphens allowed but not at start/end)"
            )
        return v.lower()  # Normalize to lowercase
    
    @field_validator("imei")
    @classmethod
    def validate_imei(cls, v):
        """Validate IMEI format (15 digits)."""
        if v is None:
            return None
        v = v.strip()
        if not re.match(r"^\d{15}$", v):
            raise ValueError("IMEI must be exactly 15 digits")
        return v


# ============================================================================
# Read Schema
# ============================================================================

class SystemRead(SystemBase):
    """Schema for reading a system."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Common name (hostname)")
    system_type: SystemType = Field(..., alias="systemType", description="System type")
    
    # Type-specific fields
    labeled_uri: Optional[str] = Field(default=None, alias="labeledURI")
    windows_inf_file: Optional[str] = Field(default=None, alias="hrcPrinterWindowsInfFile")
    windows_driver_dir: Optional[str] = Field(default=None, alias="hrcPrinterWindowsDriverDir")
    windows_driver_name: Optional[str] = Field(default=None, alias="hrcPrinterWindowsDriverName")
    telephone_number: Optional[str] = Field(default=None, alias="telephoneNumber")
    serial_number: Optional[str] = Field(default=None, alias="serialNumber")
    imei: Optional[str] = Field(default=None, alias="hrcMobileIMEI")
    operating_system: Optional[str] = Field(default=None, alias="hrcMobileOS")
    puk: Optional[str] = Field(default=None, alias="hrcMobilePUK")
    owner: Optional[str] = Field(default=None, alias="owner")


# ============================================================================
# Update Schema
# ============================================================================

class SystemUpdate(BaseModel):
    """Schema for updating a system."""
    
    description: Optional[str] = Field(default=None)
    ip_addresses: Optional[List[str]] = Field(default=None, alias="ipHostNumber")
    mac_addresses: Optional[List[str]] = Field(default=None, alias="macAddress")
    location: Optional[str] = Field(default=None, alias="l")
    mode: Optional[LockMode] = Field(default=None, alias="hrcMode")
    
    # Type-specific fields (applied based on system type)
    labeled_uri: Optional[str] = Field(default=None, alias="labeledURI")
    windows_inf_file: Optional[str] = Field(default=None, alias="hrcPrinterWindowsInfFile")
    windows_driver_dir: Optional[str] = Field(default=None, alias="hrcPrinterWindowsDriverDir")
    windows_driver_name: Optional[str] = Field(default=None, alias="hrcPrinterWindowsDriverName")
    telephone_number: Optional[str] = Field(default=None, alias="telephoneNumber")
    serial_number: Optional[str] = Field(default=None, alias="serialNumber")
    imei: Optional[str] = Field(default=None, alias="hrcMobileIMEI")
    operating_system: Optional[str] = Field(default=None, alias="hrcMobileOS")
    puk: Optional[str] = Field(default=None, alias="hrcMobilePUK")
    owner: Optional[str] = Field(default=None, alias="owner")
    
    @field_validator("ip_addresses", mode="before")
    @classmethod
    def validate_ip_addresses(cls, v):
        """Validate IP addresses (same as base)."""
        if v is None:
            return None
        return SystemBase.validate_ip_addresses(v)
    
    @field_validator("mac_addresses", mode="before")
    @classmethod
    def validate_mac_addresses(cls, v):
        """Validate MAC addresses (same as base)."""
        if v is None:
            return None
        return SystemBase.validate_mac_addresses(v)
    
    @field_validator("imei")
    @classmethod
    def validate_imei(cls, v):
        """Validate IMEI format."""
        if v is None:
            return None
        v = v.strip()
        if v and not re.match(r"^\d{15}$", v):
            raise ValueError("IMEI must be exactly 15 digits")
        return v
    
    model_config = {"populate_by_name": True}


# ============================================================================
# List Response Schemas
# ============================================================================

class SystemListItem(BaseModel):
    """Summary of a system for list views."""
    
    dn: str = Field(..., description="Distinguished Name")
    cn: str = Field(..., description="Common name (hostname)")
    system_type: SystemType = Field(..., alias="systemType", description="System type")
    description: Optional[str] = Field(default=None)
    ip_addresses: List[str] = Field(default_factory=list, alias="ipHostNumber")
    mac_addresses: List[str] = Field(default_factory=list, alias="macAddress")
    location: Optional[str] = Field(default=None, alias="l")
    mode: Optional[LockMode] = Field(default=None, alias="hrcMode")
    
    model_config = {"populate_by_name": True}


class SystemListResponse(BaseModel):
    """Response for listing systems."""
    
    systems: List[SystemListItem]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


# ============================================================================
# Host Validation Schemas (for other plugins)
# ============================================================================

class HostValidationRequest(BaseModel):
    """Request to validate host names against registered systems."""
    
    hostnames: List[str] = Field(..., description="List of hostnames to validate")


class HostValidationResponse(BaseModel):
    """Response from host validation."""
    
    valid_hosts: List[str] = Field(..., alias="validHosts", description="Hosts that exist in systems")
    invalid_hosts: List[str] = Field(..., alias="invalidHosts", description="Hosts that don't exist")
    
    model_config = {"populate_by_name": True}
