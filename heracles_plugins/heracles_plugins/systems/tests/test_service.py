"""
Tests - Systems Plugin
======================

Unit tests for the systems plugin schemas, service, and routes.
"""

import pytest
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

# Import schemas
from heracles_plugins.systems.schemas import (
    SystemType,
    SystemCreate,
    SystemRead,
    SystemUpdate,
    SystemListItem,
    SystemListResponse,
    LockMode,
    HostValidationRequest,
    HostValidationResponse,
)


# ============================================================================
# Schema Tests
# ============================================================================

class TestSystemType:
    """Tests for SystemType enum."""
    
    def test_all_types_exist(self):
        """Verify all expected system types are defined."""
        expected_types = ["server", "workstation", "terminal", "printer", "component", "phone", "mobile"]
        for type_name in expected_types:
            assert SystemType(type_name) is not None
    
    def test_get_object_class(self):
        """Test objectClass mapping."""
        assert SystemType.get_object_class(SystemType.SERVER) == "hrcServer"
        assert SystemType.get_object_class(SystemType.WORKSTATION) == "hrcWorkstation"
        assert SystemType.get_object_class(SystemType.TERMINAL) == "hrcTerminal"
        assert SystemType.get_object_class(SystemType.PRINTER) == "hrcPrinter"
        assert SystemType.get_object_class(SystemType.COMPONENT) == "device"
        assert SystemType.get_object_class(SystemType.PHONE) == "hrcPhone"
        assert SystemType.get_object_class(SystemType.MOBILE) == "hrcMobilePhone"
    
    def test_get_rdn(self):
        """Test RDN mapping."""
        assert SystemType.get_rdn(SystemType.SERVER) == "ou=servers"
        assert SystemType.get_rdn(SystemType.WORKSTATION) == "ou=workstations"
        assert SystemType.get_rdn(SystemType.TERMINAL) == "ou=terminals"
        assert SystemType.get_rdn(SystemType.PRINTER) == "ou=printers"
        assert SystemType.get_rdn(SystemType.COMPONENT) == "ou=components"
        assert SystemType.get_rdn(SystemType.PHONE) == "ou=phones"
        assert SystemType.get_rdn(SystemType.MOBILE) == "ou=mobile"
    
    def test_from_object_class(self):
        """Test reverse mapping from objectClass."""
        assert SystemType.from_object_class("hrcServer") == SystemType.SERVER
        assert SystemType.from_object_class("hrcWorkstation") == SystemType.WORKSTATION
        assert SystemType.from_object_class("device") == SystemType.COMPONENT
        assert SystemType.from_object_class("unknown") is None


