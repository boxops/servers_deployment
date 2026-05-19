"""
Unit tests for ansible/zabbix/scripts/import_host_templates.py

All Zabbix API calls are mocked via unittest.mock.
"""

import os
import glob
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open, call

# conftest.py adds ansible/zabbix/scripts to sys.path
from import_host_templates import ZabbixTemplateImporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_importer(url="http://zabbix.local", token="my-token", templates_dir="templates"):
    with patch("import_host_templates.ZabbixAPI"), \
         patch("import_host_templates.ssl"), \
         patch("import_host_templates.requests"):
        return ZabbixTemplateImporter(url, token, templates_dir)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestZabbixTemplateImporterInit:
    def test_stores_url_token_dir(self):
        imp = _make_importer("http://zabbix.local", "tok123", "my_templates")
        assert imp.url == "http://zabbix.local"
        assert imp.token == "tok123"
        assert imp.templates_dir == "my_templates"

    def test_api_starts_as_none(self):
        imp = _make_importer()
        assert imp.api is None

    def test_ssl_warnings_disabled(self):
        with patch("import_host_templates.ZabbixAPI"), \
             patch("import_host_templates.ssl"), \
             patch("import_host_templates.requests") as mock_req:
            ZabbixTemplateImporter("http://z.local", "tok")
        mock_req.packages.urllib3.disable_warnings.assert_called_once()


# ---------------------------------------------------------------------------
# connect / disconnect
# ---------------------------------------------------------------------------


class TestConnectDisconnect:
    def test_connect_logs_in_with_token(self):
        imp = _make_importer()
        mock_api = MagicMock()
        with patch("import_host_templates.ZabbixAPI", return_value=mock_api):
            imp.connect()
        mock_api.login.assert_called_once_with(token="my-token")
        assert imp.api is mock_api

    def test_disconnect_calls_logout(self):
        imp = _make_importer()
        mock_api = MagicMock()
        imp.api = mock_api
        imp.disconnect()
        mock_api.logout.assert_called_once()
        assert imp.api is None

    def test_disconnect_when_not_connected(self):
        imp = _make_importer()
        imp.api = None
        imp.disconnect()  # should not raise


# ---------------------------------------------------------------------------
# get_template_files
# ---------------------------------------------------------------------------


class TestGetTemplateFiles:
    def test_returns_yaml_files(self, tmp_path):
        (tmp_path / "template1.yaml").write_text("---")
        (tmp_path / "template2.yaml").write_text("---")
        imp = _make_importer(templates_dir=str(tmp_path))
        files = imp.get_template_files()
        assert len(files) == 2

    def test_raises_when_dir_not_found(self):
        imp = _make_importer(templates_dir="/nonexistent/dir")
        with pytest.raises(FileNotFoundError, match="not found"):
            imp.get_template_files()

    def test_returns_empty_when_no_matching_files(self, tmp_path):
        (tmp_path / "data.json").write_text("{}")
        imp = _make_importer(templates_dir=str(tmp_path))
        files = imp.get_template_files()
        assert files == []

    def test_custom_pattern(self, tmp_path):
        (tmp_path / "template.xml").write_text("<xml/>")
        (tmp_path / "template.yaml").write_text("---")
        imp = _make_importer(templates_dir=str(tmp_path))
        files = imp.get_template_files("*.xml")
        assert len(files) == 1
        assert files[0].endswith(".xml")


# ---------------------------------------------------------------------------
# read_template_file
# ---------------------------------------------------------------------------


class TestReadTemplateFile:
    def test_reads_file_content(self, tmp_path):
        f = tmp_path / "template.yaml"
        f.write_text("zabbix_export:\n  version: 7.2\n")
        imp = _make_importer()
        content = imp.read_template_file(str(f))
        assert "zabbix_export" in content

    def test_raises_when_file_not_found(self):
        imp = _make_importer()
        with pytest.raises(FileNotFoundError, match="not found"):
            imp.read_template_file("/nonexistent/file.yaml")


