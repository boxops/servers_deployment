"""
Unit tests for ansible/zabbix/scripts/host_template_generator.py

No external services are required; all file I/O is handled via tmp_path.
"""

import csv
import io
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock

# conftest.py adds ansible/zabbix/scripts to sys.path
from host_template_generator import (
    SNMPDataTypeMapper,
    ZabbixTemplateGenerator,
    ZabbixTemplateBuilder,
)


# ---------------------------------------------------------------------------
# SNMPDataTypeMapper
# ---------------------------------------------------------------------------


class TestSNMPDataTypeMapper:
    @pytest.mark.parametrize("snmp_type,expected", [
        ("STRING: something", "CHAR"),
        ("OID: 1.2.3", "CHAR"),
        ("BITS: 0xAB", "TEXT"),
        ("INTEGER: 42", "FLOAT"),
        ("INTEGER32: 42", "FLOAT"),
        ("COUNTER: 100", "TEXT"),          # empty in map → "TEXT"
        ("COUNTER32: 100", "TEXT"),
        ("COUNTER64: 200", "TEXT"),
        ("GAUGE: 5", "TEXT"),
        ("GAUGE32: 5", "TEXT"),
        ("IPADDR: 1.2.3.4", "TEXT"),
        ("IPADDRESS: 1.2.3.4", "TEXT"),
        ("OBJECTID: 1.2.3", "TEXT"),
        ("OCTETSTR: abc", "TEXT"),
        ("OCTETSTRING: abc", "TEXT"),
        ("OPAQUE: hex", "TEXT"),
        ("HEX-STRING: de ad", "TEXT"),
        ("TIMETICKS: 1234", "TEXT"),       # empty in map → "TEXT"
    ])
    def test_known_types(self, snmp_type, expected):
        result = SNMPDataTypeMapper.get_data_type(snmp_type)
        assert result == expected

    def test_unknown_type_defaults_to_text(self):
        result = SNMPDataTypeMapper.get_data_type("UNKNOWNTYPE: something")
        assert result == "TEXT"

    def test_case_insensitive(self):
        assert SNMPDataTypeMapper.get_data_type("string: val") == "CHAR"
        assert SNMPDataTypeMapper.get_data_type("STRING: val") == "CHAR"

    def test_trap_type_returns_empty_string(self, capsys):
        result = SNMPDataTypeMapper.get_data_type("NOTIF: trap")
        assert result == ""

    def test_notif_type_returns_empty_string(self):
        result = SNMPDataTypeMapper.get_data_type("TRAP: something")
        assert result == ""

    def test_value_without_colon(self):
        # Should handle gracefully – treat whole value as the type
        result = SNMPDataTypeMapper.get_data_type("TEXT")
        assert result == "TEXT"


# ---------------------------------------------------------------------------
# ZabbixTemplateGenerator
# ---------------------------------------------------------------------------


class TestZabbixTemplateGeneratorInit:
    def test_default_name_and_group(self):
        gen = ZabbixTemplateGenerator()
        assert gen.template_name == "SNMP OID Template"
        assert gen.template_group == "Custom"

    def test_custom_name_and_group(self):
        gen = ZabbixTemplateGenerator("My Template", "Production")
        assert gen.template_name == "My Template"
        assert gen.template_group == "Production"


class TestGenerateUuid:
    def test_returns_string_without_hyphens(self):
        gen = ZabbixTemplateGenerator()
        uid = gen.generate_uuid()
        assert isinstance(uid, str)
        assert "-" not in uid

    def test_uuids_are_unique(self):
        gen = ZabbixTemplateGenerator()
        uids = {gen.generate_uuid() for _ in range(50)}
        assert len(uids) == 50


class TestCreateTemplateStructure:
    def test_returns_dict_with_zabbix_export(self):
        gen = ZabbixTemplateGenerator()
        structure = gen.create_template_structure()
        assert "zabbix_export" in structure

    def test_version_is_set(self):
        gen = ZabbixTemplateGenerator()
        structure = gen.create_template_structure()
        assert structure["zabbix_export"]["version"] == "7.2"

    def test_templates_list_has_one_entry(self):
        gen = ZabbixTemplateGenerator()
        structure = gen.create_template_structure()
        templates = structure["zabbix_export"]["templates"]
        assert len(templates) == 1

    def test_template_name_matches(self):
        gen = ZabbixTemplateGenerator("CustomTemplate")
        structure = gen.create_template_structure()
        tpl = structure["zabbix_export"]["templates"][0]
        assert tpl["template"] == "CustomTemplate"

    def test_items_and_rules_are_empty_lists(self):
        gen = ZabbixTemplateGenerator()
        structure = gen.create_template_structure()
        tpl = structure["zabbix_export"]["templates"][0]
        assert tpl["items"] == []
        assert tpl["discovery_rules"] == []


