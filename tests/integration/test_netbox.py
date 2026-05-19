"""
Integration tests for NetBox connectivity.

Requires:
    NETBOX_URL=https://netbox.example.com
    NETBOX_TOKEN=<token>

Run:
    make test-integration
    # or just NetBox:
    pytest tests/integration/test_netbox.py -v -m integration
"""

import pytest


pytestmark = pytest.mark.integration


class TestNetBoxConnectivity:
    def test_api_is_reachable(self, nb_client):
        """NetBox API status endpoint returns a valid version string."""
        status = nb_client.status()
        assert "netbox-version" in status

    def test_list_devices_returns_list(self, nb_client):
        """dcim.devices.all() returns an iterable (may be empty on a fresh install)."""
        devices = list(nb_client.dcim.devices.all())
        assert isinstance(devices, list)

    def test_list_ip_ranges_returns_list(self, nb_client):
        """ipam.ip_ranges.all() returns an iterable."""
        ranges = list(nb_client.ipam.ip_ranges.all())
        assert isinstance(ranges, list)

    def test_list_prefixes_returns_list(self, nb_client):
        """ipam.prefixes.all() returns an iterable."""
        prefixes = list(nb_client.ipam.prefixes.all())
        assert isinstance(prefixes, list)

    def test_list_sites_returns_list(self, nb_client):
        """dcim.sites.all() returns an iterable."""
        sites = list(nb_client.dcim.sites.all())
        assert isinstance(sites, list)


class TestNetBoxDeviceLookup:
    def test_filter_devices_by_status(self, nb_client):
        """Filter active devices — result is a list (may be empty)."""
        active = list(nb_client.dcim.devices.filter(status="active"))
        assert isinstance(active, list)

    def test_get_nonexistent_device_returns_none(self, nb_client):
        """Looking up a device name that cannot exist returns None."""
        result = nb_client.dcim.devices.get(name="__nonexistent_device_xyz__")
        assert result is None

    def test_filter_ip_ranges_returns_list(self, nb_client):
        """ipam.ip_ranges.filter() with no filters returns an iterable."""
        ranges = list(nb_client.ipam.ip_ranges.filter())
        assert isinstance(ranges, list)


class TestNetBoxCustomFields:
    def test_devices_have_expected_structure(self, nb_client):
        """Each device returned has at minimum a name and id attribute."""
        for device in nb_client.dcim.devices.all():
            assert hasattr(device, "id")
            assert hasattr(device, "name")
            break  # only check the first device