# ---------------------------------------------------------------------------
# import_template_configuration
# ---------------------------------------------------------------------------


class TestImportTemplateConfiguration:
    def test_calls_api_import(self):
        imp = _make_importer()
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        result = imp.import_template_configuration("---\nzabbix_export:\n")
        imp.api.configuration.import_.assert_called_once()
        assert result is True

    def test_raises_when_not_connected(self):
        imp = _make_importer()
        imp.api = None
        with pytest.raises(RuntimeError, match="Not connected"):
            imp.import_template_configuration("---")

    def test_passes_yaml_format(self):
        imp = _make_importer()
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        imp.import_template_configuration("---")
        call_kwargs = imp.api.configuration.import_.call_args[1]
        assert call_kwargs.get("format") == "yaml"

    def test_create_missing_flag_true_by_default(self):
        imp = _make_importer()
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        imp.import_template_configuration("---")
        call_kwargs = imp.api.configuration.import_.call_args[1]
        rules = call_kwargs.get("rules", {})
        assert rules.get("templates", {}).get("createMissing") is True


# ---------------------------------------------------------------------------
# import_single_template
# ---------------------------------------------------------------------------


class TestImportSingleTemplate:
    def test_imports_from_full_path(self, tmp_path):
        f = tmp_path / "template.yaml"
        f.write_text("---\nzabbix_export:\n")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        result = imp.import_single_template(str(f))
        assert result is True

    def test_imports_from_filename_only(self, tmp_path):
        f = tmp_path / "template.yaml"
        f.write_text("---\nzabbix_export:\n")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        result = imp.import_single_template("template.yaml")
        assert result is True

    def test_raises_on_api_error(self, tmp_path):
        f = tmp_path / "bad.yaml"
        f.write_text("invalid: yaml: content")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        imp.api.configuration.import_.side_effect = Exception("API error")
        with pytest.raises(Exception, match="API error"):
            imp.import_single_template(str(f))


# ---------------------------------------------------------------------------
# import_all_templates
# ---------------------------------------------------------------------------


class TestImportAllTemplates:
    def test_imports_all_yaml_files(self, tmp_path):
        for i in range(3):
            (tmp_path / f"template{i}.yaml").write_text("---\nzabbix_export:\n")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        summary = imp.import_all_templates()
        assert summary["successful_imports"] == 3
        assert summary["failed_imports"] == 0

    def test_returns_summary_with_no_files(self, tmp_path):
        imp = _make_importer(templates_dir=str(tmp_path))
        summary = imp.import_all_templates()
        assert summary["total_files"] == 0
        assert summary["successful_imports"] == 0

    def test_counts_failed_imports(self, tmp_path):
        (tmp_path / "good.yaml").write_text("---\nzabbix_export:\n")
        (tmp_path / "bad.yaml").write_text("---\nzabbix_export:\n")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return True
            raise Exception("Import failed")

        imp.api.configuration.import_.side_effect = side_effect
        summary = imp.import_all_templates()
        assert summary["successful_imports"] == 1
        assert summary["failed_imports"] == 1

    def test_stop_on_error(self, tmp_path):
        for i in range(3):
            (tmp_path / f"template{i}.yaml").write_text("---\nzabbix_export:\n")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        imp.api.configuration.import_.side_effect = Exception("fail")
        summary = imp.import_all_templates(stop_on_error=True)
        # Should stop after first failure
        assert summary["failed_imports"] == 1
        assert summary["successful_imports"] == 0

    def test_results_list_populated(self, tmp_path):
        (tmp_path / "template.yaml").write_text("---\nzabbix_export:\n")
        imp = _make_importer(templates_dir=str(tmp_path))
        imp.api = MagicMock()
        imp.api.configuration.import_.return_value = True
        summary = imp.import_all_templates()
        assert len(summary["results"]) == 1
        assert summary["results"][0]["status"] == "success"
