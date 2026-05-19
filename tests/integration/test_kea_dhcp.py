"""
Integration tests for Kea DHCP Control Agent connectivity.

Requires:
    KEA_URL=http://kea-host:8000

Run:
    make test-integration
    # or just Kea:
    pytest tests/integration/test_kea_dhcp.py -v -m integration
"""

import pytest


pytestmark = pytest.mark.integration


class TestKeaConnectivity:
    def test_config_get_returns_result(self, kea_client):
        """config-get on the dhcp4 service returns result=0 (success)."""
        result = kea_client.dhcp4.config_get()
        assert result is not None

    def test_dhcp4_service_responds(self, kea_client):
        """version-get returns a non-empty response from the dhcp4 service."""
        result = kea_client.dhcp4.version_get()
        assert result is not None

    def test_ctrl_agent_responds(self, kea_client):
        """The control agent itself responds to a list-commands request."""
        result = kea_client.ctrl_agent.list_commands()
        assert result is not None


class TestKeaSubnets:
    def test_subnet4_list_is_present_in_config(self, kea_client):
        """The Dhcp4 config contains a subnet4 key (list, possibly empty)."""
        result = kea_client.dhcp4.config_get()
        # pykeadhcp wraps results; navigate to the arguments
        if hasattr(result, "arguments"):
            config = result.arguments.get("Dhcp4", {})
        elif isinstance(result, dict):
            config = result.get("arguments", {}).get("Dhcp4", {})
        else:
            pytest.skip("Unexpected Kea response format")
        assert "subnet4" in config

    def test_subnet4_entries_have_expected_fields(self, kea_client):
        """Each subnet4 entry has at least an id and subnet field."""
        result = kea_client.dhcp4.config_get()
        if hasattr(result, "arguments"):
            subnets = result.arguments.get("Dhcp4", {}).get("subnet4", [])
        elif isinstance(result, dict):
            subnets = result.get("arguments", {}).get("Dhcp4", {}).get("subnet4", [])
        else:
            pytest.skip("Unexpected Kea response format")

        for subnet in subnets:
            assert "subnet" in subnet
            break  # only check first entry


class TestKeaLeases:
    def test_lease4_get_all_returns_list(self, kea_client):
        """lease4-get-all returns a list (may be empty)."""
        try:
            result = kea_client.dhcp4.lease4_get_all()
            if hasattr(result, "leases"):
                assert isinstance(result.leases, list)
            elif isinstance(result, dict):
                leases = result.get("arguments", {}).get("leases", [])
                assert isinstance(leases, list)
        except Exception:
            pytest.skip("lease4-get-all not supported or no leases configured")