class TestCreateSingularItem:
    def test_item_has_required_fields(self):
        gen = ZabbixTemplateGenerator()
        item = gen.create_singular_item("1.3.6.1.2.1.1.1.0", {"name": "sysDescr", "type": "STRING"})
        for field in ("uuid", "name", "key", "snmp_oid", "type", "value_type", "delay"):
            assert field in item

    def test_item_name_from_mib_data(self):
        gen = ZabbixTemplateGenerator()
        item = gen.create_singular_item("1.3.6.1.2.1.1.1.0", {"name": "sysDescr", "type": "STRING"})
        assert item["name"] == "sysDescr"

    def test_item_oid_stored(self):
        gen = ZabbixTemplateGenerator()
        item = gen.create_singular_item("1.3.6.1.2.1.1.1.0", {"name": "sysDescr", "type": "STRING"})
        assert item["snmp_oid"] == "1.3.6.1.2.1.1.1.0"

    def test_item_value_type_mapping(self):
        gen = ZabbixTemplateGenerator()
        item = gen.create_singular_item("1.0", {"name": "test", "type": "INTEGER"})
        assert item["value_type"] == "FLOAT"

    def test_item_has_preprocessing(self):
        gen = ZabbixTemplateGenerator()
        item = gen.create_singular_item("1.0", {"name": "test", "type": "STRING"})
        assert len(item["preprocessing"]) > 0


class TestClassifyOids:
    def test_singular_oid_ends_with_zero(self):
        gen = ZabbixTemplateGenerator()
        mib_data = {"1.3.6.1.2.1.1.1.0": {"name": "sysDescr", "type": "STRING", "value": "Linux"}}
        result = gen.classify_oids(mib_data)
        assert "1.3.6.1.2.1.1.1.0" in result["singular"]

    def test_tabular_oid_classified_correctly(self):
        gen = ZabbixTemplateGenerator()
        mib_data = {
            "1.3.6.1.2.1.2.2.1.2.1": {"name": "ifDescr.1", "type": "STRING", "value": "eth0"},
            "1.3.6.1.2.1.2.2.1.2.2": {"name": "ifDescr.2", "type": "STRING", "value": "eth1"},
        }
        result = gen.classify_oids(mib_data)
        assert len(result["tabular"]) > 0

    def test_mixed_oids(self):
        gen = ZabbixTemplateGenerator()
        mib_data = {
            "1.3.6.1.2.1.1.1.0": {"name": "sysDescr", "type": "STRING", "value": "Linux"},
            "1.3.6.1.2.1.2.2.1.2.1": {"name": "ifDescr.1", "type": "STRING", "value": "eth0"},
        }
        result = gen.classify_oids(mib_data)
        assert len(result["singular"]) == 1
        assert len(result["tabular"]) > 0

    def test_oid_without_leading_dot(self):
        gen = ZabbixTemplateGenerator()
        mib_data = {"3.6.1.2.1.1.1.0": {"name": "sysDescr", "type": "STRING", "value": ""}}
        result = gen.classify_oids(mib_data)
        # Should be normalised and classified
        assert len(result["singular"]) + len(result["tabular"]) > 0


class TestFindCommonPrefix:
    def test_finds_common_prefix(self):
        gen = ZabbixTemplateGenerator()
        result = gen._find_common_prefix(["ifDescr.1", "ifDescr.2", "ifDescr.3"])
        assert result == "ifDescr"

    def test_no_common_prefix(self):
        gen = ZabbixTemplateGenerator()
        result = gen._find_common_prefix(["abc.1", "xyz.2"])
        # Should return something or None, not raise
        assert result is None or isinstance(result, str)

    def test_empty_list(self):
        gen = ZabbixTemplateGenerator()
        result = gen._find_common_prefix([])
        assert result is None

    def test_single_name(self):
        gen = ZabbixTemplateGenerator()
        result = gen._find_common_prefix(["ifOperStatus.1"])
        assert result is not None


