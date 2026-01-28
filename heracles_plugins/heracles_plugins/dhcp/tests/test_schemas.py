"""Unit tests for DHCP plugin Pydantic schemas."""

import pytest
from pydantic import ValidationError

from heracles_plugins.dhcp.schemas import (
    DhcpObjectType,
    TsigKeyAlgorithm,
    # Service schemas
    DhcpServiceCreate,
    DhcpServiceUpdate,
    DhcpServiceRead,
    # Subnet schemas
    DhcpSubnetCreate,
    DhcpSubnetUpdate,
    DhcpSubnetRead,
    # Pool schemas
    DhcpPoolCreate,
    DhcpPoolUpdate,
    DhcpPoolRead,
    # Host schemas
    DhcpHostCreate,
    DhcpHostUpdate,
    DhcpHostRead,
    # Shared Network schemas
    DhcpSharedNetworkCreate,
    DhcpSharedNetworkUpdate,
    DhcpSharedNetworkRead,
    # Group schemas
    DhcpGroupCreate,
    DhcpGroupUpdate,
    DhcpGroupRead,
    # Class schemas
    DhcpClassCreate,
    DhcpClassUpdate,
    DhcpClassRead,
    # SubClass schemas
    DhcpSubClassCreate,
    DhcpSubClassUpdate,
    DhcpSubClassRead,
    # TSIG Key schemas
    DhcpTsigKeyCreate,
    DhcpTsigKeyUpdate,
    DhcpTsigKeyRead,
    # DNS Zone schemas
    DhcpDnsZoneCreate,
    DhcpDnsZoneUpdate,
    DhcpDnsZoneRead,
    # Failover Peer schemas
    DhcpFailoverPeerCreate,
    DhcpFailoverPeerUpdate,
    DhcpFailoverPeerRead,
    # Validators
    validate_ip_address,
    validate_ip_range,
    validate_mac_address,
    validate_netmask,
)


# =============================================================================
# Enum Tests
# =============================================================================


class TestDhcpObjectTypeEnum:
    """Tests for DhcpObjectType enum."""

    def test_all_object_types_defined(self):
        """Verify all expected object types are defined."""
        expected_types = [
            "SERVICE",
            "SHARED_NETWORK",
            "SUBNET",
            "POOL",
            "HOST",
            "GROUP",
            "CLASS",
            "SUBCLASS",
            "TSIG_KEY",
            "DNS_ZONE",
            "FAILOVER_PEER",
        ]
        for type_name in expected_types:
            assert hasattr(DhcpObjectType, type_name)

    def test_object_type_values(self):
        """Verify object type string values."""
        assert DhcpObjectType.SERVICE.value == "service"
        assert DhcpObjectType.SUBNET.value == "subnet"
        assert DhcpObjectType.HOST.value == "host"
        assert DhcpObjectType.POOL.value == "pool"


class TestTsigKeyAlgorithmEnum:
    """Tests for TsigKeyAlgorithm enum."""

    def test_all_algorithms_defined(self):
        """Verify all TSIG key algorithms are defined."""
        expected_algorithms = ["HMAC_MD5", "HMAC_SHA1", "HMAC_SHA256", "HMAC_SHA512"]
        for algo in expected_algorithms:
            assert hasattr(TsigKeyAlgorithm, algo)

    def test_algorithm_values(self):
        """Verify algorithm string values match ISC DHCP format."""
        assert TsigKeyAlgorithm.HMAC_MD5.value == "hmac-md5"
        assert TsigKeyAlgorithm.HMAC_SHA256.value == "hmac-sha256"


# =============================================================================
# Validator Tests
# =============================================================================


