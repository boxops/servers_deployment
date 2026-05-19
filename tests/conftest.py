"""
Shared pytest fixtures and utilities for the infrastructure test suite.

All external services (NetBox, Zabbix, Kea DHCP, Tachyon devices) are mocked
so that tests run without real network connectivity.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path helpers – make source modules importable from tests/
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).parent.parent

def add_to_sys_path(rel_path: str) -> None:
    """Add a project-relative path to sys.path if not already present."""
    p = str(PROJECT_ROOT / rel_path)
    if p not in sys.path:
        sys.path.insert(0, p)


# Pre-register all script directories so test files can import cleanly.
add_to_sys_path("scripts")
add_to_sys_path("ansible/kea_dhcp/scripts")
add_to_sys_path("ansible/zabbix/scripts")
add_to_sys_path("ansible/oxidized/scripts")


# ---------------------------------------------------------------------------
# NetBox mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_netbox_ip_ranges():
    """Sample IP range data as returned by pynetbox ipam.ip_ranges.all()."""
    return [
        {
            "id": 1,
            "start_address": "192.168.1.10/24",
            "end_address": "192.168.1.200/24",
            "custom_fields": {
                "DHCPPoolSubnet": "192.168.1.0/24",
                "DHCPCreatePools": True,
                "DHCPPoolDefaultGateway": "192.168.1.1",
                "DHCPPoolRelayIPs": "192.168.1.254",
                "DHCPPoolOptions": [{"name": "domain-name-servers", "data": "8.8.8.8"}],
            },
        },
        {
            "id": 2,
            "start_address": "10.0.0.10/8",
            "end_address": "10.0.0.100/8",
            "custom_fields": {
                "DHCPPoolSubnet": "10.0.0.0/8",
                "DHCPCreatePools": True,
                "DHCPPoolDefaultGateway": "10.0.0.1",
                "DHCPPoolRelayIPs": None,
                "DHCPPoolOptions": None,
            },
        },
    ]


@pytest.fixture
def mock_netbox_ip_address_factory():
    """Factory that creates mock pynetbox IP address objects."""
    def _factory(ip="192.168.1.50/24", hw_address="aa:bb:cc:dd:ee:ff",
                 circuit_id=None, is_reservation=True, is_kea_managed=True):
        obj = MagicMock()
        obj.address = ip
        obj.custom_fields = {
            "DHCPIsReservation": is_reservation,
            "IsKeaManaged": is_kea_managed,
            "DHCPHardwareAddress": hw_address,
            "DHCPCircuitID": circuit_id,
        }
        return obj
    return _factory


@pytest.fixture
def mock_netbox_prefix_factory():
    """Factory that creates mock pynetbox prefix objects."""
    def _factory(prefix="192.168.1.0/24"):
        obj = MagicMock()
        obj.prefix = prefix
        return obj
    return _factory


@pytest.fixture
def mock_netbox_device():
    """A single mock pynetbox device object."""
    device = MagicMock()
    device.name = "test-router-01"
    device.primary_ip = MagicMock()
    device.primary_ip.__str__ = lambda self: "192.168.1.100/24"
    device.device_type = MagicMock()
    device.device_type.display = "Cisco ISR 4321"
    device.device_type.model = "ISR4321"
    device.device_type.manufacturer = MagicMock()
    device.device_type.manufacturer.name = "Cisco"
    device.site = MagicMock()
    device.site.name = "Main Site"
    device.site.latitude = "40.7128"
    device.site.longitude = "-74.0060"
    device.location = MagicMock()
    device.location.name = "Rack A"
    device.platform = MagicMock()
    device.platform.name = "cisco-ios"
    device.role = MagicMock()
    device.role.name = "Router"
    device.status = MagicMock()
    device.status.label = "Active"
    device.custom_fields = {"SNMPCommunity": "public", "ZabbixTemplates": None}
    return device


# ---------------------------------------------------------------------------
# Kea DHCP mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kea_config():
    """Minimal valid Kea DHCP4 config structure as returned by config_get()."""
    return {
        "result": 0,
        "arguments": {
            "Dhcp4": {
                "subnet4": [],
                "shared-networks": [],
                "interfaces-config": {"interfaces": ["eth0"]},
            }
        },
    }


@pytest.fixture
def mock_kea_result_ok():
    """A successful Kea API result."""
    return {"result": 0, "text": "Configuration set successfully."}


# ---------------------------------------------------------------------------
# Zabbix mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_zabbix_host():
    """A minimal Zabbix host dict."""
    return {"hostid": "10001", "host": "test-router-01", "name": "test-router-01"}


@pytest.fixture
def mock_zabbix_template():
    """A minimal Zabbix template dict."""
    return {"templateid": "10563", "name": "Generic by SNMP", "groupid": "5"}


@pytest.fixture
def mock_zabbix_group():
    """A minimal Zabbix host group dict."""
    return {"groupid": "42", "name": "Network Devices"}


# ---------------------------------------------------------------------------
# Tachyon device mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tachyon_login_response():
    """Mock successful Tachyon login response body."""
    return {"token": "abc123token"}


@pytest.fixture
def tachyon_config_response():
    """Mock Tachyon config fetch response body."""
    return {
        "config": {
            "system": {"hostname": "test-device", "firmware": "1.0.0"},
            "wireless": {},
            "network": {},
        }
    }


@pytest.fixture
def tachyon_push_response():
    """Mock Tachyon config push response body."""
    return {
        "status_msg": "OK",
        "response": {
            "reboot_required": False,
            "keys_changed": ["system.hostname"],
            "keys_added": [],
            "keys_removed": [],
            "warnings": [],
        },
    }


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_tfvars_content():
    """Content for a minimal terraform.tfvars file."""
    return """
