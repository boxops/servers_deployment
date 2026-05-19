"""
Unit tests for scripts/generate-docs.py

Tests InfrastructureDocsGenerator without hitting any real Terraform or
Ansible endpoints; filesystem and subprocess calls are fully mocked.
"""

import json
import subprocess
import pytest
import yaml
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch, call

# The module lives at scripts/generate-docs.py; conftest.py adds scripts/ to
# sys.path so we can import it under its runtime name.
import importlib, sys

# generate-docs.py has a hyphen – import it via importlib
spec = importlib.util.spec_from_file_location(
    "generate_docs",
    Path(__file__).parent.parent / "scripts" / "generate-docs.py",
)
generate_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_docs)
InfrastructureDocsGenerator = generate_docs.InfrastructureDocsGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_generator(tmp_path):
    """Return an InfrastructureDocsGenerator that writes into tmp_path."""
    return InfrastructureDocsGenerator(
        config_dir=str(tmp_path / "terraform"),
        ansible_dir=str(tmp_path / "ansible"),
        output_dir=str(tmp_path / "docs"),
    )


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestInit:
    def test_output_directory_created(self, tmp_path):
        gen = _make_generator(tmp_path)
        assert (tmp_path / "docs").is_dir()

    def test_paths_stored_as_path_objects(self, tmp_path):
        gen = _make_generator(tmp_path)
        assert isinstance(gen.config_dir, Path)
        assert isinstance(gen.ansible_dir, Path)
        assert isinstance(gen.output_dir, Path)

    def test_initial_state_empty(self, tmp_path):
        gen = _make_generator(tmp_path)
        assert gen.terraform_vars == {}
        assert gen.ansible_vars == {}
        assert gen.infrastructure == {}


# ---------------------------------------------------------------------------
# _parse_tfvars
# ---------------------------------------------------------------------------


class TestParseTfvars:
    def test_parses_simple_key_value(self, tmp_path):
        tf = tmp_path / "main.tfvars"
        tf.write_text('proxmox_node = "pve"\nnetwork_cidr = "24"\n')
        gen = _make_generator(tmp_path)
        result = gen._parse_tfvars(tf)
        assert result["proxmox_node"] == "pve"
        assert result["network_cidr"] == "24"

    def test_ignores_comment_lines(self, tmp_path):
        tf = tmp_path / "main.tfvars"
        tf.write_text("# This is a comment\nkey = \"value\"\n")
        gen = _make_generator(tmp_path)
        result = gen._parse_tfvars(tf)
        assert "# This is a comment" not in result
        assert result["key"] == "value"

    def test_ignores_lines_without_equals(self, tmp_path):
        tf = tmp_path / "main.tfvars"
        tf.write_text("no_equals_here\nvalid = \"yes\"\n")
        gen = _make_generator(tmp_path)
        result = gen._parse_tfvars(tf)
        assert "no_equals_here" not in result
        assert result["valid"] == "yes"

    def test_strips_quotes(self, tmp_path):
        tf = tmp_path / "main.tfvars"
        tf.write_text('my_var = \'single_quoted\'\n')
        gen = _make_generator(tmp_path)
        result = gen._parse_tfvars(tf)
        assert result["my_var"] == "single_quoted"

    def test_value_with_equals_sign(self, tmp_path):
        tf = tmp_path / "main.tfvars"
        tf.write_text('url = "https://host:8006/api2/json"\n')
        gen = _make_generator(tmp_path)
        result = gen._parse_tfvars(tf)
        assert result["url"] == "https://host:8006/api2/json"

    def test_sample_fixture(self, tmp_path, sample_tfvars_content):
        tf = tmp_path / "terraform.tfvars"
        tf.write_text(sample_tfvars_content)
        gen = _make_generator(tmp_path)
        result = gen._parse_tfvars(tf)
        assert result["proxmox_node"] == "pve"
        assert result["network_gateway"] == "192.168.1.1"
        assert result["zabbix_server_cores"] == "4"


# ---------------------------------------------------------------------------
# load_terraform_config
# ---------------------------------------------------------------------------


class TestLoadTerraformConfig:
    def test_loads_tfvars_when_file_exists(self, tmp_path, sample_tfvars_content):
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        (tf_dir / "terraform.tfvars").write_text(sample_tfvars_content)

        gen = _make_generator(tmp_path)
        gen.config_dir = tf_dir
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "terraform")
            result = gen.load_terraform_config()

        assert result["proxmox_node"] == "pve"

    def test_handles_missing_tfvars_gracefully(self, tmp_path):
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        gen = _make_generator(tmp_path)
        gen.config_dir = tf_dir
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            result = gen.load_terraform_config()
        assert isinstance(result, dict)

    def test_merges_terraform_outputs(self, tmp_path):
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        gen = _make_generator(tmp_path)
        gen.config_dir = tf_dir
        tf_output = {"proxmox_api_url": {"value": "https://pve.example.com"}}
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(tf_output)
            )
            result = gen.load_terraform_config()
        assert result.get("proxmox_api_url") == "https://pve.example.com"


