"""
Unit tests for ansible/zabbix/scripts/sync_devices_from_netbox.py

All NetBox and Zabbix API calls are mocked via unittest.mock.
"""

import pytest
from unittest.mock import MagicMock, patch, call

# conftest.py adds ansible/zabbix/scripts to sys.path
from sync_devices_from_netbox import (
    NetBoxClient,
    ZabbixClient,
    NetboxZabbixSync,
)


# ---------------------------------------------------------------------------
# NetBoxClient
# ---------------------------------------------------------------------------


class TestNetBoxClientInit:
    def test_init_sets_token(self):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "my-token")
        assert client.conn.token == "my-token"

    def test_init_disables_ssl_verification(self):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "tok")
        conn.http_session.verify = False


class TestNetBoxClientFormatDeviceData:
    def _make_client(self):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            MockAPI.return_value = MagicMock()
            return NetBoxClient("http://netbox.local", "tok")

    def test_format_returns_expected_keys(self, mock_netbox_device):
        client = self._make_client()
        result = client._format_device_data(mock_netbox_device)
        expected_keys = {"name", "primary_ip", "description", "snmp_community",
                         "site", "latitude", "longitude", "location",
                         "manufacturer", "model", "platform", "role", "status"}
        assert expected_keys.issubset(result.keys())

    def test_format_extracts_name(self, mock_netbox_device):
        client = self._make_client()
        result = client._format_device_data(mock_netbox_device)
        assert result["name"] == "test-router-01"

    def test_format_strips_cidr_from_primary_ip(self, mock_netbox_device):
        client = self._make_client()
        result = client._format_device_data(mock_netbox_device)
        assert "/" not in result["primary_ip"]
        assert result["primary_ip"] == "192.168.1.100"

    def test_format_handles_none_primary_ip(self, mock_netbox_device):
        mock_netbox_device.primary_ip = None
        client = self._make_client()
        result = client._format_device_data(mock_netbox_device)
        assert result["primary_ip"] is None

    def test_format_handles_none_site(self, mock_netbox_device):
        mock_netbox_device.site = None
        client = self._make_client()
        result = client._format_device_data(mock_netbox_device)
        assert result["site"] is None
        assert result["latitude"] is None


