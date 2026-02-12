"""
SSH Plugin Schemas
==================

Pydantic models for SSH key management.
"""

import hashlib
import base64
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime


# ============================================================================
# SSH Key Types
# ============================================================================

SSH_KEY_TYPES = [
    "ssh-rsa",
    "ssh-dss",
    "ssh-ed25519",
    "ecdsa-sha2-nistp256",
    "ecdsa-sha2-nistp384",
    "ecdsa-sha2-nistp521",
    "sk-ssh-ed25519@openssh.com",
    "sk-ecdsa-sha2-nistp256@openssh.com",
]


# ============================================================================
# SSH Key Schemas
# ============================================================================

class SSHKeyBase(BaseModel):
    """Base SSH key attributes."""
    
    key: str = Field(
        ...,
        min_length=20,
        description="Full SSH public key (type + key + optional comment)",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional comment/label for this key",
    )
    
    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, v: str) -> str:
        """Normalize SSH key (strip whitespace, validate format)."""
        if not v:
            raise ValueError("SSH key cannot be empty")
        
        # Strip and normalize whitespace
        v = " ".join(v.strip().split())
        
        return v
    
    @model_validator(mode="after")
    def validate_ssh_key_format(self):
        """Validate SSH public key format."""
        parts = self.key.split()
        
        if len(parts) < 2:
            raise ValueError("Invalid SSH key format: must have at least type and key")
        
        key_type = parts[0]
        key_data = parts[1]
        
        # Validate key type
        if key_type not in SSH_KEY_TYPES:
            raise ValueError(f"Unknown SSH key type: {key_type}. Supported: {', '.join(SSH_KEY_TYPES)}")
        
        # Validate base64 encoding
        try:
            decoded = base64.b64decode(key_data)
            if len(decoded) < 10:
                raise ValueError("SSH key data too short")
        except Exception:
            raise ValueError("Invalid SSH key: key data is not valid base64")
        
        # Extract comment from key if present and not already set
        if len(parts) >= 3 and not self.comment:
            self.comment = " ".join(parts[2:])
        
        return self


class SSHKeyCreate(SSHKeyBase):
    """Schema for adding an SSH key."""
    pass


class SSHKeyRead(BaseModel):
    """Schema for reading an SSH key."""
    
    key: str = Field(..., description="Full SSH public key")
    key_type: str = Field(..., alias="keyType", description="SSH key type (ssh-rsa, ssh-ed25519, etc.)")
    fingerprint: str = Field(..., description="SHA256 fingerprint of the key")
    comment: Optional[str] = Field(default=None, description="Key comment/label")
    bits: Optional[int] = Field(default=None, description="Key size in bits (for RSA/DSA)")
    added_at: Optional[datetime] = Field(default=None, alias="addedAt", description="When the key was added")
    
    class Config:
        populate_by_name = True


class SSHKeyUpdate(BaseModel):
    """Schema for updating an SSH key (only comment can be changed)."""
    
    comment: Optional[str] = Field(
        default=None,
        max_length=255,
        description="New comment/label for this key",
    )


class SSHKeyDelete(BaseModel):
    """Schema for deleting an SSH key."""
    
    fingerprint: str = Field(
        ...,
        description="SHA256 fingerprint of the key to delete",
    )


# ============================================================================
# User SSH Status
# ============================================================================

class UserSSHStatus(BaseModel):
    """SSH status for a user."""
    
    uid: str = Field(..., description="User ID")
    dn: str = Field(..., description="User DN")
    has_ssh: bool = Field(..., alias="hasSsh", description="Whether user has ldapPublicKey objectClass")
    keys: List[SSHKeyRead] = Field(default_factory=list, description="List of SSH public keys")
    key_count: int = Field(default=0, alias="keyCount", description="Number of SSH keys")
    
    class Config:
        populate_by_name = True


class UserSSHActivate(BaseModel):
    """Schema for activating SSH on a user account."""
    
    initial_key: Optional[str] = Field(
        default=None,
        alias="initialKey",
        description="Optional initial SSH public key to add",
    )
    
    class Config:
        populate_by_name = True


class UserSSHKeysUpdate(BaseModel):
    """Schema for bulk updating SSH keys."""
    
    keys: List[str] = Field(
        ...,
        description="Complete list of SSH public keys (replaces existing)",
    )
    
    @field_validator("keys", mode="before")
    @classmethod
    def validate_keys(cls, v):
        """Validate all keys."""
        if v is None:
            return []
        
        validated = []
        for key in v:
            key = " ".join(key.strip().split())
            if not key:
                continue
            
            parts = key.split()
            if len(parts) < 2:
                raise ValueError(f"Invalid SSH key format: {key[:50]}...")
            
            if parts[0] not in SSH_KEY_TYPES:
                raise ValueError(f"Unknown SSH key type: {parts[0]}")
            
            validated.append(key)
        
        return validated


# ============================================================================
# Helper Functions
# ============================================================================

def compute_fingerprint(key: str) -> str:
    """
    Compute SHA256 fingerprint of an SSH public key.
    
    Returns fingerprint in format: SHA256:base64hash
    """
    parts = key.split()
    if len(parts) < 2:
        raise ValueError("Invalid SSH key format")
    
    key_data = parts[1]
    
    try:
        decoded = base64.b64decode(key_data)
    except Exception:
        raise ValueError("Invalid SSH key: cannot decode base64")
    
    # Compute SHA256
    sha256_hash = hashlib.sha256(decoded).digest()
    fingerprint = base64.b64encode(sha256_hash).decode("ascii").rstrip("=")
    
    return f"SHA256:{fingerprint}"


def parse_ssh_key(key: str) -> dict:
    """
    Parse an SSH public key and extract metadata.
    
    Returns dict with: key_type, key_data, comment, fingerprint, bits
    """
    parts = key.split()
    
    if len(parts) < 2:
        raise ValueError("Invalid SSH key format")
    
    key_type = parts[0]
    key_data = parts[1]
    comment = " ".join(parts[2:]) if len(parts) > 2 else None
    
    # Decode to get size
    try:
        decoded = base64.b64decode(key_data)
    except Exception:
        raise ValueError("Invalid SSH key: cannot decode base64")
    
    # Compute fingerprint
    sha256_hash = hashlib.sha256(decoded).digest()
    fingerprint = f"SHA256:{base64.b64encode(sha256_hash).decode('ascii').rstrip('=')}"
    
    # Estimate key bits (rough approximation)
    bits = None
    if key_type == "ssh-rsa":
        # RSA key size is roughly (decoded_length - header) * 8
        bits = (len(decoded) - 20) * 8 // 2
        # Round to common sizes
        if bits > 3500:
            bits = 4096
        elif bits > 1900:
            bits = 2048
        elif bits > 900:
            bits = 1024
    elif key_type == "ssh-dss":
        bits = 1024
    elif key_type == "ssh-ed25519":
        bits = 256
    elif "nistp256" in key_type:
        bits = 256
    elif "nistp384" in key_type:
        bits = 384
    elif "nistp521" in key_type:
        bits = 521
    
    return {
        "key": key,
        "key_type": key_type,
        "key_data": key_data,
        "comment": comment,
        "fingerprint": fingerprint,
        "bits": bits,
    }


def validate_ssh_key(key: str) -> bool:
    """
    Validate an SSH public key.
    
    Returns True if valid, raises ValueError if invalid.
    """
    try:
        parse_ssh_key(key)
        return True
    except ValueError:
        return False
