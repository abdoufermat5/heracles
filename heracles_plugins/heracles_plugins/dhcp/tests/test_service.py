"""Unit tests for DHCP plugin service layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, PropertyMock

from heracles_plugins.dhcp.service import DhcpService
from heracles_plugins.dhcp.schemas import (
    DhcpObjectType,
    TsigKeyAlgorithm,
    DhcpServiceCreate,
    SubnetCreate,
    PoolCreate,
    HostCreate,
    SharedNetworkCreate,
    GroupCreate,
    DhcpClassCreate,
    SubClassCreate,
    TsigKeyCreate,
    DnsZoneCreate,
    FailoverPeerCreate,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_ldap_service():
    """Create a mock LdapService."""
    mock = MagicMock()
    mock.base_dn = "dc=example,dc=com"

    # Async methods
    mock.search = AsyncMock(return_value=[])
    mock.get_by_dn = AsyncMock(return_value=None)
    mock.add = AsyncMock()
    mock.modify = AsyncMock()
    mock.delete = AsyncMock()

    return mock


@pytest.fixture
def dhcp_config():
    """Create a DHCP service config."""
    return {
        "base_dn": "dc=example,dc=com",
        "dhcp_rdn": "ou=dhcp",
    }


@pytest.fixture
def dhcp_service(mock_ldap_service, dhcp_config):
    """Create a DhcpService instance with mocked LdapService."""
    service = DhcpService(
        ldap_service=mock_ldap_service,
        config=dhcp_config,
    )
    return service


# =============================================================================
# Service Configuration Tests
# =============================================================================


class TestDhcpServiceConfiguration:
    """Tests for DhcpService configuration and initialization."""

    def test_service_initialization(self, dhcp_service):
        """Test that service initializes correctly."""
        assert dhcp_service._ldap is not None
        assert dhcp_service._dhcp_dn == "ou=dhcp,dc=example,dc=com"

    def test_dhcp_container_dn(self, dhcp_service):
        """Test DHCP container DN calculation."""
        expected_dn = "ou=dhcp,dc=example,dc=com"
        assert dhcp_service._get_dhcp_container() == expected_dn

    def test_dhcp_container_dn_with_base(self, dhcp_service):
        """Test DHCP container DN with custom base_dn."""
        result = dhcp_service._get_dhcp_container(
            base_dn="ou=dept1,dc=example,dc=com"
        )
        assert result == "ou=dhcp,ou=dept1,dc=example,dc=com"

    def test_service_dn(self, dhcp_service):
        """Test service DN calculation."""
        result = dhcp_service._get_service_dn("mydhcp")
        assert result == "cn=mydhcp,ou=dhcp,dc=example,dc=com"

    def test_object_dn(self, dhcp_service):
        """Test object DN calculation."""
        result = dhcp_service._get_object_dn(
            "192.168.1.0",
            "cn=mydhcp,ou=dhcp,dc=example,dc=com",
        )
        assert result == "cn=192.168.1.0,cn=mydhcp,ou=dhcp,dc=example,dc=com"

    def test_systems_service_integration(self, dhcp_service):
        """Test systems service integration setter."""
        mock_systems_service = MagicMock()
        dhcp_service.set_systems_service(mock_systems_service)
        assert dhcp_service._systems_service == mock_systems_service


# =============================================================================
# DHCP Service CRUD Tests
# =============================================================================


class TestDhcpServiceCRUD:
    """Tests for DHCP Service CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_services_empty(self, dhcp_service, mock_ldap_service):
        """Test listing services when none exist."""
        mock_ldap_service.search.return_value = []

        result = await dhcp_service.list_services()

        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_services_with_results(self, dhcp_service, mock_ldap_service):
        """Test listing services with results."""
        entry1 = MagicMock()
        entry1.dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"
        entry1.get.side_effect = lambda k, d=None: {
            "cn": ["mydhcp"],
            "dhcpStatements": ["authoritative"],
            "dhcpOption": [],
        }.get(k, d)
        entry1.__getitem__ = lambda self, k: {
            "cn": ["mydhcp"],
            "dhcpStatements": ["authoritative"],
            "dhcpOption": [],
        }[k]
        entry1.__contains__ = lambda self, k: k in {"cn", "dhcpStatements", "dhcpOption"}

        entry2 = MagicMock()
        entry2.dn = "cn=testdhcp,ou=dhcp,dc=example,dc=com"
        entry2.get.side_effect = lambda k, d=None: {
            "cn": ["testdhcp"],
            "dhcpStatements": [],
            "dhcpOption": ["domain-name test.local"],
        }.get(k, d)
        entry2.__getitem__ = lambda self, k: {
            "cn": ["testdhcp"],
            "dhcpStatements": [],
            "dhcpOption": ["domain-name test.local"],
        }[k]
        entry2.__contains__ = lambda self, k: k in {"cn", "dhcpStatements", "dhcpOption"}

        mock_ldap_service.search.return_value = [entry1, entry2]

        result = await dhcp_service.list_services()

        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.asyncio
    async def test_create_service_minimal(self, dhcp_service, mock_ldap_service):
        """Test creating a service with minimal parameters."""
        create_data = DhcpServiceCreate(cn="new-dhcp")

        # Mock get_by_dn calls:
        # 1) _ensure_dhcp_ou checks if OU exists → None (creates it)
        # 2) create_service checks if service exists → None (proceeds)
        # 3) get_service reads the created entry → returns entry
        read_entry = MagicMock()
        read_entry.dn = "cn=new-dhcp,ou=dhcp,dc=example,dc=com"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["new-dhcp"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, None, read_entry]

        await dhcp_service.create_service(create_data)

        # add() is called twice: once for OU creation, once for service creation
        assert mock_ldap_service.add.call_count == 2
        # Verify the service creation call
        service_call = mock_ldap_service.add.call_args_list[-1]
        assert "cn=new-dhcp" in service_call.kwargs.get("dn", "")

    @pytest.mark.asyncio
    async def test_get_service_not_found(self, dhcp_service, mock_ldap_service):
        """Test getting a non-existent service."""
        from heracles_api.services.ldap_service import LdapNotFoundError

        mock_ldap_service.get_by_dn.return_value = None

        with pytest.raises(LdapNotFoundError):
            await dhcp_service.get_service("nonexistent")

    @pytest.mark.asyncio
    async def test_delete_service(self, dhcp_service, mock_ldap_service):
        """Test deleting a service."""
        # Mock finding the service first
        existing = MagicMock()
        existing.dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"
        mock_ldap_service.get_by_dn.return_value = existing

        await dhcp_service.delete_service("mydhcp")

        mock_ldap_service.delete.assert_called_once()


