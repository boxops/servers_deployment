"""
Integration tests for Tachyon device connectivity.

Requires:
    TACHYON_IP=192.168.1.1
    TACHYON_USERNAME=admin
    TACHYON_PASSWORD=secret

Run:
    make test-integration
    # or just Tachyon:
    pytest tests/integration/test_tachyon.py -v -m integration
"""

import pytest


pytestmark = pytest.mark.integration


class TestTachyonConnectivity:
    def test_login_sets_token(self, tachyon_dev):
        """Successful login populates self.token."""
        tachyon_dev.login()
        assert tachyon_dev.token is not None
        tachyon_dev.logout()

    def test_logout_clears_token(self, tachyon_dev):
        """After logout token is None."""
        tachyon_dev.login()
        tachyon_dev.logout()
        assert tachyon_dev.token is None

    def test_double_logout_does_not_raise(self, tachyon_dev):
        """Calling logout when already logged out is safe."""
        tachyon_dev.login()
        tachyon_dev.logout()
        tachyon_dev.logout()  # second call — should not raise


class TestTachyonConfig:
    def test_fetch_config_returns_dict(self, tachyon_dev):
        """fetch_config() returns a dict with a 'config' key."""
        tachyon_dev.login()
        try:
            data = tachyon_dev.fetch_config()
            assert isinstance(data, dict)
            assert "config" in data
        finally:
            tachyon_dev.logout()

    def test_config_has_system_section(self, tachyon_dev):
        """config['system'] is present and contains a hostname key."""
        tachyon_dev.login()
        try:
            data = tachyon_dev.fetch_config()
            config = data.get("config", {})
            assert "system" in config
            assert "hostname" in config["system"]
        finally:
            tachyon_dev.logout()

    def test_set_hostname_does_not_push(self, tachyon_dev):
        """set_hostname mutates a config dict in-place without making an API call."""
        tachyon_dev.login()
        try:
            data = tachyon_dev.fetch_config()
            config = data.get("config", {})
            original = config["system"]["hostname"]
            modified = tachyon_dev.set_hostname(config, "__test_hostname__")
            assert modified["system"]["hostname"] == "__test_hostname__"
            # Restore the original name (no push — just in-memory)
            tachyon_dev.set_hostname(config, original)
        finally:
            tachyon_dev.logout()


class TestTachyonStats:
    def test_get_stats_returns_dict(self, tachyon_dev):
        """get_stats() returns a non-empty dict."""
        tachyon_dev.login()
        try:
            stats = tachyon_dev.get_stats()
            assert isinstance(stats, dict)
            assert len(stats) > 0
        finally:
            tachyon_dev.logout()