class TestCreateDiscoveryRule:
    def _make_table_data(self):
        return {
            "table_name": "Interface Table",
            "columns": {
                "2": [
                    {
                        "instance_id": "1",
                        "full_oid": "1.3.6.1.2.1.2.2.1.2.1",
                        "data": {
                            "name": "ifDescr.1",
                            "type": "STRING",
                            "value": "eth0",
                        },
                    }
                ]
            },
        }

    def test_returns_discovery_rule_dict(self):
        gen = ZabbixTemplateGenerator()
        rule = gen.create_discovery_rule("1.3.6.1.2.1.2.2", self._make_table_data())
        assert "uuid" in rule
        assert "item_prototypes" in rule

    def test_item_prototypes_populated(self):
        gen = ZabbixTemplateGenerator()
        rule = gen.create_discovery_rule("1.3.6.1.2.1.2.2", self._make_table_data())
        assert len(rule["item_prototypes"]) == 1

    def test_discovery_rule_type_is_snmp(self):
        gen = ZabbixTemplateGenerator()
        rule = gen.create_discovery_rule("1.3.6.1.2.1.2.2", self._make_table_data())
        assert rule["type"] == "SNMP_AGENT"


class TestParseCsv:
    def test_parses_csv_into_mib_dict(self, tmp_path, sample_csv_content):
        csv_file = tmp_path / "mibwalk.csv"
        csv_file.write_text(sample_csv_content)
        gen = ZabbixTemplateGenerator()
        result = gen._parse_csv(str(csv_file))
        assert "3.6.1.2.1.1.1.0" in result or any("sysDescr" in v.get("name","") for v in result.values())

    def test_parses_name_field(self, tmp_path, sample_csv_content):
        csv_file = tmp_path / "mibwalk.csv"
        csv_file.write_text(sample_csv_content)
        gen = ZabbixTemplateGenerator()
        result = gen._parse_csv(str(csv_file))
        names = [v["name"] for v in result.values()]
        assert "sysDescr" in names

    def test_handles_tab_delimiter(self, tmp_path):
        content = "OID\tName\tType\tValue\n1.3.6.1.2.1.1.1.0\tsysDescr\tSTRING\tLinux\n"
        csv_file = tmp_path / "mibwalk.tsv"
        csv_file.write_text(content)
        gen = ZabbixTemplateGenerator()
        result = gen._parse_csv(str(csv_file))
        assert len(result) > 0

    def test_skips_rows_without_oid(self, tmp_path):
        content = "OID,Name,Type,Value\n,empty_oid,STRING,nothing\n1.2.3.0,valid,STRING,yes\n"
        csv_file = tmp_path / "mibwalk.csv"
        csv_file.write_text(content)
        gen = ZabbixTemplateGenerator()
        result = gen._parse_csv(str(csv_file))
        assert len(result) == 1


class TestGenerateTemplateFromCsv:
    def test_creates_template_with_items(self, tmp_path, sample_csv_content):
        csv_file = tmp_path / "mibwalk.csv"
        csv_file.write_text(sample_csv_content)
        gen = ZabbixTemplateGenerator()
        template = gen.generate_template_from_csv(str(csv_file))
        tpl = template["zabbix_export"]["templates"][0]
        total = len(tpl["items"]) + len(tpl["discovery_rules"])
        assert total > 0

    def test_template_has_correct_structure(self, tmp_path, sample_csv_content):
        csv_file = tmp_path / "mibwalk.csv"
        csv_file.write_text(sample_csv_content)
        gen = ZabbixTemplateGenerator()
        template = gen.generate_template_from_csv(str(csv_file))
        assert "zabbix_export" in template


class TestSaveTemplate:
    def test_saves_yaml_file(self, tmp_path):
        gen = ZabbixTemplateGenerator()
        template = gen.create_template_structure()
        outfile = str(tmp_path / "output.yaml")
        gen.save_template(template, outfile)
        assert Path(outfile).exists()

    def test_saved_file_is_valid_yaml(self, tmp_path):
        gen = ZabbixTemplateGenerator()
        template = gen.create_template_structure()
        outfile = str(tmp_path / "output.yaml")
        gen.save_template(template, outfile)
        with open(outfile) as f:
            loaded = yaml.safe_load(f)
        assert "zabbix_export" in loaded


# ---------------------------------------------------------------------------
# ZabbixTemplateBuilder
# ---------------------------------------------------------------------------


class TestZabbixTemplateBuilder:
    def test_build_from_csv(self, tmp_path, sample_csv_content):
        csv_file = tmp_path / "mibwalk.csv"
        csv_file.write_text(sample_csv_content)
        output_file = tmp_path / "output.yaml"
        builder = ZabbixTemplateBuilder("Test Template")
        template = builder.build_from_csv(str(csv_file), str(output_file))
        assert "zabbix_export" in template
        assert output_file.exists()

    def test_builder_default_name(self):
        builder = ZabbixTemplateBuilder()
        assert builder.generator.template_name == "SNMP OID Template"

    def test_builder_custom_name(self):
        builder = ZabbixTemplateBuilder("My Custom Template")
        assert builder.generator.template_name == "My Custom Template"
