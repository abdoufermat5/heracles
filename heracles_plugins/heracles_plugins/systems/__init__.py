"""
Systems Plugin
==============

Provides system/device management for LDAP-based infrastructure.

Manages the following LDAP objectClasses:
- hrcServer: Server systems
- hrcWorkstation: Workstation systems
- hrcTerminal: Terminal systems
- hrcPrinter: Printer devices
- device: Network components (standard objectClass)
- hrcPhone: Phone devices
- hrcMobilePhone: Mobile phone devices

Common Attributes:
- cn: System hostname (required)
- description: System description
- ipHostNumber: IP addresses (via ipHost objectClass)
- macAddress: MAC addresses (via ieee802Device objectClass)
- hrcMode: Lock mode (active, locked, maintenance)
- l: Location

Printer-specific:
- labeledURI: Printer URI
- hrcWindowsInf, hrcWindowsDriver*: Windows driver configuration

Phone-specific:
- telephoneNumber: Phone number/extension
- serialNumber: Device serial number

Mobile-specific:
- hrcImei: IMEI number
- hrcOperatingSystem: OS type
- hrcPuk: PUK code
"""

from .plugin import SystemsPlugin

__plugin__ = SystemsPlugin

__all__ = ["SystemsPlugin", "__plugin__"]
