"""
Integration tests for Zabbix connectivity.

Requires:
    ZABBIX_URL=https://zabbix.example.com
    ZABBIX_TOKEN=<api-token>

Run:
    make test-integration
    # or just Zabbix:
    pytest tests/integration/test_zabbix.py -v -m integration
"""

import pytest


pytestmark = pytest.mark.integration


class TestZabbixConnectivity:
    def test_api_info_returns_version(self, zbx_client):
        """apiinfo.version() returns a non-empty version string."""
        version = zbx_client.apiinfo.version()
        assert version
        assert "." in version  # e.g. "7.0.0"

    def test_list_hosts_returns_list(self, zbx_client):
        """host.get() returns a list (may be empty on a fresh install)."""
        hosts = zbx_client.host.get(output=["hostid", "host"])
        assert isinstance(hosts, list)

    def test_list_templates_returns_list(self, zbx_client):
        """template.get() returns a list."""
        templates = zbx_client.template.get(output=["templateid", "name"])
        assert isinstance(templates, list)

    def test_list_host_groups_returns_list(self, zbx_client):
        """hostgroup.get() returns a list."""
        groups = zbx_client.hostgroup.get(output=["groupid", "name"])
        assert isinstance(groups, list)


class TestZabbixHostLookup:
    def test_host_exists_false_for_nonexistent(self, zbx_client):
        """Searching for a host that cannot exist returns an empty list."""
        result = zbx_client.host.get(
            filter={"host": "__nonexistent_host_xyz__"},
            output=["hostid"],
        )
        assert result == []

    def test_get_template_by_name_returns_list(self, zbx_client):
        """template.get with a name search returns a list."""
        result = zbx_client.template.get(
            search={"name": "Linux"},
            output=["templateid", "name"],
        )
        assert isinstance(result, list)


class TestZabbixHostStructure:
    def test_hosts_have_expected_fields(self, zbx_client):
        """Every returned host has hostid and host fields."""
        hosts = zbx_client.host.get(
            output=["hostid", "host"],
            limit=1,
        )
        if hosts:
            assert "hostid" in hosts[0]
            assert "host" in hosts[0]

    def test_templates_have_expected_fields(self, zbx_client):
        """Every returned template has templateid and name fields."""
        templates = zbx_client.template.get(
            output=["templateid", "name"],
            limit=1,
        )
        if templates:
            assert "templateid" in templates[0]
            assert "name" in templates[0]