class TestSystemCreate:
    """Tests for SystemCreate schema."""
    
    def test_valid_server_create(self):
        """Test creating a valid server."""
        data = SystemCreate(
            cn="srv-web-01",
            system_type=SystemType.SERVER,
            description="Web server",
            ip_addresses=["192.168.1.10"],
            mac_addresses=["00:11:22:33:44:55"],
            location="Data Center A",
        )
        assert data.cn == "srv-web-01"
        assert data.system_type == SystemType.SERVER
        assert data.ip_addresses == ["192.168.1.10"]
    
    def test_valid_workstation_create(self):
        """Test creating a valid workstation."""
        data = SystemCreate(
            cn="ws-dev-001",
            system_type=SystemType.WORKSTATION,
        )
        assert data.cn == "ws-dev-001"
        assert data.system_type == SystemType.WORKSTATION
        assert data.ip_addresses == []
    
    def test_valid_printer_create(self):
        """Test creating a valid printer with printer-specific fields."""
        data = SystemCreate(
            cn="print-floor1",
            system_type=SystemType.PRINTER,
            labeled_uri="ipp://print.example.com/printers/floor1",
            windows_driver_name="HP LaserJet",
        )
        assert data.cn == "print-floor1"
        assert data.system_type == SystemType.PRINTER
        assert data.labeled_uri == "ipp://print.example.com/printers/floor1"
    
    def test_valid_mobile_create(self):
        """Test creating a valid mobile phone."""
        data = SystemCreate(
            cn="mobile-001",
            system_type=SystemType.MOBILE,
            telephone_number="+1234567890",
            imei="123456789012345",
            operating_system="iOS 17",
        )
        assert data.cn == "mobile-001"
        assert data.imei == "123456789012345"
        assert data.operating_system == "iOS 17"
    
    def test_cn_validation_valid(self):
        """Test valid CN formats."""
        valid_cns = ["server1", "srv-web-01", "ws001", "A1B2C3"]
        for cn in valid_cns:
            data = SystemCreate(cn=cn, system_type=SystemType.SERVER)
            assert data.cn == cn.lower()  # Normalized to lowercase
    
    def test_cn_validation_invalid(self):
        """Test invalid CN formats."""
        invalid_cns = ["-invalid", "invalid-", "_invalid", "inv@lid", "inv alid"]
        for cn in invalid_cns:
            with pytest.raises(ValueError):
                SystemCreate(cn=cn, system_type=SystemType.SERVER)
    
    def test_ip_address_validation(self):
        """Test IP address validation."""
        # Valid IPv4
        data = SystemCreate(
            cn="server1",
            system_type=SystemType.SERVER,
            ip_addresses=["192.168.1.1", "10.0.0.1"],
        )
        assert len(data.ip_addresses) == 2
        
        # Invalid IPv4
        with pytest.raises(ValueError):
            SystemCreate(
                cn="server1",
                system_type=SystemType.SERVER,
                ip_addresses=["300.168.1.1"],
            )
    
    def test_mac_address_validation(self):
        """Test MAC address validation and normalization."""
        # Various valid formats
        data = SystemCreate(
            cn="server1",
            system_type=SystemType.SERVER,
            mac_addresses=["00:11:22:33:44:55", "AA-BB-CC-DD-EE-FF", "aabbccddeeff"],
        )
        # All should be normalized to uppercase colon format
        assert data.mac_addresses == ["00:11:22:33:44:55", "AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"]
        
        # Invalid MAC
        with pytest.raises(ValueError):
            SystemCreate(
                cn="server1",
                system_type=SystemType.SERVER,
                mac_addresses=["invalid-mac"],
            )
    
    def test_imei_validation(self):
        """Test IMEI validation."""
        # Valid IMEI (15 digits)
        data = SystemCreate(
            cn="mobile1",
            system_type=SystemType.MOBILE,
            imei="123456789012345",
        )
        assert data.imei == "123456789012345"
        
        # Invalid IMEI (wrong length)
        with pytest.raises(ValueError):
            SystemCreate(
                cn="mobile1",
                system_type=SystemType.MOBILE,
                imei="12345",
            )


class TestSystemUpdate:
    """Tests for SystemUpdate schema."""
    
    def test_partial_update(self):
        """Test partial update only changes specified fields."""
        data = SystemUpdate(description="New description")
        assert data.description == "New description"
        assert data.ip_addresses is None
        assert data.mac_addresses is None
    
    def test_update_mode(self):
        """Test updating lock mode."""
        data = SystemUpdate(mode=LockMode.LOCKED)
        assert data.mode == LockMode.LOCKED
    
    def test_update_ip_addresses(self):
        """Test updating IP addresses."""
        data = SystemUpdate(ip_addresses=["10.0.0.1", "10.0.0.2"])
        assert data.ip_addresses == ["10.0.0.1", "10.0.0.2"]


class TestSystemRead:
    """Tests for SystemRead schema."""
    
    def test_read_schema(self):
        """Test reading a system."""
        data = SystemRead(
            dn="cn=srv-01,ou=servers,ou=systems,dc=example,dc=com",
            cn="srv-01",
            system_type=SystemType.SERVER,
            description="Test server",
            ip_addresses=["192.168.1.10"],
            mac_addresses=["00:11:22:33:44:55"],
        )
        assert data.dn.startswith("cn=srv-01")
        assert data.system_type == SystemType.SERVER


class TestHostValidation:
    """Tests for host validation schemas."""
    
    def test_validation_request(self):
        """Test host validation request."""
        data = HostValidationRequest(hostnames=["srv-01", "srv-02", "srv-03"])
        assert len(data.hostnames) == 3
    
    def test_validation_response(self):
        """Test host validation response."""
        data = HostValidationResponse(
            valid_hosts=["srv-01", "srv-02"],
            invalid_hosts=["unknown-host"],
        )
        assert len(data.valid_hosts) == 2
        assert len(data.invalid_hosts) == 1


# ============================================================================
# Service Tests (with mocked LDAP)
# ============================================================================

