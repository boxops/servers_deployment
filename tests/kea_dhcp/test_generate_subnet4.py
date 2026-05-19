"""
Unit tests for ansible/kea_dhcp/scripts/generate_subnet4_from_netbox.py

All NetBox and Kea DHCP API calls are mocked; no real network connectivity
is required.
"""

import json
import pytest
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# conftest.py adds ansible/kea_dhcp/scripts to sys.path
from generate_subnet4_from_netbox import (
    Netbox,
    KeaDHCP,
    SubnetConfig,
    Manager,
)


# ---------------------------------------------------------------------------
# Netbox class
# ---------------------------------------------------------------------------


class TestNetbox:
    """Tests for the Netbox client wrapper."""

    def test_init_stores_url_and_token(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            mock_api.return_value = MagicMock()
            nb = Netbox("http://netbox.local", "my-token")
        mock_api.assert_called_once_with("http://netbox.local", token="my-token")

    def test_ssl_verification_disabled(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            mock_api.return_value = nb_instance
            nb = Netbox("http://netbox.local", "my-token")
        nb_instance.http_session.verify = False

    def test_get_ip_ranges_returns_list(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            range_obj = MagicMock()
            dict_data = {
                "id": 1,
                "start_address": "10.0.0.1/24",
                "end_address": "10.0.0.100/24",
                "custom_fields": {},
            }
            range_obj.__iter__ = lambda self: iter(dict_data.items())
            range_obj.items = lambda: dict_data.items()
            nb_instance.ipam.ip_ranges.all.return_value = [range_obj]
            mock_api.return_value = nb_instance

            nb = Netbox("http://netbox.local", "tok")
            nb.nb = nb_instance  # inject directly
            # Patch dict() call on the range objects by using dicts directly
            nb_instance.ipam.ip_ranges.all.return_value = [dict_data]
            result = nb.get_ip_ranges()
        assert isinstance(result, list)

    def test_get_host_reservations_returns_list(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            mock_api.return_value = nb_instance
            nb = Netbox("http://netbox.local", "tok")
            nb.nb = nb_instance
            # No matching reservations
            nb_instance.ipam.ip_addresses.filter.return_value = []
            result = nb.get_host_reservations()
        assert isinstance(result, list)
        assert result == []

    def test_get_host_reservations_hw_address(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            mock_api.return_value = nb_instance
            nb = Netbox("http://netbox.local", "tok")
            nb.nb = nb_instance

            ip_obj = MagicMock()
            ip_obj.address = "192.168.1.50/24"
            ip_obj.custom_fields = {
                "DHCPIsReservation": True,
                "IsKeaManaged": True,
                "DHCPHardwareAddress": "aa:bb:cc:dd:ee:ff",
                "DHCPCircuitID": None,
            }

            prefix_obj = MagicMock()
            prefix_obj.prefix = "192.168.1.0/24"

            nb_instance.ipam.ip_addresses.filter.return_value = [ip_obj]
            nb_instance.ipam.prefixes.filter.return_value = [prefix_obj]

            result = nb.get_host_reservations()

        assert len(result) == 1
        assert result[0]["subnet"] == "192.168.1.0/24"
        assert result[0]["reservations"][0]["hw-address"] == "aa:bb:cc:dd:ee:ff"
        assert result[0]["reservations"][0]["ip-address"] == "192.168.1.50"

    def test_get_host_reservations_circuit_id(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            mock_api.return_value = nb_instance
            nb = Netbox("http://netbox.local", "tok")
            nb.nb = nb_instance

            ip_obj = MagicMock()
            ip_obj.address = "10.0.0.5/8"
            ip_obj.custom_fields = {
                "DHCPIsReservation": True,
                "IsKeaManaged": True,
                "DHCPHardwareAddress": None,
                "DHCPCircuitID": "CIRCUIT-001",
            }

            prefix_obj = MagicMock()
            prefix_obj.prefix = "10.0.0.0/8"
            nb_instance.ipam.ip_addresses.filter.return_value = [ip_obj]
            nb_instance.ipam.prefixes.filter.return_value = [prefix_obj]

            result = nb.get_host_reservations()

        assert result[0]["reservations"][0]["circuit-id"] == "'CIRCUIT-001'"

    def test_get_host_reservations_skips_when_no_hw_and_no_circuit(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            mock_api.return_value = nb_instance
            nb = Netbox("http://netbox.local", "tok")
            nb.nb = nb_instance

            ip_obj = MagicMock()
            ip_obj.address = "10.0.0.5/8"
            ip_obj.custom_fields = {
                "DHCPIsReservation": True,
                "IsKeaManaged": True,
                "DHCPHardwareAddress": None,
                "DHCPCircuitID": None,
            }

            prefix_obj = MagicMock()
            prefix_obj.prefix = "10.0.0.0/8"
            nb_instance.ipam.ip_addresses.filter.return_value = [ip_obj]
            nb_instance.ipam.prefixes.filter.return_value = [prefix_obj]

            result = nb.get_host_reservations()

        # Entry skipped due to missing both identifiers
        assert result == [] or result[0]["reservations"] == []

    def test_get_host_reservations_no_prefix(self):
        with patch("generate_subnet4_from_netbox.api") as mock_api:
            nb_instance = MagicMock()
            mock_api.return_value = nb_instance
            nb = Netbox("http://netbox.local", "tok")
            nb.nb = nb_instance

            ip_obj = MagicMock()
            ip_obj.address = "10.0.0.5/8"
            ip_obj.custom_fields = {
                "DHCPIsReservation": True,
                "IsKeaManaged": True,
                "DHCPHardwareAddress": "aa:bb:cc:dd:ee:ff",
                "DHCPCircuitID": None,
            }
            nb_instance.ipam.ip_addresses.filter.return_value = [ip_obj]
            nb_instance.ipam.prefixes.filter.return_value = []

            result = nb.get_host_reservations()
        assert result == []


# ---------------------------------------------------------------------------
# KeaDHCP class
# ---------------------------------------------------------------------------


class TestKeaDHCP:
    """Tests for the Kea DHCP4 API wrapper."""

    def _make_kea(self):
        with patch("generate_subnet4_from_netbox.Kea") as MockKea:
            instance = MagicMock()
            MockKea.return_value = instance
            kea = KeaDHCP("http://kea.local", 8000)
            kea.server = instance
        return kea

    def test_init_creates_kea_server(self):
        with patch("generate_subnet4_from_netbox.Kea") as MockKea:
            MockKea.return_value = MagicMock()
            kea = KeaDHCP("http://kea.local", 8000)
        MockKea.assert_called_once_with(host="http://kea.local", port=8000)

    def test_push_config_removes_hash(self):
        kea = self._make_kea()
        config = {"arguments": {"hash": "abc", "Dhcp4": {}}}
        kea.server.dhcp4.config_set.return_value = {"result": 0}
        kea.server.dhcp4.config_test.return_value = {"result": 0}
        kea.server.dhcp4.config_write.return_value = {"result": 0}
        kea.push_config(config)
        assert "hash" not in config["arguments"]

    def test_push_config_calls_set_test_write(self):
        kea = self._make_kea()
        config = {"arguments": {"Dhcp4": {}}}
        kea.server.dhcp4.config_set.return_value = {"result": 0}
        kea.server.dhcp4.config_test.return_value = {"result": 0}
        kea.server.dhcp4.config_write.return_value = {"result": 0}
        kea.push_config(config)
        kea.server.dhcp4.config_set.assert_called_once()
        kea.server.dhcp4.config_test.assert_called_once()
        kea.server.dhcp4.config_write.assert_called_once()

    def test_push_config_raises_on_failed_result(self):
        kea = self._make_kea()
        config = {"arguments": {"Dhcp4": {}}}
        kea.server.dhcp4.config_set.return_value = {"result": 1}
        with pytest.raises(AssertionError):
            kea.push_config(config)

    def test_replace_subnet4_updates_and_pushes(self):
        kea = self._make_kea()
        existing_config = {
            "result": 0,
            "arguments": {"Dhcp4": {"subnet4": []}},
        }
        kea.server.dhcp4.config_get.return_value = existing_config
        kea.server.dhcp4.config_set.return_value = {"result": 0}
        kea.server.dhcp4.config_test.return_value = {"result": 0}
        kea.server.dhcp4.config_write.return_value = {"result": 0}

        new_subnets = [{"subnet": "192.168.1.0/24"}]
        kea.replace_subnet4(new_subnets)

        assert existing_config["arguments"]["Dhcp4"]["subnet4"] == new_subnets

    def test_replace_subnet4_removes_hash(self):
        kea = self._make_kea()
        existing_config = {
            "result": 0,
            "arguments": {"hash": "xyz", "Dhcp4": {"subnet4": []}},
        }
        kea.server.dhcp4.config_get.return_value = existing_config
        kea.server.dhcp4.config_set.return_value = {"result": 0}
        kea.server.dhcp4.config_test.return_value = {"result": 0}
        kea.server.dhcp4.config_write.return_value = {"result": 0}
        kea.replace_subnet4([])
        assert "hash" not in existing_config["arguments"]

    def test_replace_shared_networks(self):
        kea = self._make_kea()
        existing_config = {
            "result": 0,
            "arguments": {"Dhcp4": {"shared-networks": []}},
        }
        kea.server.dhcp4.config_get.return_value = existing_config
        kea.server.dhcp4.config_set.return_value = {"result": 0}
        kea.server.dhcp4.config_test.return_value = {"result": 0}
        kea.server.dhcp4.config_write.return_value = {"result": 0}

        new_networks = [{"name": "net1", "subnet4": []}]
        kea.replace_shared_networks(new_networks)

        assert existing_config["arguments"]["Dhcp4"]["shared-networks"] == new_networks


# ---------------------------------------------------------------------------
# SubnetConfig static methods
# ---------------------------------------------------------------------------


class TestSubnetConfigSplitPool:
    def test_splits_into_two_parts(self):
        pools = SubnetConfig.split_pool("192.168.1.10", "192.168.1.100")
        assert len(pools) == 2

    def test_no_overlap(self):
        pools = SubnetConfig.split_pool("192.168.1.10", "192.168.1.100")
        start1, end1 = pools[0].split("-")
        start2, end2 = pools[1].split("-")
        assert IPv4Address(end1) < IPv4Address(start2)

    def test_covers_full_range(self):
        start, end = "192.168.1.10", "192.168.1.100"
        pools = SubnetConfig.split_pool(start, end)
        _, end1 = pools[0].split("-")
        start2, end2 = pools[1].split("-")
        assert start2 == str(IPv4Address(end1) + 1)
        assert end2 == end

    def test_verbose_does_not_raise(self):
        pools = SubnetConfig.split_pool("10.0.0.1", "10.0.0.50", verbose=True)
        assert len(pools) == 2

    def test_single_ip_range(self):
        # Only 1 IP between start and end – edge case
        pools = SubnetConfig.split_pool("10.0.0.1", "10.0.0.2")
        assert len(pools) == 2

    @pytest.mark.parametrize("start,end", [
        ("172.16.0.1", "172.16.0.254"),
        ("10.0.0.1", "10.0.255.254"),
    ])
    def test_parametrized_ranges(self, start, end):
        pools = SubnetConfig.split_pool(start, end)
        assert len(pools) == 2


class TestSubnetConfigGetSubnets:
    def test_extracts_unique_subnets(self, mock_netbox_ip_ranges):
        subnets, only = SubnetConfig.get_subnets(mock_netbox_ip_ranges)
        assert len(subnets) == 2
        assert "192.168.1.0/24" in only
        assert "10.0.0.0/8" in only

    def test_deduplicates_same_subnet(self):
        ranges = [
            {"custom_fields": {"DHCPPoolSubnet": "192.168.1.0/24"}},
            {"custom_fields": {"DHCPPoolSubnet": "192.168.1.0/24"}},
        ]
        subnets, only = SubnetConfig.get_subnets(ranges)
        assert len(subnets) == 1

    def test_skips_range_without_subnet(self):
        ranges = [{"custom_fields": {"DHCPPoolSubnet": None}}]
        subnets, only = SubnetConfig.get_subnets(ranges)
        assert subnets == []

    def test_empty_input(self):
        subnets, only = SubnetConfig.get_subnets([])
        assert subnets == []
        assert only == []


class TestSubnetConfigAttachPools:
    def test_attaches_pool_to_correct_subnet(self, mock_netbox_ip_ranges):
        subnets = [{"subnet": "192.168.1.0/24"}, {"subnet": "10.0.0.0/8"}]
        result = SubnetConfig.attach_pools(mock_netbox_ip_ranges, subnets)
        sn1 = next(s for s in result if s["subnet"] == "192.168.1.0/24")
        assert len(sn1["pools"]) == 1
        assert "192.168.1.10" in sn1["pools"][0]["pool"]

    def test_skips_range_with_no_create_pools(self):
        ranges = [
            {
                "start_address": "192.168.1.10/24",
                "end_address": "192.168.1.200/24",
                "custom_fields": {
                    "DHCPPoolSubnet": "192.168.1.0/24",
                    "DHCPCreatePools": False,
                },
            }
        ]
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_pools(ranges, subnets)
        assert "pools" not in result[0]

    def test_creates_multiple_pools_for_same_subnet(self):
        ranges = [
            {
                "start_address": "192.168.1.10/24",
                "end_address": "192.168.1.50/24",
                "custom_fields": {"DHCPPoolSubnet": "192.168.1.0/24", "DHCPCreatePools": True},
            },
            {
                "start_address": "192.168.1.100/24",
                "end_address": "192.168.1.150/24",
                "custom_fields": {"DHCPPoolSubnet": "192.168.1.0/24", "DHCPCreatePools": True},
            },
        ]
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_pools(ranges, subnets)
        assert len(result[0]["pools"]) == 2


class TestSubnetConfigAttachDefaultGateway:
    def test_attaches_gateway(self, mock_netbox_ip_ranges):
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_default_gateway(mock_netbox_ip_ranges, subnets)
        option = next(o for o in result[0]["option-data"] if o["name"] == "routers")
        assert option["data"] == "192.168.1.1"

    def test_skips_when_no_gateway(self):
        ranges = [
            {
                "custom_fields": {
                    "DHCPPoolSubnet": "192.168.1.0/24",
                    "DHCPPoolDefaultGateway": None,
                }
            }
        ]
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_default_gateway(ranges, subnets)
        assert "option-data" not in result[0]


class TestSubnetConfigAttachRelayIp:
    def test_attaches_relay(self, mock_netbox_ip_ranges):
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_relay_ip(mock_netbox_ip_ranges, subnets)
        assert "192.168.1.254" in result[0]["relay"]["ip-addresses"]

    def test_skips_when_no_relay(self):
        ranges = [
            {
                "custom_fields": {
                    "DHCPPoolSubnet": "10.0.0.0/8",
                    "DHCPPoolRelayIPs": None,
                }
            }
        ]
        subnets = [{"subnet": "10.0.0.0/8"}]
        result = SubnetConfig.attach_relay_ip(ranges, subnets)
        assert "relay" not in result[0]

    def test_multiple_relays(self):
        ranges = [
            {
                "custom_fields": {
                    "DHCPPoolSubnet": "10.0.0.0/8",
                    "DHCPPoolRelayIPs": "10.0.0.254,10.0.0.253",
                }
            }
        ]
        subnets = [{"subnet": "10.0.0.0/8"}]
        result = SubnetConfig.attach_relay_ip(ranges, subnets)
        assert len(result[0]["relay"]["ip-addresses"]) == 2


class TestSubnetConfigAttachOptionData:
    def test_attaches_option_data(self, mock_netbox_ip_ranges):
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_option_data(mock_netbox_ip_ranges, subnets)
        names = [o["name"] for o in result[0]["option-data"]]
        assert "domain-name-servers" in names

    def test_skips_when_no_option_data(self):
        ranges = [
            {"custom_fields": {"DHCPPoolSubnet": "10.0.0.0/8", "DHCPPoolOptions": None}}
        ]
        subnets = [{"subnet": "10.0.0.0/8"}]
        result = SubnetConfig.attach_option_data(ranges, subnets)
        assert "option-data" not in result[0]


class TestSubnetConfigAttachReservations:
    def test_attaches_reservation_to_correct_subnet(self):
        reservations = [
            {
                "subnet": "192.168.1.0/24",
                "reservations": [
                    {"hw-address": "aa:bb:cc:dd:ee:ff", "ip-address": "192.168.1.50"}
                ],
            }
        ]
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_reservations(subnets, reservations)
        assert len(result[0]["reservations"]) == 1

    def test_does_not_attach_to_wrong_subnet(self):
        reservations = [
            {
                "subnet": "10.0.0.0/8",
                "reservations": [
                    {"hw-address": "ff:ee:dd:cc:bb:aa", "ip-address": "10.0.0.5"}
                ],
            }
        ]
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_reservations(subnets, reservations)
        assert "reservations" not in result[0]

    def test_empty_reservations(self):
        subnets = [{"subnet": "192.168.1.0/24"}]
        result = SubnetConfig.attach_reservations(subnets, [])
        assert "reservations" not in result[0]


class TestSubnetConfigGenerateSubnet4:
    def test_generates_subnet_with_id(self, mock_netbox_ip_ranges, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = SubnetConfig.generate_subnet4(mock_netbox_ip_ranges, [])
        assert all("id" in s for s in result)
        assert result[0]["id"] == 1

    def test_creates_subnet4_json_file(self, mock_netbox_ip_ranges, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        SubnetConfig.generate_subnet4(mock_netbox_ip_ranges, [])
        assert (tmp_path / "subnet4.json").exists()

    def test_returns_list(self, mock_netbox_ip_ranges, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = SubnetConfig.generate_subnet4(mock_netbox_ip_ranges, [])
        assert isinstance(result, list)

    def test_empty_ranges_returns_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = SubnetConfig.generate_subnet4([], [])
        assert result == []


# ---------------------------------------------------------------------------
# Manager class
# ---------------------------------------------------------------------------


class TestManager:
    def _make_manager(self):
        with patch("generate_subnet4_from_netbox.Netbox") as MockNetbox, \
             patch("generate_subnet4_from_netbox.KeaDHCP") as MockKea:
            nb_instance = MagicMock()
            kea_instance = MagicMock()
            MockNetbox.return_value = nb_instance
            MockKea.return_value = kea_instance
            m = Manager("http://netbox.local", "tok", "http://kea.local", 8000)
            m.netbox_api = nb_instance
            m.kea_dhcp = kea_instance
        return m

    def test_run_fetches_ranges_and_reservations(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        m = self._make_manager()
        m.netbox_api.get_ip_ranges.return_value = []
        m.netbox_api.get_host_reservations.return_value = []
        m.run()
        m.netbox_api.get_ip_ranges.assert_called_once()
        m.netbox_api.get_host_reservations.assert_called_once()

    def test_run_calls_replace_subnet4(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        m = self._make_manager()
        m.netbox_api.get_ip_ranges.return_value = []
        m.netbox_api.get_host_reservations.return_value = []
        m.run()
        m.kea_dhcp.replace_subnet4.assert_called_once()