class TestNetBoxClientGetDevices:
    def _make_client(self, devices=None):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "tok")
        if devices:
            client.conn.dcim.devices.filter.return_value = devices
        else:
            client.conn.dcim.devices.filter.return_value = []
        return client

    def test_get_devices_returns_list(self, mock_netbox_device):
        client = self._make_client([mock_netbox_device])
        with patch.object(client, "_format_device_data", return_value={"name": "test-router-01"}):
            result = client.get_devices()
        assert isinstance(result, list)

    def test_get_device_by_name_returns_formatted(self, mock_netbox_device):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "tok")
        client.conn.dcim.devices.get.return_value = mock_netbox_device
        with patch.object(client, "_format_device_data", return_value={"name": "test-router-01"}):
            result = client.get_device_by_name("test-router-01")
        assert result["name"] == "test-router-01"

    def test_get_device_by_name_not_found(self):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "tok")
        client.conn.dcim.devices.get.return_value = None
        result = client.get_device_by_name("nonexistent")
        assert result is None

    def test_get_custom_field(self, mock_netbox_device):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "tok")
        result = client.get_device_custom_field(mock_netbox_device, "SNMPCommunity")
        assert result == "public"

    def test_get_custom_field_missing_returns_default(self, mock_netbox_device):
        with patch("sync_devices_from_netbox.NetboxAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = NetBoxClient("http://netbox.local", "tok")
        result = client.get_device_custom_field(mock_netbox_device, "NonExistent", default="fallback")
        assert result == "fallback"


# ---------------------------------------------------------------------------
# ZabbixClient
# ---------------------------------------------------------------------------


class TestZabbixClientInit:
    def test_init_logs_in_with_token(self):
        with patch("sync_devices_from_netbox.ZabbixAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            client = ZabbixClient("http://zabbix.local", "my-api-token")
        conn.login.assert_called_once_with(token="my-api-token")


class TestZabbixClientHostExists:
    def _make_client(self):
        with patch("sync_devices_from_netbox.ZabbixAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            return ZabbixClient("http://zabbix.local", "tok")

    def test_returns_true_when_host_exists(self):
        client = self._make_client()
        client.conn.host.get.return_value = [{"hostid": "10001", "host": "router"}]
        assert client.host_exists("router") is True

    def test_returns_false_when_host_not_found(self):
        client = self._make_client()
        client.conn.host.get.return_value = []
        assert client.host_exists("nonexistent") is False


class TestZabbixClientCreateHost:
    def _make_client(self):
        with patch("sync_devices_from_netbox.ZabbixAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            return ZabbixClient("http://zabbix.local", "tok")

    def test_create_host_calls_api(self):
        client = self._make_client()
        client.conn.hostgroup.get.return_value = [{"groupid": "5", "name": "Network"}]
        client.conn.host.create.return_value = {"hostids": ["10001"]}
        host_data = {
            "name": "router-01",
            "primary_ip": "192.168.1.1",
            "description": "Router",
        }
        result = client.create_host(host_data, "Network")
        client.conn.host.create.assert_called_once()

    def test_create_host_creates_group_when_missing(self):
        client = self._make_client()
        client.conn.hostgroup.get.return_value = []
        client.conn.hostgroup.create.return_value = {"groupid": "99", "name": "New Group"}
        client.conn.host.create.return_value = {"hostids": ["10001"]}
        host_data = {"name": "router", "primary_ip": "10.0.0.1", "description": ""}
        client.create_host(host_data, "New Group")
        client.conn.hostgroup.create.assert_called_once_with(name="New Group")

    def test_update_host_calls_api(self):
        client = self._make_client()
        client.conn.host.update.return_value = {"hostids": ["10001"]}
        client.update_host("10001", {"name": "router", "description": "Updated"})
        client.conn.host.update.assert_called_once()

    def test_delete_host_calls_api(self):
        client = self._make_client()
        client.conn.host.delete.return_value = {"hostids": ["10001"]}
        client.delete_host("10001")
        client.conn.host.delete.assert_called_once_with("10001")


class TestZabbixClientInterfaces:
    def _make_client(self):
        with patch("sync_devices_from_netbox.ZabbixAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            return ZabbixClient("http://zabbix.local", "tok")

    @pytest.mark.parametrize("monitoring_type,expected_type", [
        ("SNMP v2", 2),
        ("SNMP v1", 2),
        ("SNMP v3", 2),
        ("IPMI", 3),
        ("JMX", 4),
        ("Agent", 1),
        (None, 2),
        ("unknown_type", 2),
    ])
    def test_create_interface_types(self, monitoring_type, expected_type):
        client = self._make_client()
        ifaces = client._create_interface("192.168.1.1", "public", monitoring_type)
        assert ifaces[0]["type"] == expected_type

    def test_empty_ip_returns_empty_list(self):
        client = self._make_client()
        result = client._create_interface(None, "public", None)
        assert result == []

    def test_snmp_v1_interface(self):
        client = self._make_client()
        ifaces = client._create_interface("192.168.1.1", "public", "SNMP v1")
        assert ifaces[0]["details"]["version"] == 1

    def test_snmp_v3_interface(self):
        client = self._make_client()
        ifaces = client._create_interface("192.168.1.1", "public", "SNMP v3")
        assert ifaces[0]["details"]["version"] == 3


class TestZabbixClientTemplateAndInventory:
    def _make_client(self):
        with patch("sync_devices_from_netbox.ZabbixAPI") as MockAPI:
            conn = MagicMock()
            MockAPI.return_value = conn
            return ZabbixClient("http://zabbix.local", "tok")

    def test_get_template_id_by_name_found(self):
        client = self._make_client()
        client.conn.template.get.return_value = [{"templateid": "10563", "name": "Generic SNMP"}]
        result = client.get_template_id_by_name("Generic SNMP")
        assert result == "10563"

    def test_get_template_id_by_name_not_found(self):
        client = self._make_client()
        client.conn.template.get.return_value = []
        result = client.get_template_id_by_name("nonexistent")
        assert result is None

    def test_set_inventory_mode(self):
        client = self._make_client()
        client.conn.host.update.return_value = {"hostids": ["1"]}
        client.set_inventory_mode("1", mode=1)
        client.conn.host.update.assert_called_once()

    def test_update_host_inventory_field(self):
        client = self._make_client()
        client.conn.host.update.return_value = {"hostids": ["1"]}
        client.update_host_inventory_field("1", "location_lat", "40.71")
        call_arg = client.conn.host.update.call_args[0][0]
        assert call_arg["inventory"]["location_lat"] == "40.71"

    def test_assign_template_to_host(self):
        client = self._make_client()
        client.conn.host.update.return_value = {"hostids": ["1"]}
        client.assign_template_to_host("1", "10563")
        call_arg = client.conn.host.update.call_args[0][0]
        assert {"templateid": "10563"} in call_arg["templates"]


# ---------------------------------------------------------------------------
# NetboxZabbixSync
# ---------------------------------------------------------------------------


class TestNetboxZabbixSync:
    def _make_sync(self):
        config = {
            "netbox_url": "http://netbox.local",
            "netbox_token": "nb-tok",
            "zabbix_url": "http://zabbix.local",
            "zabbix_token": "zb-tok",
            "zabbix_group": "Network Devices",
            "zabbix_template_id": "10563",
        }
        with patch("sync_devices_from_netbox.NetboxAPI"), \
             patch("sync_devices_from_netbox.ZabbixAPI"):
            sync = NetboxZabbixSync(config)
        sync.netbox_client = MagicMock()
        sync.zabbix_client = MagicMock()
        return sync

    def _full_device(self, **overrides):
        base = {
            "name": "router-01", "primary_ip": "192.168.1.1",
            "description": "", "snmp_community": "public",
            "site": "Main", "latitude": None, "longitude": None,
            "location": "Rack A", "manufacturer": "Cisco", "model": "ISR4321",
            "platform": "ios", "role": "Router", "status": "Active",
        }
        base.update(overrides)
        return base

    def test_sync_device_creates_when_not_exists(self):
        sync = self._make_sync()
        device = self._full_device()
        sync.netbox_client.get_device_by_name.return_value = device
        sync.zabbix_client.host_exists.return_value = False
        sync.zabbix_client.conn.host.get.return_value = [{"hostid": "10001"}]
        sync.netbox_client.conn.dcim.device_types.get.return_value = None

        sync.sync_device("router-01")
        sync.zabbix_client.create_host.assert_called_once()

    def test_sync_device_updates_when_exists(self):
        sync = self._make_sync()
        device = self._full_device()
        sync.netbox_client.get_device_by_name.return_value = device
        sync.zabbix_client.host_exists.return_value = True
        sync.zabbix_client.conn.host.get.return_value = [{"hostid": "10001"}]
        sync.netbox_client.conn.dcim.device_types.get.return_value = None

        sync.sync_device("router-01")
        sync.zabbix_client.update_host.assert_called_once()

    def test_sync_device_skips_when_not_in_netbox(self, capsys):
        sync = self._make_sync()
        sync.netbox_client.get_device_by_name.return_value = None
        sync.sync_device("nonexistent")
        sync.zabbix_client.create_host.assert_not_called()
        sync.zabbix_client.update_host.assert_not_called()

    def test_sync_all_devices(self):
        sync = self._make_sync()
        sync.netbox_client.get_devices.return_value = [
            {"name": "r1"}, {"name": "r2"}
        ]
        with patch.object(sync, "sync_device") as mock_sync:
            sync.sync_all_devices()
        assert mock_sync.call_count == 2

    def test_sync_devices_by_platform(self):
        sync = self._make_sync()
        sync.netbox_client.get_devices_by_platform.return_value = [{"name": "r1"}]
        with patch.object(sync, "sync_device") as mock_sync:
            sync.sync_devices_by_platform("cisco-ios")
        mock_sync.assert_called_once_with("r1")

    def test_delete_device_calls_delete_host(self):
        sync = self._make_sync()
        device = {"name": "router-01", "primary_ip": "192.168.1.1"}
        sync.netbox_client.get_device_by_name.return_value = device
        sync.zabbix_client.conn.host.get.return_value = [{"hostid": "10001"}]
        sync.delete_device("router-01")
        sync.zabbix_client.delete_host.assert_called_once_with("10001")

    def test_delete_device_skips_when_not_in_netbox(self, capsys):
        sync = self._make_sync()
        sync.netbox_client.get_device_by_name.return_value = None
        sync.delete_device("nonexistent")
        sync.zabbix_client.delete_host.assert_not_called()

    def test_delete_device_skips_when_not_in_zabbix(self, capsys):
        sync = self._make_sync()
        device = {"name": "router-01", "primary_ip": "192.168.1.1"}
        sync.netbox_client.get_device_by_name.return_value = device
        sync.zabbix_client.conn.host.get.return_value = []
        sync.delete_device("router-01")
        sync.zabbix_client.delete_host.assert_not_called()

    def test_assign_tags_to_host(self):
        sync = self._make_sync()
        device = {
            "name": "r1", "site": "Main", "location": "Rack A",
            "manufacturer": "Cisco", "model": "ISR4321",
            "platform": "ios", "role": "Router", "status": "Active",
        }
        sync._assign_tags_to_host(device, "10001")
        sync.zabbix_client.assign_tags_to_host.assert_called_once()
        tags = sync.zabbix_client.assign_tags_to_host.call_args[0][1]
        tag_names = [t["tag"] for t in tags]
        assert "site" in tag_names
        assert "vendor" in tag_names