# ---------------------------------------------------------------------------
# load_ansible_config
# ---------------------------------------------------------------------------


class TestLoadAnsibleConfig:
    def test_loads_inventory_when_file_exists(self, tmp_path, sample_inventory_content):
        ans_dir = tmp_path / "ansible"
        inv_dir = ans_dir / "inventories"
        inv_dir.mkdir(parents=True)
        with open(inv_dir / "hosts.yml", "w") as f:
            yaml.dump(sample_inventory_content, f)

        gen = _make_generator(tmp_path)
        gen.ansible_dir = ans_dir
        result = gen.load_ansible_config()
        assert "inventory" in result

    def test_returns_empty_when_no_inventory(self, tmp_path):
        ans_dir = tmp_path / "ansible"
        ans_dir.mkdir()
        gen = _make_generator(tmp_path)
        gen.ansible_dir = ans_dir
        result = gen.load_ansible_config()
        assert isinstance(result, dict)

    def test_loads_group_vars(self, tmp_path):
        ans_dir = tmp_path / "ansible"
        gv_dir = ans_dir / "group_vars"
        gv_dir.mkdir(parents=True)
        (gv_dir / "all.yml").write_text("my_var: my_value\n")

        gen = _make_generator(tmp_path)
        gen.ansible_dir = ans_dir
        result = gen.load_ansible_config()
        assert result.get("all", {}).get("my_var") == "my_value"


# ---------------------------------------------------------------------------
# analyze_infrastructure
# ---------------------------------------------------------------------------


class TestAnalyzeInfrastructure:
    def _setup_gen_with_inventory(self, tmp_path, sample_inventory_content, tfvars=""):
        gen = _make_generator(tmp_path)
        gen.ansible_vars = {"inventory": sample_inventory_content}
        gen.terraform_vars = {
            "network_gateway": "192.168.1.1",
            "network_cidr": "24",
            "proxmox_bridge": "vmbr0",
            "proxmox_node": "pve",
            "proxmox_storage": "local-lvm",
            "vm_template": "ubuntu-22.04",
            "zabbix_server_vmid": "200",
            "zabbix_server_cores": "4",
            "zabbix_server_memory": "4096",
        }
        return gen

    def test_returns_expected_keys(self, tmp_path, sample_inventory_content):
        gen = self._setup_gen_with_inventory(tmp_path, sample_inventory_content)
        result = gen.analyze_infrastructure()
        for key in ("servers", "proxies", "network", "resources", "services", "deployment_info"):
            assert key in result

    def test_extracts_server_from_inventory(self, tmp_path, sample_inventory_content):
        gen = self._setup_gen_with_inventory(tmp_path, sample_inventory_content)
        result = gen.analyze_infrastructure()
        assert len(result["servers"]) == 1
        assert result["servers"][0]["name"] == "zabbix-server-01"

    def test_extracts_proxy_from_inventory(self, tmp_path, sample_inventory_content):
        gen = self._setup_gen_with_inventory(tmp_path, sample_inventory_content)
        result = gen.analyze_infrastructure()
        assert len(result["proxies"]) == 1
        assert result["proxies"][0]["ip_address"] == "192.168.1.20"

    def test_network_config_populated(self, tmp_path, sample_inventory_content):
        gen = self._setup_gen_with_inventory(tmp_path, sample_inventory_content)
        result = gen.analyze_infrastructure()
        assert result["network"]["gateway"] == "192.168.1.1"
        assert result["network"]["bridge"] == "vmbr0"

    def test_resource_totals_computed(self, tmp_path, sample_inventory_content):
        gen = self._setup_gen_with_inventory(tmp_path, sample_inventory_content)
        result = gen.analyze_infrastructure()
        assert result["resources"]["total_cpu_cores"] == 4
        assert result["resources"]["total_memory_gb"] == 4.0

    def test_empty_inventory_returns_empty_lists(self, tmp_path):
        gen = _make_generator(tmp_path)
        gen.ansible_vars = {}
        gen.terraform_vars = {}
        result = gen.analyze_infrastructure()
        assert result["servers"] == []
        assert result["proxies"] == []


# ---------------------------------------------------------------------------
# generate_architecture_markdown
# ---------------------------------------------------------------------------