class TestValidators:
    """Tests for validation functions."""

    def test_validate_ip_address_valid(self):
        """Test valid IP addresses."""
        valid_ips = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255",
            "0.0.0.0",
        ]
        for ip in valid_ips:
            assert validate_ip_address(ip) == ip

    def test_validate_ip_address_invalid(self):
        """Test invalid IP addresses."""
        invalid_ips = [
            "256.1.1.1",
            "192.168.1",
            "192.168.1.1.1",
            "abc.def.ghi.jkl",
            "192.168.1.a",
            "",
            "192.168.1.1/24",
        ]
        for ip in invalid_ips:
            with pytest.raises(ValueError):
                validate_ip_address(ip)

    def test_validate_ip_range_valid(self):
        """Test valid IP ranges."""
        valid_ranges = [
            "192.168.1.10 192.168.1.20",
            "10.0.0.1 10.0.0.254",
        ]
        for range_str in valid_ranges:
            assert validate_ip_range(range_str) == range_str

    def test_validate_ip_range_invalid(self):
        """Test invalid IP ranges."""
        invalid_ranges = [
            "192.168.1.20 192.168.1.10",  # End before start
            "192.168.1.10",  # Missing end
            "192.168.1.10-192.168.1.20",  # Wrong separator
            "invalid 192.168.1.20",
        ]
        for range_str in invalid_ranges:
            with pytest.raises(ValueError):
                validate_ip_range(range_str)

    def test_validate_mac_address_valid(self):
        """Test valid MAC addresses."""
        valid_macs = [
            "00:11:22:33:44:55",
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
            "00-11-22-33-44-55",
            "AA-BB-CC-DD-EE-FF",
        ]
        for mac in valid_macs:
            # Should not raise
            result = validate_mac_address(mac)
            assert result is not None

    def test_validate_mac_address_invalid(self):
        """Test invalid MAC addresses."""
        invalid_macs = [
            "00:11:22:33:44",  # Too short
            "00:11:22:33:44:55:66",  # Too long
            "GG:HH:II:JJ:KK:LL",  # Invalid hex
            "001122334455",  # No separator
        ]
        for mac in invalid_macs:
            with pytest.raises(ValueError):
                validate_mac_address(mac)

    def test_validate_netmask_valid(self):
        """Test valid netmasks."""
        valid_netmasks = [0, 8, 16, 24, 32]
        for mask in valid_netmasks:
            assert validate_netmask(mask) == mask

    def test_validate_netmask_invalid(self):
        """Test invalid netmasks."""
        invalid_netmasks = [-1, 33, 100]
        for mask in invalid_netmasks:
            with pytest.raises(ValueError):
                validate_netmask(mask)


# =============================================================================
# Service Schema Tests
# =============================================================================


class TestDhcpServiceSchemas:
    """Tests for DHCP Service schemas."""

    def test_service_create_minimal(self):
        """Test creating service with minimal required fields."""
        service = DhcpServiceCreate(cn="main-dhcp")
        assert service.cn == "main-dhcp"
        assert service.statements == []
        assert service.options == []

    def test_service_create_full(self):
        """Test creating service with all fields."""
        service = DhcpServiceCreate(
            cn="production-dhcp",
            description="Production DHCP Service",
            statements=["authoritative", "ddns-update-style interim"],
            options=["domain-name-servers 8.8.8.8", "domain-name example.com"],
            primary_server_dn="cn=dhcp1,ou=servers,dc=example,dc=com",
            secondary_server_dn="cn=dhcp2,ou=servers,dc=example,dc=com",
        )
        assert service.cn == "production-dhcp"
        assert service.description == "Production DHCP Service"
        assert len(service.statements) == 2
        assert len(service.options) == 2

    def test_service_create_invalid_cn(self):
        """Test that empty cn raises validation error."""
        with pytest.raises(ValidationError):
            DhcpServiceCreate(cn="")

    def test_service_update_partial(self):
        """Test partial service update."""
        update = DhcpServiceUpdate(description="Updated description")
        assert update.description == "Updated description"
        assert update.statements is None
        assert update.options is None

    def test_service_read_from_dict(self):
        """Test creating read model from dict (simulating LDAP response)."""
        data = {
            "dn": "cn=mydhcp,ou=dhcp,dc=example,dc=com",
            "cn": "mydhcp",
            "description": "Test DHCP",
            "statements": ["authoritative"],
            "options": ["domain-name test.local"],
        }
        service = DhcpServiceRead(**data)
        assert service.dn == "cn=mydhcp,ou=dhcp,dc=example,dc=com"
        assert service.cn == "mydhcp"


# =============================================================================
# Subnet Schema Tests
# =============================================================================


