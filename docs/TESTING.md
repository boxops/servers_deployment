# Testing Guide

This document describes the test suite for the `servers_deployment` project,
how to run tests locally, and how to write new tests.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Running Tests](#running-tests)
3. [Integration Tests](#integration-tests)
4. [Terraform Testing](#terraform-testing)
5. [Ansible Testing](#ansible-testing)
6. [Test Structure](#test-structure)
7. [Coverage](#coverage)
8. [Writing New Tests](#writing-new-tests)
9. [Fixtures Reference](#fixtures-reference)
10. [CI Integration](#ci-integration)

---

## Prerequisites

All test and lint dependencies are included in `requirements.txt`. Install them
(preferably into a virtual environment) with:

```bash
# Recommended: let make manage the venv automatically
make venv

# Or manually
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Key dependencies:

| Package | Version | Purpose |
|---|---|---|
| `pytest` | ≥ 7.4.0 | Test runner |
| `pytest-cov` | ≥ 4.1.0 | Coverage measurement |
| `pytest-mock` | ≥ 3.12.0 | `mocker` fixture for mocking |
| `responses` | ≥ 0.23.0 | HTTP request mocking (Tachyon tests) |
| `faker` | ≥ 20.0.0 | Fake data generation in fixtures |
| `ansible-lint` | ≥ 6.22.0 | Ansible playbook/role linting |
| `yamllint` | ≥ 1.33.0 | YAML formatting lint |
| `checkov` | ≥ 3.0.0 | Terraform + Ansible security scanning |

`tflint` is a standalone binary (not pip-installable). See [Terraform Testing](#terraform-testing).

---

## Running Tests

All commands are available via `make`. Tabs in the Makefile are required.

| Command | Description |
|---|---|
| `make test` | Run unit tests (mocked — no real services needed) |
| `make test-cov` | Run unit tests and show per-line coverage in the terminal |
| `make test-report` | Run unit tests and generate an HTML coverage report in `htmlcov/` |
| `make test-integration` | Run integration tests against real services (requires env vars) |
| `make test-clean` | Remove `.coverage`, `htmlcov/`, `.pytest_cache/`, and `__pycache__` dirs |
| `make lint` | Run all static analysis (Terraform + Ansible) |
| `make lint-terraform` | Terraform fmt-check + validate + checkov |
| `make lint-ansible` | ansible-lint + yamllint across `ansible/` |
| `make ansible-syntax-check` | Syntax-check every `deploy.yml` playbook |

You can also run pytest directly for more control:

```bash
# Run a single test file
python3 -m pytest tests/zabbix/test_snmpwalker.py -v

# Run tests matching a keyword
python3 -m pytest -k "TestLogin" -v -m "not integration"

# Run only unit-marked tests
python3 -m pytest -m unit -v

# Run with coverage for a specific source module
python3 -m pytest tests/oxidized/ --cov=ansible/oxidized/scripts --cov-report=term-missing -m "not integration"
```

---

## Integration Tests

Integration tests live in `tests/integration/` and are marked `@pytest.mark.integration`.
They connect to **real running services** and are skipped automatically if the required
environment variables are not set.

### Environment Variables

| Variable | Required by | Description |
|---|---|---|
| `NETBOX_URL` | NetBox tests | Full URL, e.g. `https://netbox.example.com` |
| `NETBOX_TOKEN` | NetBox tests | API token |
| `ZABBIX_URL` | Zabbix tests | Full URL, e.g. `https://zabbix.example.com` |
| `ZABBIX_TOKEN` | Zabbix tests | API token |
| `KEA_URL` | Kea DHCP tests | Control Agent URL, e.g. `http://kea-host:8000` |
| `TACHYON_IP` | Tachyon tests | Device IP address |
| `TACHYON_USERNAME` | Tachyon tests | Login username |
| `TACHYON_PASSWORD` | Tachyon tests | Login password |

### Running integration tests

```bash
# Run all integration tests (skipped unless env vars are set)
make test-integration

# Run only against one service
export NETBOX_URL=https://netbox.example.com
export NETBOX_TOKEN=abc123
pytest tests/integration/test_netbox.py -v -m integration

# Run with all services configured
export NETBOX_URL=...  NETBOX_TOKEN=...
export ZABBIX_URL=...  ZABBIX_TOKEN=...
export KEA_URL=...
export TACHYON_IP=... TACHYON_USERNAME=... TACHYON_PASSWORD=...
make test-integration
```

### What each file tests

| File | Service | Tests |
|---|---|---|
| `tests/integration/test_netbox.py` | NetBox | API reachability, list devices, IP ranges, prefixes, lookup by name |
| `tests/integration/test_zabbix.py` | Zabbix | API version, list hosts/templates/groups, host lookup |
| `tests/integration/test_kea_dhcp.py` | Kea DHCP | config-get, version-get, subnet4 structure, lease list |
| `tests/integration/test_tachyon.py` | Tachyon device | login/logout, fetch_config, set_hostname (in-memory only), get_stats |

### Behaviour when env vars are missing

`pytest.skip()` is called rather than failing, so `make test-integration` always exits 0
when no services are configured. The test report shows skipped counts rather than failures.

---

## Terraform Testing

Terraform testing is **fully offline** — no real Proxmox credentials are needed.

### Tools

| Tool | Install | What it checks |
|---|---|---|
| `terraform fmt -check` | `terraform` binary (already required) | HCL formatting |
| `terraform validate` | `terraform` binary | Syntax and type errors |
| `checkov` | `pip install checkov` (in `requirements.txt`) | Security policy violations |
| `tflint` | Binary — see below | Provider-specific rules |

### Installing tflint (optional)

```bash
# Linux (amd64)
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash

# macOS
brew install tflint

# After install, fetch the proxmox plugin rules:
tflint --init
```

`make lint-terraform` skips `tflint` with a warning if it is not installed; all other checks
still run.

### Running Terraform checks

```bash
make lint-terraform          # fmt-check + validate + checkov + tflint (if installed)
make terraform-fmt-check     # formatting only
make terraform-validate-all  # validate all 6 modules (uses -backend=false)
```

### Terraform modules checked

All modules under `terraform/` are validated:
- `terraform/example`
- `terraform/PVE-HOME/pve-home-clab01`
- `terraform/PVE-HOME/pve-home-n8n01`
- `terraform/PVE-HOME/pve-home-nbox01`
- `terraform/PVE-HOME/pve-home-netobs01`
- `terraform/PVE-HOME/pve-home-zt-netops01`

### checkov soft-fail

`checkov` is run with `--soft-fail` so existing violations are reported but do not block
other commands. Once violations are remediated, remove `--soft-fail` from the Makefile target
to enforce clean scans.

---

## Ansible Testing

Ansible testing uses lint tools only — no Docker, no real hosts, no Molecule.

### Tools

| Tool | Install | What it checks |
|---|---|---|
| `ansible-lint` | `pip install ansible-lint` (in `requirements.txt`) | Best practices, idempotency patterns, FQCN |
| `yamllint` | `pip install yamllint` (in `requirements.txt`) | YAML formatting and syntax |
| `ansible-playbook --syntax-check` | `ansible` binary | Playbook parse errors |

### Configuration

**`.ansible-lint`** (project root) — `profile: basic`. Skips:
- `command-instead-of-module` — many roles use `command:` for tools with no module equivalent
  (`dpkg`, `rndc`, `ipa-client-install`, etc.)
- `no-changed-when` — intentional in handler-driven tasks
- `yaml[line-length]` — delegated to yamllint

**`.yamllint.yml`** (project root) — extends default ruleset. Key overrides:
- `line-length`: max 160 (warning) — long `when:` conditions are common
- `truthy`: accepts both `true/false` and `yes/no`

### Running Ansible checks

```bash
make lint-ansible          # ansible-lint + yamllint
make ansible-syntax-check  # syntax-check every deploy.yml and deploy_server.yml
make lint                  # everything: lint-terraform + lint-ansible
```

---

## Test Structure

```
tests/
├── conftest.py                   # Shared pytest fixtures
├── __init__.py
├── test_generate_docs.py         # scripts/generate-docs.py
├── kea_dhcp/
│   ├── __init__.py
│   └── test_generate_subnet4.py  # ansible/kea_dhcp/scripts/generate_subnet4_from_netbox.py
├── oxidized/
│   ├── __init__.py
│   └── test_tachyon.py           # ansible/oxidized/scripts/tachyon.py
└── zabbix/
    ├── __init__.py
    ├── test_export_host_templates.py  # ansible/zabbix/scripts/export_host_templates.py
    ├── test_host_template_generator.py # ansible/zabbix/scripts/host_template_generator.py
    ├── test_import_host_templates.py  # ansible/zabbix/scripts/import_host_templates.py
    ├── test_snmpwalker.py             # ansible/zabbix/scripts/snmpwalker.py
    └── test_sync_devices.py           # ansible/zabbix/scripts/sync_devices_from_netbox.py
```

Coverage is measured across four source trees:

- `scripts/`
- `ansible/kea_dhcp/scripts/`
- `ansible/zabbix/scripts/`
- `ansible/oxidized/scripts/`

The minimum acceptable coverage is **80%** (enforced by `pytest-cov`'s
`fail_under` setting in `pytest.ini`).

---

## Coverage

After `make test-report`, open `htmlcov/index.html` in your browser:

```bash
make test-report
xdg-open htmlcov/index.html   # Linux
open htmlcov/index.html        # macOS
```

The terminal summary is also printed when running `make test-cov`.

Lines excluded from coverage (configured in `pytest.ini`):
- `if __name__ == "__main__":` guards
- `pass` statements
- `raise NotImplementedError`
- Lines marked with `# pragma: no cover`

---

## Writing New Tests

### File naming

| Source file location | Test file location |
|---|---|
| `scripts/foo.py` | `tests/test_foo.py` |
| `ansible/<service>/scripts/bar.py` | `tests/<service>/test_bar.py` |

### Importing source modules

`tests/conftest.py` adds all four script directories to `sys.path` at
collection time, so you can import source modules directly:

```python
from snmpwalker import SNMPWalker
from tachyon import TachyonDevice
```

The only exception is `scripts/generate-docs.py` (hyphen in name), which must
be imported via `importlib`:

```python
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "generate_docs",
    Path(__file__).parent.parent / "scripts" / "generate-docs.py",
)
generate_docs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_docs)
InfrastructureDocsGenerator = generate_docs.InfrastructureDocsGenerator
```

### Mocking external services

All tests are unit tests — no real service connectivity is required.

**NetBox** (`pynetbox`):
```python
from unittest.mock import MagicMock, patch

with patch("module_under_test.NetboxAPI") as MockAPI:
    conn = MagicMock()
    MockAPI.return_value = conn
    client = NetBoxClient("http://netbox.local", "tok")
conn.dcim.devices.filter.return_value = [mock_device]
```

**Zabbix** (`zabbix-utils`):
```python
with patch("module_under_test.ZabbixAPI") as MockAPI:
    conn = MagicMock()
    MockAPI.return_value = conn
    client = ZabbixClient("http://zabbix.local", "tok")
conn.host.get.return_value = [{"hostid": "10001"}]
```

**HTTP requests** (`requests.Session`, used in `tachyon.py`):
```python
import responses

@responses.activate
def test_something():
    responses.add(responses.GET, "https://device/cgi.lua/apiv1/config",
                  json={"config": {}}, status=200)
    device = TachyonDevice("device", "admin", "pass")
    # ... assertions
```

**Subprocess** (used in `generate-docs.py` and `snmpwalker.py`):
```python
from unittest.mock import patch

with patch("subprocess.run") as mock_run:
    mock_run.return_value.stdout = "output"
    mock_run.return_value.returncode = 0
    # ... call code under test
```

### Filesystem operations

Use `tmp_path` (pytest built-in) or `monkeypatch.chdir` for code that writes files:

```python
def test_writes_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    manager.generate_subnet4()   # writes subnet4.json to cwd
    assert (tmp_path / "subnet4.json").exists()
```

### Pytest markers

Mark tests with the appropriate marker from `pytest.ini`:

```python
@pytest.mark.unit
def test_something(): ...

@pytest.mark.integration   # for tests that need real services
def test_real_netbox(): ...
```

---

## Fixtures Reference

All shared fixtures live in `tests/conftest.py`.

| Fixture | Type | Description |
|---|---|---|
| `mock_netbox_ip_ranges` | `list[dict]` | Two IP range dicts (`192.168.1.0/24`, `10.0.0.0/8`) |
| `mock_netbox_ip_address_factory` | factory | Creates mock pynetbox IP address objects |
| `mock_netbox_prefix_factory` | factory | Creates mock pynetbox prefix objects |
| `mock_netbox_device` | `MagicMock` | Single device: `test-router-01`, IP `192.168.1.100/32` |
| `mock_kea_config` | `dict` | Minimal valid Kea DHCP4 config |
| `mock_kea_result_ok` | `dict` | Successful Kea API result (`{"result": 0}`) |
| `mock_zabbix_host` | `dict` | Single Zabbix host dict (`hostid: "10001"`) |
| `mock_zabbix_template` | `dict` | Single Zabbix template dict (`templateid: "10563"`) |
| `mock_zabbix_group` | `dict` | Single Zabbix group dict (`groupid: "5"`) |
| `tachyon_login_response` | `dict` | `{"token": "abc123token"}` |
| `tachyon_config_response` | `dict` | Config with hostname `test-device` |
| `tachyon_push_response` | `dict` | `{"status_msg": "OK", ...}` |
| `sample_tfvars_content` | `str` | Minimal `terraform.tfvars` content |
| `sample_inventory_content` | `str` | Ansible hosts.yml (1 server + 1 proxy) |
| `sample_snmpwalk_output` | `str` | Raw snmpwalk output lines |
| `sample_snmpwalk_parsed` | `list[dict]` | Parsed version of `sample_snmpwalk_output` |
| `sample_csv_content` | `str` | MIB walk CSV for template generator tests |

---

## CI Integration

To integrate with a CI pipeline (GitHub Actions, GitLab CI, etc.), add a step
that runs:

```bash
pip install -r requirements.txt
python3 -m pytest tests/ --cov --cov-report=xml
```

The `coverage.xml` file can be uploaded to coverage services such as Codecov or
Coveralls, or used to generate diff-coverage reports in pull requests.

Example GitHub Actions step:

```yaml
- name: Run tests
  run: |
    pip install -r requirements.txt
    python3 -m pytest tests/ --cov --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: coverage.xml
```
