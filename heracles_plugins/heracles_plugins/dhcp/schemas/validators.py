"""
DHCP Validators
===============

Validation functions for DHCP data.
"""

import re


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


def validate_cn_alphanumeric(v: str) -> str:
    """Validate that cn starts with alphanumeric and contains only valid chars."""
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", v):
        raise ValueError(
            "Name must start with alphanumeric and contain only "
            "alphanumeric, underscore, or hyphen"
        )
    return v