class TestDhcpSubnetSchemas:
    """Tests for DHCP Subnet schemas."""

    def test_subnet_create_minimal(self):
        """Test creating subnet with minimal required fields."""
        subnet = DhcpSubnetCreate(cn="192.168.1.0", netmask=24)
        assert subnet.cn == "192.168.1.0"
        assert subnet.netmask == 24

    def test_subnet_create_full(self):
        """Test creating subnet with all fields."""
        subnet = DhcpSubnetCreate(
            cn="10.0.0.0",
            netmask=8,
            description="Office network",
            range="10.0.0.100 10.0.0.200",
            statements=["default-lease-time 3600", "max-lease-time 7200"],
            options=["routers 10.0.0.1", "domain-name-servers 10.0.0.2"],
            dns_zone_dn="cn=office.local,ou=dns,dc=example,dc=com",
            failover_peer_dn="cn=dhcp-failover,ou=dhcp,dc=example,dc=com",
        )
        assert subnet.cn == "10.0.0.0"
        assert subnet.netmask == 8
        assert subnet.range == "10.0.0.100 10.0.0.200"

    def test_subnet_create_invalid_netmask(self):
        """Test that invalid netmask raises validation error."""
        with pytest.raises(ValidationError):
            DhcpSubnetCreate(cn="192.168.1.0", netmask=33)

    def test_subnet_create_invalid_range(self):
        """Test that invalid range raises validation error."""
        with pytest.raises(ValidationError):
            DhcpSubnetCreate(
                cn="192.168.1.0",
                netmask=24,
                range="192.168.1.200 192.168.1.100",  # End before start
            )


# =============================================================================
# Pool Schema Tests
# =============================================================================


class TestDhcpPoolSchemas:
    """Tests for DHCP Pool schemas."""

    def test_pool_create_minimal(self):
        """Test creating pool with minimal required fields."""
        pool = DhcpPoolCreate(cn="pool1", range="192.168.1.100 192.168.1.200")
        assert pool.cn == "pool1"
        assert pool.range == "192.168.1.100 192.168.1.200"

    def test_pool_create_with_permits(self):
        """Test creating pool with permit lists."""
        pool = DhcpPoolCreate(
            cn="known-clients-pool",
            range="192.168.1.50 192.168.1.99",
            description="Pool for known clients only",
            permit_list=["allow known-clients", "deny unknown-clients"],
            statements=["default-lease-time 86400"],
        )
        assert len(pool.permit_list) == 2
        assert "allow known-clients" in pool.permit_list

    def test_pool_create_invalid_range(self):
        """Test that missing range raises validation error."""
        with pytest.raises(ValidationError):
            DhcpPoolCreate(cn="pool1", range="")


# =============================================================================
# Host Schema Tests
# =============================================================================


class TestDhcpHostSchemas:
    """Tests for DHCP Host schemas."""

    def test_host_create_minimal(self):
        """Test creating host with minimal required fields."""
        host = DhcpHostCreate(cn="workstation1")
        assert host.cn == "workstation1"

    def test_host_create_full(self):
        """Test creating host with all fields."""
        host = DhcpHostCreate(
            cn="server1",
            description="Production server",
            hw_address="ethernet 00:11:22:33:44:55",
            statements=["fixed-address 192.168.1.10"],
            options=["host-name server1.example.com"],
        )
        assert host.cn == "server1"
        assert host.hw_address == "ethernet 00:11:22:33:44:55"

    def test_host_read_model(self):
        """Test host read model with system reference."""
        data = {
            "dn": "cn=workstation1,cn=mydhcp,ou=dhcp,dc=example,dc=com",
            "cn": "workstation1",
            "hw_address": "ethernet aa:bb:cc:dd:ee:ff",
            "statements": ["fixed-address 192.168.1.50"],
            "options": [],
            "system_dn": "cn=workstation1,ou=systems,dc=example,dc=com",
        }
        host = DhcpHostRead(**data)
        assert host.system_dn == "cn=workstation1,ou=systems,dc=example,dc=com"


# =============================================================================
# Shared Network Schema Tests
# =============================================================================


