"""
Integration test fixtures.

Every fixture reads connection details from environment variables.
If the required env var is not set the fixture calls pytest.skip(),
so the test is reported as skipped rather than failed — no real services
are needed in the default developer workflow.

Set env vars before running:
    export NETBOX_URL=https://netbox.example.com
    export NETBOX_TOKEN=<token>
    export ZABBIX_URL=https://zabbix.example.com
    export ZABBIX_TOKEN=<api-token>
    export KEA_URL=http://kea-host:8000
    export TACHYON_IP=192.168.1.1
    export TACHYON_USERNAME=admin
    export TACHYON_PASSWORD=secret

Then run:
    make test-integration
"""

import os
import sys
import pytest
from pathlib import Path

# Make source modules importable
PROJECT_ROOT = Path(__file__).parent.parent.parent

for rel in (
    "scripts",
    "ansible/kea_dhcp/scripts",
    "ansible/zabbix/scripts",
    "ansible/oxidized/scripts",
):
    p = str(PROJECT_ROOT / rel)
    if p not in sys.path:
        sys.path.insert(0, p)


def _require_env(*names):
    """Return values for all env vars or skip the test if any is missing."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        pytest.skip(f"Required env vars not set: {', '.join(missing)}")
    return tuple(os.environ[n] for n in names)


# ---------------------------------------------------------------------------
# NetBox
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def nb_client():
    """Live pynetbox API client; skipped unless NETBOX_URL + NETBOX_TOKEN set."""
    url, token = _require_env("NETBOX_URL", "NETBOX_TOKEN")
    import pynetbox
    nb = pynetbox.api(url, token=token)
    nb.http_session.verify = False
    return nb


# ---------------------------------------------------------------------------
# Zabbix
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def zbx_client():
    """Live ZabbixAPI client; skipped unless ZABBIX_URL + ZABBIX_TOKEN set."""
    url, token = _require_env("ZABBIX_URL", "ZABBIX_TOKEN")
    from zabbix_utils import ZabbixAPI
    api = ZabbixAPI(url=url)
    api.login(token=token)
    yield api
    api.logout()


# ---------------------------------------------------------------------------
# Kea DHCP
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def kea_client():
    """Live Kea Control Agent client; skipped unless KEA_URL set."""
    (url,) = _require_env("KEA_URL")
    from pykeadhcp import Kea
    return Kea(host=url)


# ---------------------------------------------------------------------------
# Tachyon device
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tachyon_dev():
    """Live TachyonDevice; skipped unless TACHYON_IP/USERNAME/PASSWORD set."""
    ip, username, password = _require_env(
        "TACHYON_IP", "TACHYON_USERNAME", "TACHYON_PASSWORD"
    )
    from tachyon import TachyonDevice
    return TachyonDevice(ip, username, password)