class TestGenerateArchitectureMarkdown:
    def _populated_gen(self, tmp_path, sample_inventory_content):
        gen = _make_generator(tmp_path)
        gen.ansible_vars = {"inventory": sample_inventory_content}
        gen.terraform_vars = {
            "network_gateway": "192.168.1.1",
            "network_cidr": "24",
            "proxmox_bridge": "vmbr0",
            "proxmox_node": "pve",
            "proxmox_storage": "local-lvm",
            "vm_template": "ubuntu-22.04",
            "zabbix_server_vmid": "200",
            "zabbix_server_cores": "4",
            "zabbix_server_memory": "4096",
        }
        gen.analyze_infrastructure()
        return gen

    def test_returns_string(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_architecture_markdown()
        assert isinstance(result, str)

    def test_contains_server_ip(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_architecture_markdown()
        assert "192.168.1.10" in result

    def test_contains_proxy_ip(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_architecture_markdown()
        assert "192.168.1.20" in result

    def test_contains_heading(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_architecture_markdown()
        assert "# Zabbix Infrastructure Architecture" in result

    def test_handles_bad_gateway_gracefully(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        gen.infrastructure["network"]["gateway"] = ""
        gen.infrastructure["network"]["cidr"] = ""
        result = gen.generate_architecture_markdown()
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# generate_quick_reference
# ---------------------------------------------------------------------------


class TestGenerateQuickReference:
    def _populated_gen(self, tmp_path, sample_inventory_content):
        gen = _make_generator(tmp_path)
        gen.ansible_vars = {"inventory": sample_inventory_content}
        gen.terraform_vars = {
            "network_gateway": "192.168.1.1",
            "network_cidr": "24",
            "proxmox_bridge": "vmbr0",
            "proxmox_node": "pve",
            "proxmox_storage": "local-lvm",
            "vm_template": "ubuntu-22.04",
            "zabbix_server_vmid": "200",
            "zabbix_server_cores": "4",
            "zabbix_server_memory": "4096",
        }
        gen.analyze_infrastructure()
        return gen

    def test_returns_string(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_quick_reference()
        assert isinstance(result, str)

    def test_contains_zabbix_heading(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_quick_reference()
        assert "Quick Reference" in result

    def test_contains_server_ip(self, tmp_path, sample_inventory_content):
        gen = self._populated_gen(tmp_path, sample_inventory_content)
        result = gen.generate_quick_reference()
        assert "192.168.1.10" in result


# ---------------------------------------------------------------------------
# validate_infrastructure
# ---------------------------------------------------------------------------


class TestValidateInfrastructure:
    def _gen_with_infra(self, tmp_path, sample_inventory_content):
        gen = _make_generator(tmp_path)
        gen.ansible_vars = {"inventory": sample_inventory_content}
        gen.terraform_vars = {
            "network_gateway": "192.168.1.1",
            "network_cidr": "24",
            "proxmox_bridge": "vmbr0",
            "proxmox_node": "pve",
            "proxmox_storage": "local-lvm",
            "vm_template": "ubuntu-22.04",
            "zabbix_server_vmid": "200",
            "zabbix_server_cores": "4",
            "zabbix_server_memory": "4096",
        }
        gen.analyze_infrastructure()
        return gen

    def test_returns_true_when_all_ssh_succeed(self, tmp_path, sample_inventory_content):
        gen = self._gen_with_infra(tmp_path, sample_inventory_content)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = gen.validate_infrastructure()
        assert result is True

    def test_returns_false_when_ssh_fails(self, tmp_path, sample_inventory_content):
        gen = self._gen_with_infra(tmp_path, sample_inventory_content)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = gen.validate_infrastructure()
        assert result is False

    def test_returns_false_on_exception(self, tmp_path, sample_inventory_content):
        gen = self._gen_with_infra(tmp_path, sample_inventory_content)
        with patch("subprocess.run", side_effect=Exception("timeout")):
            result = gen.validate_infrastructure()
        assert result is False


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


class TestRun:
    def test_creates_output_files(self, tmp_path, sample_inventory_content, sample_tfvars_content):
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        (tf_dir / "terraform.tfvars").write_text(sample_tfvars_content)

        ans_dir = tmp_path / "ansible"
        inv_dir = ans_dir / "inventories"
        inv_dir.mkdir(parents=True)
        with open(inv_dir / "hosts.yml", "w") as f:
            yaml.dump(sample_inventory_content, f)

        gen = InfrastructureDocsGenerator(
            config_dir=str(tf_dir),
            ansible_dir=str(ans_dir),
            output_dir=str(tmp_path / "docs"),
        )

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "terraform")
            gen.run(validate=False)

        assert (tmp_path / "docs" / "ARCHITECTURE.md").exists()
        assert (tmp_path / "docs" / "QUICK_REFERENCE.md").exists()

    def test_run_with_validate(self, tmp_path, sample_inventory_content, sample_tfvars_content):
        tf_dir = tmp_path / "terraform"
        tf_dir.mkdir()
        (tf_dir / "terraform.tfvars").write_text(sample_tfvars_content)

        ans_dir = tmp_path / "ansible"
        inv_dir = ans_dir / "inventories"
        inv_dir.mkdir(parents=True)
        with open(inv_dir / "hosts.yml", "w") as f:
            yaml.dump(sample_inventory_content, f)

        gen = InfrastructureDocsGenerator(
            config_dir=str(tf_dir),
            ansible_dir=str(ans_dir),
            output_dir=str(tmp_path / "docs"),
        )

        with patch("subprocess.run") as mock_run:
            # terraform call fails, SSH validation succeeds
            def side_effect(cmd, **kwargs):
                if cmd[0] == "ssh":
                    return MagicMock(returncode=0)
                raise subprocess.CalledProcessError(1, "terraform")
            mock_run.side_effect = side_effect
            gen.run(validate=True)

        assert (tmp_path / "docs" / "ARCHITECTURE.md").exists()