class TestDhcpSharedNetworkSchemas:
    """Tests for DHCP Shared Network schemas."""

    def test_shared_network_create_minimal(self):
        """Test creating shared network with minimal required fields."""
        network = DhcpSharedNetworkCreate(cn="office-network")
        assert network.cn == "office-network"

    def test_shared_network_create_full(self):
        """Test creating shared network with all fields."""
        network = DhcpSharedNetworkCreate(
            cn="campus-network",
            description="Main campus shared network",
            statements=["authoritative"],
            options=["domain-name campus.edu"],
        )
        assert network.cn == "campus-network"
        assert network.description == "Main campus shared network"


# =============================================================================
# Group Schema Tests
# =============================================================================


class TestDhcpGroupSchemas:
    """Tests for DHCP Group schemas."""

    def test_group_create_minimal(self):
        """Test creating group with minimal required fields."""
        group = DhcpGroupCreate(cn="printers")
        assert group.cn == "printers"

    def test_group_create_full(self):
        """Test creating group with all fields."""
        group = DhcpGroupCreate(
            cn="voip-phones",
            description="VoIP phone devices",
            statements=["default-lease-time 3600"],
            options=["tftp-server-name 192.168.1.5"],
        )
        assert group.cn == "voip-phones"


# =============================================================================
# Class Schema Tests
# =============================================================================


class TestDhcpClassSchemas:
    """Tests for DHCP Class schemas."""

    def test_class_create_minimal(self):
        """Test creating class with minimal required fields."""
        dhcp_class = DhcpClassCreate(cn="known-clients")
        assert dhcp_class.cn == "known-clients"

    def test_class_create_with_match(self):
        """Test creating class with match expression."""
        dhcp_class = DhcpClassCreate(
            cn="vendor-class",
            description="Match by vendor class identifier",
            statements=['match if option vendor-class-identifier = "MSFT"'],
        )
        assert len(dhcp_class.statements) == 1


class TestDhcpSubClassSchemas:
    """Tests for DHCP SubClass schemas."""

    def test_subclass_create_minimal(self):
        """Test creating subclass with minimal required fields."""
        subclass = DhcpSubClassCreate(cn="special-client")
        assert subclass.cn == "special-client"

    def test_subclass_create_with_data(self):
        """Test creating subclass with class data."""
        subclass = DhcpSubClassCreate(
            cn="client-01:02:03:04:05:06",
            description="Specific MAC address client",
            class_data="01:02:03:04:05:06",
        )
        assert subclass.class_data == "01:02:03:04:05:06"


# =============================================================================
# TSIG Key Schema Tests
# =============================================================================


class TestDhcpTsigKeySchemas:
    """Tests for DHCP TSIG Key schemas."""

    def test_tsig_key_create_minimal(self):
        """Test creating TSIG key with minimal required fields."""
        key = DhcpTsigKeyCreate(
            cn="ddns-key",
            algorithm=TsigKeyAlgorithm.HMAC_SHA256,
            secret="c2VjcmV0a2V5MTIzNDU2Nzg=",
        )
        assert key.cn == "ddns-key"
        assert key.algorithm == TsigKeyAlgorithm.HMAC_SHA256
        assert key.secret == "c2VjcmV0a2V5MTIzNDU2Nzg="

    def test_tsig_key_create_missing_secret(self):
        """Test that missing secret raises validation error."""
        with pytest.raises(ValidationError):
            DhcpTsigKeyCreate(cn="ddns-key", algorithm=TsigKeyAlgorithm.HMAC_SHA256)

    def test_tsig_key_update_partial(self):
        """Test partial TSIG key update."""
        update = DhcpTsigKeyUpdate(description="Updated key description")
        assert update.description == "Updated key description"
        assert update.algorithm is None
        assert update.secret is None


# =============================================================================
# DNS Zone Schema Tests
# =============================================================================


class TestDhcpDnsZoneSchemas:
    """Tests for DHCP DNS Zone schemas."""

    def test_dns_zone_create_minimal(self):
        """Test creating DNS zone with minimal required fields."""
        zone = DhcpDnsZoneCreate(cn="example.com", dns_server="ns1.example.com")
        assert zone.cn == "example.com"
        assert zone.dns_server == "ns1.example.com"

    def test_dns_zone_create_with_key(self):
        """Test creating DNS zone with TSIG key reference."""
        zone = DhcpDnsZoneCreate(
            cn="internal.local",
            dns_server="192.168.1.2",
            description="Internal DNS zone",
            tsig_key_dn="cn=ddns-key,cn=mydhcp,ou=dhcp,dc=example,dc=com",
        )
        assert zone.tsig_key_dn is not None

    def test_dns_zone_create_missing_server(self):
        """Test that missing dns_server raises validation error."""
        with pytest.raises(ValidationError):
            DhcpDnsZoneCreate(cn="example.com")