proxmox_api_url = "https://pve.example.com:8006/api2/json"
proxmox_node    = "pve"
proxmox_bridge  = "vmbr0"
proxmox_storage = "local-lvm"
vm_template     = "ubuntu-cloud-22.04"

network_gateway = "192.168.1.1"
network_cidr    = "24"

# Zabbix Server
zabbix_server_vmid   = "200"
zabbix_server_cores  = "4"
zabbix_server_memory = "4096"
"""


@pytest.fixture
def sample_inventory_content():
    """Content for a minimal Ansible inventory YAML file."""
    return {
        "all": {
            "children": {
                "zabbix": {
                    "children": {
                        "zabbix_servers": {
                            "hosts": {
                                "zabbix-server-01": {
                                    "ansible_host": "192.168.1.10",
                                    "zabbix_server_dbhost": "localhost",
                                    "zabbix_server_dbname": "zabbix",
                                    "zabbix_server_dbuser": "zabbix",
                                }
                            }
                        },
                        "zabbix_proxies": {
                            "hosts": {
                                "zabbix-proxy-01": {
                                    "ansible_host": "192.168.1.20",
                                    "zabbix_proxy_server": "192.168.1.10",
                                    "zabbix_proxy_dbhost": "localhost",
                                    "zabbix_proxy_dbname": "zabbix_proxy",
                                    "zabbix_proxy_dbuser": "zabbix_proxy",
                                }
                            }
                        },
                    }
                }
            }
        }
    }


# ---------------------------------------------------------------------------
# SNMP walk sample data
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_snmpwalk_output():
    """A small sample of snmpwalk text output."""
    return (
        "iso.3.6.1.2.1.1.1.0 = STRING: \"Linux router 5.4.0\"\n"
        "iso.3.6.1.2.1.1.3.0 = Timeticks: (12345) 0:02:03.45\n"
        "iso.3.6.1.2.1.2.2.1.2.1 = STRING: \"eth0\"\n"
        "iso.3.6.1.2.1.2.2.1.2.2 = STRING: \"eth1\"\n"
    )


@pytest.fixture
def sample_snmpwalk_parsed():
    """Expected parsed dict from sample_snmpwalk_output."""
    return {
        "1.3.6.1.2.1.1.1.0": 'STRING: "Linux router 5.4.0"',
        "1.3.6.1.2.1.1.3.0": "Timeticks: (12345) 0:02:03.45",
        "1.3.6.1.2.1.2.2.1.2.1": 'STRING: "eth0"',
        "1.3.6.1.2.1.2.2.1.2.2": 'STRING: "eth1"',
    }


# ---------------------------------------------------------------------------
# CSV MIB data fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_csv_content():
    """Minimal MIB walk CSV content for template generator tests."""
    return (
        "OID,Name,Type,Value\n"
        "1.3.6.1.2.1.1.1.0,sysDescr,STRING,Linux router\n"
        "1.3.6.1.2.1.2.2.1.2.1,ifDescr,STRING,eth0\n"
        "1.3.6.1.2.1.2.2.1.2.2,ifDescr,STRING,eth1\n"
    )