class TestSystemServiceUnit:
    """Unit tests for SystemService with mocked dependencies."""
    
    @pytest.fixture
    def mock_ldap_service(self):
        """Create a mock LDAP service."""
        mock = MagicMock()
        mock.base_dn = "dc=example,dc=com"
        mock._escape_filter = lambda x: x  # Simple pass-through
        return mock
    
    @pytest.fixture
    def config(self):
        """Service configuration."""
        return {
            "systems_rdn": "ou=systems",
            "base_dn": "dc=example,dc=com",
        }
    
    @pytest.fixture
    def service(self, mock_ldap_service, config):
        """Create SystemService with mocked dependencies."""
        from heracles_plugins.systems.service import SystemService
        return SystemService(mock_ldap_service, config)
    
    @pytest.mark.asyncio
    async def test_create_server(self, service, mock_ldap_service):
        """Test creating a server."""
        # Mock entry for the created server
        mock_entry = MagicMock()
        mock_entry.dn = "cn=srv-01,ou=servers,ou=systems,dc=example,dc=com"
        mock_entry.get = lambda attr, default=[]: {
            "cn": ["srv-01"],
            "objectClass": ["hrcServer", "ipHost", "ieee802Device"],
            "description": ["Test server"],
        }.get(attr, default)
        mock_entry.get_first = lambda attr, default=None: {
            "cn": "srv-01",
            "description": "Test server",
        }.get(attr, default)
        
        # get_by_dn returns:
        # 1. None for checking systems OU exists (triggers creation)
        # 2. None for checking type OU exists (triggers creation)
        # 3. None for checking if system already exists
        # 4. Entry for reading back after create
        mock_ldap_service.get_by_dn = AsyncMock(side_effect=[None, None, None, mock_entry])
        mock_ldap_service.add = AsyncMock()
        mock_ldap_service.search = AsyncMock(return_value=[])
        
        data = SystemCreate(
            cn="srv-01",
            system_type=SystemType.SERVER,
            description="Test server",
        )
        
        result = await service.create_system(data)
        
        # Verify add was called (for OUs and system entry)
        assert mock_ldap_service.add.call_count >= 1
    
    @pytest.mark.asyncio
    async def test_validate_hosts_all_valid(self, service, mock_ldap_service):
        """Test validating hosts when all exist."""
        # Mock search to return matching entries
        mock_entry1 = MagicMock()
        mock_entry1.get_first = lambda attr: "srv-01" if attr == "cn" else None
        
        mock_entry2 = MagicMock()
        mock_entry2.get_first = lambda attr: "srv-02" if attr == "cn" else None
        
        mock_ldap_service.search = AsyncMock(return_value=[mock_entry1, mock_entry2])
        
        result = await service.validate_hosts(["srv-01", "srv-02"])
        
        assert "srv-01" in result.valid_hosts
        assert "srv-02" in result.valid_hosts
        assert len(result.invalid_hosts) == 0
    
    @pytest.mark.asyncio
    async def test_validate_hosts_some_invalid(self, service, mock_ldap_service):
        """Test validating hosts when some don't exist."""
        mock_entry = MagicMock()
        mock_entry.get_first = lambda attr: "srv-01" if attr == "cn" else None
        
        mock_ldap_service.search = AsyncMock(return_value=[mock_entry])
        
        result = await service.validate_hosts(["srv-01", "unknown-host"])
        
        assert "srv-01" in result.valid_hosts
        assert "unknown-host" in result.invalid_hosts
    
    @pytest.mark.asyncio
    async def test_validate_hosts_empty_list(self, service, mock_ldap_service):
        """Test validating empty host list."""
        result = await service.validate_hosts([])
        
        assert result.valid_hosts == []
        assert result.invalid_hosts == []
        mock_ldap_service.search.assert_not_called()


# ============================================================================
# E2E Tests (require running infrastructure)
# ============================================================================

@pytest.mark.skipif(
    True,  # Change to check RUN_E2E_TESTS env var
    reason="E2E tests require running infrastructure"
)
class TestSystemsE2E:
    """End-to-end tests for systems plugin."""
    
    pass  # E2E tests would go here


# ============================================================================
# Integration Tests  
# ============================================================================

class TestPosixHostValidationIntegration:
    """Test POSIX plugin integration with systems plugin for host validation."""
    
    @pytest.mark.asyncio
    async def test_posix_group_validates_hosts(self):
        """Test that POSIX group creation validates hosts via systems plugin."""
        # This is a conceptual test showing how the integration works
        # In real integration tests, you'd mock the plugin_registry
        pass