# =============================================================================
# Failover Peer Schema Tests
# =============================================================================


class TestDhcpFailoverPeerSchemas:
    """Tests for DHCP Failover Peer schemas."""

    def test_failover_peer_create_minimal(self):
        """Test creating failover peer with minimal required fields."""
        peer = DhcpFailoverPeerCreate(
            cn="dhcp-failover",
            primary_server="192.168.1.10",
            secondary_server="192.168.1.11",
            primary_port=647,
            secondary_port=647,
        )
        assert peer.cn == "dhcp-failover"
        assert peer.primary_server == "192.168.1.10"
        assert peer.secondary_server == "192.168.1.11"

    def test_failover_peer_create_full(self):
        """Test creating failover peer with all fields."""
        peer = DhcpFailoverPeerCreate(
            cn="production-failover",
            description="Production DHCP failover configuration",
            primary_server="dhcp1.example.com",
            secondary_server="dhcp2.example.com",
            primary_port=647,
            secondary_port=647,
            response_delay=60,
            unacked_updates=10,
            max_client_lead_time=3600,
            split=128,
            load_balance_time=3,
        )
        assert peer.response_delay == 60
        assert peer.split == 128

    def test_failover_peer_create_missing_required(self):
        """Test that missing required fields raises validation error."""
        with pytest.raises(ValidationError):
            DhcpFailoverPeerCreate(cn="failover")  # Missing servers and ports

    def test_failover_peer_update_partial(self):
        """Test partial failover peer update."""
        update = DhcpFailoverPeerUpdate(response_delay=120, split=200)
        assert update.response_delay == 120
        assert update.split == 200
        assert update.primary_server is None


# =============================================================================
# Cross-Schema Tests
# =============================================================================


class TestCrossSchemaValidation:
    """Tests for cross-schema validation and relationships."""

    def test_all_create_schemas_have_cn(self):
        """Verify all create schemas require cn field."""
        create_schemas = [
            DhcpServiceCreate,
            DhcpSubnetCreate,
            DhcpPoolCreate,
            DhcpHostCreate,
            DhcpSharedNetworkCreate,
            DhcpGroupCreate,
            DhcpClassCreate,
            DhcpSubClassCreate,
            DhcpTsigKeyCreate,
            DhcpDnsZoneCreate,
            DhcpFailoverPeerCreate,
        ]
        for schema in create_schemas:
            fields = schema.model_fields
            assert "cn" in fields, f"{schema.__name__} missing cn field"

    def test_all_read_schemas_have_dn_and_cn(self):
        """Verify all read schemas have dn and cn fields."""
        read_schemas = [
            DhcpServiceRead,
            DhcpSubnetRead,
            DhcpPoolRead,
            DhcpHostRead,
            DhcpSharedNetworkRead,
            DhcpGroupRead,
            DhcpClassRead,
            DhcpSubClassRead,
            DhcpTsigKeyRead,
            DhcpDnsZoneRead,
            DhcpFailoverPeerRead,
        ]
        for schema in read_schemas:
            fields = schema.model_fields
            assert "dn" in fields, f"{schema.__name__} missing dn field"
            assert "cn" in fields, f"{schema.__name__} missing cn field"

    def test_update_schemas_allow_none(self):
        """Verify update schemas allow None for all fields (partial update)."""
        # Test that update schemas can be created with no arguments
        DhcpServiceUpdate()
        DhcpSubnetUpdate()
        DhcpPoolUpdate()
        DhcpHostUpdate()
        DhcpSharedNetworkUpdate()
        DhcpGroupUpdate()
        DhcpClassUpdate()
        DhcpSubClassUpdate()
        DhcpTsigKeyUpdate()
        DhcpDnsZoneUpdate()
        DhcpFailoverPeerUpdate()