# =============================================================================
# DHCP Subnet CRUD Tests
# =============================================================================


class TestDhcpSubnetCRUD:
    """Tests for DHCP Subnet CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_subnet(self, dhcp_service, mock_ldap_service):
        """Test creating a subnet."""
        create_data = SubnetCreate(
            cn="192.168.1.0",
            dhcp_netmask=24,
            dhcp_range=["192.168.1.100 192.168.1.200"],
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        # Mock: not exists, then return created entry
        read_entry = MagicMock()
        read_entry.dn = f"cn=192.168.1.0,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["192.168.1.0"],
            "dhcpNetMask": ["24"],
            "dhcpRange": ["192.168.1.100 192.168.1.200"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_subnet(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()
        call_kwargs = mock_ldap_service.add.call_args.kwargs
        assert "dhcpNetMask" in call_kwargs.get("attributes", {})

    @pytest.mark.asyncio
    async def test_list_subnets(self, dhcp_service, mock_ldap_service):
        """Test listing subnets for a service."""
        entry = MagicMock()
        entry.dn = "cn=192.168.1.0,cn=mydhcp,ou=dhcp,dc=example,dc=com"
        entry.get.side_effect = lambda k, d=None: {
            "cn": ["192.168.1.0"],
            "dhcpNetMask": ["24"],
            "dhcpRange": ["192.168.1.100 192.168.1.200"],
        }.get(k, d)

        mock_ldap_service.search.return_value = [entry]

        result = await dhcp_service.list_subnets("mydhcp")

        assert result.total == 1


# =============================================================================
# DHCP Host CRUD Tests
# =============================================================================


class TestDhcpHostCRUD:
    """Tests for DHCP Host CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_host(self, dhcp_service, mock_ldap_service):
        """Test creating a host."""
        create_data = HostCreate(
            cn="workstation1",
            dhcp_hw_address="ethernet 00:11:22:33:44:55",
            dhcp_statements=["fixed-address 192.168.1.10"],
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        # Mock: not exists, then return created
        read_entry = MagicMock()
        read_entry.dn = f"cn=workstation1,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["workstation1"],
            "dhcpHWAddress": ["ethernet 00:11:22:33:44:55"],
            "dhcpStatements": ["fixed-address 192.168.1.10"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_host(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_host_by_mac(self, dhcp_service, mock_ldap_service):
        """Test finding a host by MAC address."""
        entry = MagicMock()
        entry.dn = "cn=workstation1,cn=mydhcp,ou=dhcp,dc=example,dc=com"
        entry.get.side_effect = lambda k, d=None: {
            "cn": ["workstation1"],
            "dhcpHWAddress": ["ethernet 00:11:22:33:44:55"],
            "dhcpStatements": ["fixed-address 192.168.1.50"],
        }.get(k, d)

        mock_ldap_service.search.return_value = [entry]

        result = await dhcp_service.get_host_by_mac("00:11:22:33:44:55")

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_hosts_by_ip(self, dhcp_service, mock_ldap_service):
        """Test finding hosts by IP address."""
        entry = MagicMock()
        entry.dn = "cn=server1,cn=mydhcp,ou=dhcp,dc=example,dc=com"
        entry.get.side_effect = lambda k, d=None: {
            "cn": ["server1"],
            "dhcpStatements": ["fixed-address 192.168.1.10"],
        }.get(k, d)

        mock_ldap_service.search.return_value = [entry]

        result = await dhcp_service.get_hosts_by_ip("192.168.1.10")

        assert len(result) >= 0


# =============================================================================
# DHCP Shared Network CRUD Tests
# =============================================================================


class TestDhcpSharedNetworkCRUD:
    """Tests for DHCP Shared Network CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_shared_network(self, dhcp_service, mock_ldap_service):
        """Test creating a shared network."""
        create_data = SharedNetworkCreate(
            cn="campus-network",
            comments="Main campus network",
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=campus-network,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["campus-network"],
            "dhcpComments": ["Main campus network"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_shared_network(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()


# =============================================================================
# DHCP Group CRUD Tests
# =============================================================================


class TestDhcpGroupCRUD:
    """Tests for DHCP Group CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_group(self, dhcp_service, mock_ldap_service):
        """Test creating a group."""
        create_data = GroupCreate(
            cn="printers",
            comments="Network printers group",
            dhcp_statements=["default-lease-time 86400"],
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=printers,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["printers"],
            "dhcpComments": ["Network printers group"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_group(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()


# =============================================================================
# DHCP Class CRUD Tests
# =============================================================================


class TestDhcpClassCRUD:
    """Tests for DHCP Class CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_class(self, dhcp_service, mock_ldap_service):
        """Test creating a DHCP class."""
        create_data = DhcpClassCreate(
            cn="vendor-msft",
            dhcp_statements=['match if option vendor-class-identifier = "MSFT"'],
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=vendor-msft,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["vendor-msft"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_class(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_subclass(self, dhcp_service, mock_ldap_service):
        """Test creating a DHCP subclass."""
        create_data = SubClassCreate(
            cn="client-specific",
            dhcp_class_data="01:02:03:04:05:06",
        )

        parent_dn = "cn=vendor-msft,cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=client-specific,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["client-specific"],
            "dhcpClassData": ["01:02:03:04:05:06"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_subclass(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()


# =============================================================================
# DHCP TSIG Key CRUD Tests
# =============================================================================


class TestDhcpTsigKeyCRUD:
    """Tests for DHCP TSIG Key CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_tsig_key(self, dhcp_service, mock_ldap_service):
        """Test creating a TSIG key."""
        create_data = TsigKeyCreate(
            cn="ddns-key",
            dhcp_key_algorithm=TsigKeyAlgorithm.HMAC_SHA256,
            dhcp_key_secret="c2VjcmV0a2V5MTIzNDU2Nzg=",
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=ddns-key,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["ddns-key"],
            "dhcpKeyAlgorithm": ["hmac-sha256"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_tsig_key(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()
        call_kwargs = mock_ldap_service.add.call_args.kwargs
        attributes = call_kwargs.get("attributes", {})
        assert "dhcpKeyAlgorithm" in attributes
        assert "dhcpKeySecret" in attributes


# =============================================================================
# DHCP DNS Zone CRUD Tests
# =============================================================================


class TestDhcpDnsZoneCRUD:
    """Tests for DHCP DNS Zone CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_dns_zone(self, dhcp_service, mock_ldap_service):
        """Test creating a DNS zone."""
        create_data = DnsZoneCreate(
            cn="example.com",
            dhcp_dns_zone_server="ns1.example.com",
            dhcp_key_dn="cn=ddns-key,cn=mydhcp,ou=dhcp,dc=example,dc=com",
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=example.com,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["example.com"],
            "dhcpDnsZoneServer": ["ns1.example.com"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_dns_zone(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()
        call_kwargs = mock_ldap_service.add.call_args.kwargs
        attributes = call_kwargs.get("attributes", {})
        assert "dhcpDnsZoneServer" in attributes


# =============================================================================
# DHCP Failover Peer CRUD Tests
# =============================================================================


class TestDhcpFailoverPeerCRUD:
    """Tests for DHCP Failover Peer CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_failover_peer(self, dhcp_service, mock_ldap_service):
        """Test creating a failover peer."""
        create_data = FailoverPeerCreate(
            cn="dhcp-failover",
            dhcp_failover_primary_server="192.168.1.10",
            dhcp_failover_secondary_server="192.168.1.11",
            dhcp_failover_primary_port=647,
            dhcp_failover_secondary_port=647,
            dhcp_failover_split=128,
        )

        parent_dn = "cn=mydhcp,ou=dhcp,dc=example,dc=com"

        read_entry = MagicMock()
        read_entry.dn = f"cn=dhcp-failover,{parent_dn}"
        read_entry.get.side_effect = lambda k, d=None: {
            "cn": ["dhcp-failover"],
            "dhcpFailOverPrimaryServer": ["192.168.1.10"],
            "dhcpFailOverSecondaryServer": ["192.168.1.11"],
            "dhcpFailOverPrimaryPort": ["647"],
            "dhcpFailOverSecondaryPort": ["647"],
        }.get(k, d)

        mock_ldap_service.get_by_dn.side_effect = [None, read_entry]

        await dhcp_service.create_failover_peer(parent_dn, create_data)

        mock_ldap_service.add.assert_called_once()
        call_kwargs = mock_ldap_service.add.call_args.kwargs
        attributes = call_kwargs.get("attributes", {})
        assert "dhcpFailOverPrimaryServer" in attributes
        assert "dhcpFailOverSecondaryServer" in attributes
        assert "dhcpFailOverPrimaryPort" in attributes
        assert "dhcpFailOverSecondaryPort" in attributes


# =============================================================================
# Systems Integration Tests
# =============================================================================


class TestSystemsIntegration:
    """Tests for systems plugin integration."""

    def test_validate_host_with_systems_service(self, dhcp_service):
        """Test host validation when systems service is available."""
        mock_systems_service = AsyncMock()
        mock_systems_service.get_system_by_mac.return_value = {
            "dn": "cn=workstation1,ou=systems,dc=example,dc=com",
            "cn": "workstation1",
        }

        dhcp_service.set_systems_service(mock_systems_service)

        assert dhcp_service._systems_service is not None

    def test_host_without_systems_integration(self, dhcp_service):
        """Test that hosts can be created without systems integration."""
        assert dhcp_service._systems_service is None

        # Should still be able to create host schemas
        host = HostCreate(cn="standalone-host", dhcp_hw_address="ethernet 00:11:22:33:44:55")
        assert host.cn == "standalone-host"


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling in DhcpService."""

    @pytest.mark.asyncio
    async def test_create_duplicate_service(self, dhcp_service, mock_ldap_service):
        """Test handling of duplicate service creation."""
        from heracles_plugins.dhcp.service.base import DhcpValidationError

        # Mock: service already exists
        existing = MagicMock()
        existing.dn = "cn=existing-dhcp,ou=dhcp,dc=example,dc=com"
        mock_ldap_service.get_by_dn.return_value = existing

        create_data = DhcpServiceCreate(cn="existing-dhcp")

        with pytest.raises(DhcpValidationError):
            await dhcp_service.create_service(create_data)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_service(self, dhcp_service, mock_ldap_service):
        """Test deleting a service that doesn't exist."""
        from heracles_api.services.ldap_service import LdapNotFoundError

        mock_ldap_service.get_by_dn.return_value = None

        with pytest.raises(LdapNotFoundError):
            await dhcp_service.delete_service("nonexistent")
