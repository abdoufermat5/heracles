"""
DNS Service Constants
=====================

Attribute definitions and mappings for DNS objects.
"""



# Default DNS container RDN
DNS_BASE_RDN = "ou=dns"

# Object classes for DNS zone entries
OBJECT_CLASSES = ["dNSZone"]

# Default DNS class
DNS_CLASS = "IN"

# All DNS-related attributes we manage
MANAGED_ATTRIBUTES = [
    "zoneName",
    "relativeDomainName",
    "dNSTTL",
    "dNSClass",
    "sOARecord",
    "aRecord",
    "aAAARecord",
    "mXRecord",
    "nSRecord",
    "cNAMERecord",
    "pTRRecord",
    "tXTRecord",
    "sRVRecord",
]
