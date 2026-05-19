"""
Unit tests for ansible/zabbix/scripts/export_host_templates.py

All Zabbix API calls are mocked via unittest.mock.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call, mock_open

# conftest.py adds ansible/zabbix/scripts to sys.path
from export_host_templates import ZabbixTemplateExporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_exporter(url="http://zabbix.local", token="my-token", output_dir="out"):
    with patch("export_host_templates.ZabbixAPI"), \
         patch("export_host_templates.ssl"), \
         patch("export_host_templates.requests"):
        return ZabbixTemplateExporter(url, token, output_dir)


# ---------------------------------------------------------------------------
# __init__ / SSL configuration
# ---------------------------------------------------------------------------


class TestZabbixTemplateExporterInit:
    def test_stores_url_token_dir(self):
        exporter = _make_exporter("http://zabbix.local", "tok123", "templates")
        assert exporter.url == "http://zabbix.local"
        assert exporter.token == "tok123"
        assert exporter.output_dir == "templates"

    def test_api_starts_as_none(self):
        exporter = _make_exporter()
        assert exporter.api is None

    def test_ssl_configuration_called(self):
        with patch("export_host_templates.ZabbixAPI"), \
             patch("export_host_templates.ssl") as mock_ssl, \
             patch("export_host_templates.requests") as mock_req:
            exporter = ZabbixTemplateExporter("http://z.local", "tok")
        # _configure_ssl disables warnings and overrides default context
        mock_req.packages.urllib3.disable_warnings.assert_called_once()


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    def test_connect_creates_api_and_logs_in(self):
        exporter = _make_exporter()
        mock_api_instance = MagicMock()
        with patch("export_host_templates.ZabbixAPI", return_value=mock_api_instance):
            exporter.connect()
        mock_api_instance.login.assert_called_once_with(token="my-token")
        assert exporter.api is mock_api_instance

    def test_disconnect_calls_logout(self):
        exporter = _make_exporter()
        mock_api = MagicMock()
        exporter.api = mock_api
        exporter.disconnect()
        mock_api.logout.assert_called_once()
        assert exporter.api is None

    def test_disconnect_when_not_connected_does_not_raise(self):
        exporter = _make_exporter()
        exporter.api = None
        exporter.disconnect()  # should not raise


# ---------------------------------------------------------------------------
# get_templates_filtered_by_group
# ---------------------------------------------------------------------------


class TestGetTemplatesFilteredByGroup:
    def test_returns_templates_for_group(self):
        exporter = _make_exporter()
        exporter.api = MagicMock()
        exporter.api.templategroup.get.return_value = [{"groupid": "5", "name": "Custom"}]
        exporter.api.template.get.return_value = [
            {"templateid": "100", "name": "Template1"},
            {"templateid": "101", "name": "Template2"},
        ]
        result = exporter.get_templates_filtered_by_group("Custom")
        assert len(result) == 2

    def test_returns_empty_when_group_not_found(self):
        exporter = _make_exporter()
        exporter.api = MagicMock()
        exporter.api.templategroup.get.return_value = []
        result = exporter.get_templates_filtered_by_group("NonExistentGroup")
        assert result == []


# ---------------------------------------------------------------------------
# get_all_templates
# ---------------------------------------------------------------------------


class TestGetAllTemplates:
    def test_returns_all_templates(self):
        exporter = _make_exporter()
        exporter.api = MagicMock()
        exporter.api.template.get.return_value = [
            {"templateid": "1", "name": "A"},
            {"templateid": "2", "name": "B"},
        ]
        result = exporter.get_all_templates()
        assert len(result) == 2

    def test_raises_when_not_connected(self):
        exporter = _make_exporter()
        exporter.api = None
        with pytest.raises(RuntimeError, match="Not connected"):
            exporter.get_all_templates()


# ---------------------------------------------------------------------------
# filter_templates_by_group
# ---------------------------------------------------------------------------


class TestFilterTemplatesByGroup:
    def test_filters_correctly(self):
        templates = [
            {"name": "T1", "templategroups": [{"name": "Custom"}]},
            {"name": "T2", "templategroups": [{"name": "Other"}]},
            {"name": "T3", "templategroups": [{"name": "Custom"}, {"name": "Other"}]},
        ]
        exporter = _make_exporter()
        result = exporter.filter_templates_by_group(templates, "Custom")
        assert len(result) == 2
        names = [t["name"] for t in result]
        assert "T1" in names
        assert "T3" in names

    def test_returns_empty_when_no_match(self):
        templates = [{"name": "T1", "templategroups": [{"name": "Other"}]}]
        exporter = _make_exporter()
        result = exporter.filter_templates_by_group(templates, "Nonexistent")
        assert result == []

    def test_handles_template_without_groups(self):
        templates = [{"name": "T1", "templategroups": []}]
        exporter = _make_exporter()
        result = exporter.filter_templates_by_group(templates, "Custom")
        assert result == []


# ---------------------------------------------------------------------------
# export_templates_configuration
# ---------------------------------------------------------------------------


class TestExportTemplatesConfiguration:
    def test_calls_api_export(self):
        exporter = _make_exporter()
        exporter.api = MagicMock()
        exporter.api.configuration.export.return_value = "---\nzabbix_export:\n  version: 7.2\n"
        result = exporter.export_templates_configuration(["100", "101"])
        exporter.api.configuration.export.assert_called_once_with(
            options={"templates": ["100", "101"]}, format="yaml"
        )
        assert "zabbix_export" in result

    def test_raises_when_not_connected(self):
        exporter = _make_exporter()
        exporter.api = None
        with pytest.raises(RuntimeError, match="Not connected"):
            exporter.export_templates_configuration(["100"])


# ---------------------------------------------------------------------------
# _sanitize_filename
# ---------------------------------------------------------------------------


class TestSanitizeFilename:
    def test_replaces_slash(self):
        exporter = _make_exporter()
        assert exporter._sanitize_filename("Template/Name") == "Template_Name"

    def test_no_slash_unchanged(self):
        exporter = _make_exporter()
        assert exporter._sanitize_filename("TemplateName") == "TemplateName"

    def test_multiple_slashes(self):
        exporter = _make_exporter()
        assert exporter._sanitize_filename("A/B/C") == "A_B_C"


# ---------------------------------------------------------------------------
# save_template_to_file
# ---------------------------------------------------------------------------


class TestSaveTemplateToFile:
    def test_saves_file_in_output_dir(self, tmp_path):
        exporter = _make_exporter(output_dir=str(tmp_path))
        path = exporter.save_template_to_file("MyTemplate", "---\nzabbix_export:\n")
        assert Path(path).exists()
        assert Path(path).read_text() == "---\nzabbix_export:\n"

    def test_filename_has_yaml_extension(self, tmp_path):
        exporter = _make_exporter(output_dir=str(tmp_path))
        path = exporter.save_template_to_file("MyTemplate", "content")
        assert path.endswith(".yaml")

    def test_creates_output_dir_if_missing(self, tmp_path):
        new_dir = tmp_path / "new_output"
        exporter = _make_exporter(output_dir=str(new_dir))
        exporter.save_template_to_file("T", "content")
        assert new_dir.exists()

    def test_sanitizes_template_name_in_filename(self, tmp_path):
        exporter = _make_exporter(output_dir=str(tmp_path))
        path = exporter.save_template_to_file("Linux/Servers", "content")
        assert "Linux_Servers" in path


# ---------------------------------------------------------------------------
# export_templates_by_group (integration-style)
# ---------------------------------------------------------------------------


class TestExportTemplatesByGroup:
    def test_exports_each_template_to_file(self, tmp_path):
        exporter = _make_exporter(output_dir=str(tmp_path))
        exporter.api = MagicMock()
        exporter.api.templategroup.get.return_value = [{"groupid": "5", "name": "Custom"}]
        exporter.api.template.get.return_value = [
            {"templateid": "100", "name": "Template1"},
        ]
        exporter.api.configuration.export.return_value = "---\nzabbix_export:\n  version: 7.2\n"
        exporter.export_templates_by_group("Custom")
        assert (tmp_path / "Template1.yaml").exists()

    def test_handles_empty_group(self, tmp_path, capsys):
        exporter = _make_exporter(output_dir=str(tmp_path))
        exporter.api = MagicMock()
        exporter.api.templategroup.get.return_value = []
        exporter.export_templates_by_group("EmptyGroup")
        # Should not raise; output directory should be empty
        assert not list(tmp_path.glob("*.yaml"))
