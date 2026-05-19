"""
Unit tests for ansible/oxidized/scripts/tachyon.py

All HTTP requests are intercepted with the responses library so no real
network connectivity is required.
"""

import json
import pytest
import responses as responses_lib
from unittest.mock import MagicMock, patch
from requests.exceptions import RequestException

# conftest.py adds ansible/oxidized/scripts to sys.path
from tachyon import TachyonDevice


BASE_URL = "https://192.168.1.1/cgi.lua/apiv1"


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestTachyonDeviceInit:
    def test_base_url_constructed(self):
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        assert device.base_url == "https://192.168.1.1/cgi.lua/apiv1"

    def test_stores_credentials(self):
        device = TachyonDevice("10.0.0.1", "user", "secret")
        assert device.username == "user"
        assert device.password == "secret"

    def test_token_starts_none(self):
        device = TachyonDevice("10.0.0.1", "u", "p")
        assert device.token is None

    def test_verbose_default_false(self):
        device = TachyonDevice("10.0.0.1", "u", "p")
        assert device.verbose is False

    def test_verbose_can_be_set(self):
        device = TachyonDevice("10.0.0.1", "u", "p", verbose=True)
        assert device.verbose is True


# ---------------------------------------------------------------------------
# _debug
# ---------------------------------------------------------------------------


class TestDebug:
    def test_prints_when_verbose(self, capsys):
        device = TachyonDevice("10.0.0.1", "u", "p", verbose=True)
        device._debug("hello debug")
        captured = capsys.readouterr()
        assert "hello debug" in captured.out

    def test_silent_when_not_verbose(self, capsys):
        device = TachyonDevice("10.0.0.1", "u", "p", verbose=False)
        device._debug("silent message")
        captured = capsys.readouterr()
        assert "silent message" not in captured.out


# ---------------------------------------------------------------------------
# _handle_response
# ---------------------------------------------------------------------------


class TestHandleResponse:
    def test_returns_parsed_json(self):
        device = TachyonDevice("10.0.0.1", "u", "p")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"token": "abc"}
        mock_resp.text = '{"token": "abc"}'
        result = device._handle_response(mock_resp)
        assert result == {"token": "abc"}

    def test_raises_on_invalid_json(self):
        device = TachyonDevice("10.0.0.1", "u", "p")
        mock_resp = MagicMock()
        mock_resp.json.side_effect = json.JSONDecodeError("err", "doc", 0)
        mock_resp.text = "not json"
        with pytest.raises(Exception, match="Invalid JSON"):
            device._handle_response(mock_resp)

    def test_raises_on_error_field(self):
        device = TachyonDevice("10.0.0.1", "u", "p")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": {"details": "Unauthorized"}}
        with pytest.raises(Exception, match="Unauthorized"):
            device._handle_response(mock_resp)

    def test_raises_on_error_without_details(self):
        device = TachyonDevice("10.0.0.1", "u", "p")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"error": {}}
        with pytest.raises(Exception, match="Unknown error"):
            device._handle_response(mock_resp)


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


class TestLogin:
    @responses_lib.activate
    def test_successful_login_stores_token(self, tachyon_login_response):
        responses_lib.add(
            responses_lib.POST,
            f"{BASE_URL}/login",
            json=tachyon_login_response,
            status=200,
        )
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        assert device.token == "abc123token"

    @responses_lib.activate
    def test_successful_login_sets_session_cookie(self, tachyon_login_response):
        responses_lib.add(
            responses_lib.POST,
            f"{BASE_URL}/login",
            json=tachyon_login_response,
            status=200,
        )
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        assert "Cookie" in device.session.headers
        assert "abc123token" in device.session.headers["Cookie"]

    @responses_lib.activate
    def test_login_raises_on_request_exception(self):
        responses_lib.add(
            responses_lib.POST,
            f"{BASE_URL}/login",
            body=RequestException("connection refused"),
        )
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        with pytest.raises(Exception, match="Login failed"):
            device.login()

    @responses_lib.activate
    def test_login_raises_on_api_error(self):
        responses_lib.add(
            responses_lib.POST,
            f"{BASE_URL}/login",
            json={"error": {"details": "Bad credentials"}},
            status=200,
        )
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        with pytest.raises(Exception, match="Bad credentials"):
            device.login()


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


class TestLogout:
    @responses_lib.activate
    def test_logout_clears_token(self, tachyon_login_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.DELETE, f"{BASE_URL}/login", status=200)
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        device.logout()
        assert device.token is None

    @responses_lib.activate
    def test_logout_removes_cookie_header(self, tachyon_login_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.DELETE, f"{BASE_URL}/login", status=200)
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        device.logout()
        assert "Cookie" not in device.session.headers

    def test_logout_without_token_does_not_raise(self):
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.logout()  # token is None – should be a no-op

    @responses_lib.activate
    def test_logout_handles_request_exception_gracefully(self, tachyon_login_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.DELETE, f"{BASE_URL}/login",
                          body=RequestException("network error"))
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        device.logout()  # should not raise
        assert device.token is None


# ---------------------------------------------------------------------------
# fetch_config
# ---------------------------------------------------------------------------


class TestFetchConfig:
    @responses_lib.activate
    def test_returns_config_dict(self, tachyon_login_response, tachyon_config_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.GET, f"{BASE_URL}/config",
                          json=tachyon_config_response, status=200)
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        result = device.fetch_config()
        assert "config" in result
        assert result["config"]["system"]["hostname"] == "test-device"

    @responses_lib.activate
    def test_raises_on_request_failure(self, tachyon_login_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.GET, f"{BASE_URL}/config",
                          body=RequestException("timeout"))
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        with pytest.raises(Exception, match="Failed to fetch config"):
            device.fetch_config()


# ---------------------------------------------------------------------------
# push_config
# ---------------------------------------------------------------------------


class TestPushConfig:
    @responses_lib.activate
    def test_pushes_config_and_returns_response(self, tachyon_login_response, tachyon_push_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/config",
                          json=tachyon_push_response, status=200)
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        result = device.push_config({"system": {}})
        assert result["status_msg"] == "OK"

    @responses_lib.activate
    def test_dry_run_flag_sent(self, tachyon_login_response, tachyon_push_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/config",
                          json=tachyon_push_response, status=200)
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        device.push_config({"system": {}}, dry_run=True)
        last_call_body = json.loads(responses_lib.calls[-1].request.body)
        assert last_call_body["dry_run"] is True

    @responses_lib.activate
    def test_raises_on_request_failure(self, tachyon_login_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/config",
                          body=RequestException("timeout"))
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        with pytest.raises(Exception, match="Failed to push config"):
            device.push_config({"system": {}})


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------


class TestGetStats:
    @responses_lib.activate
    def test_returns_stats_dict(self, tachyon_login_response):
        stats = {"system": {"uptime": 12345}, "wireless": {}, "network": {}, "ethernet": {}}
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(
            responses_lib.GET,
            f"{BASE_URL}/stats",
            json=stats,
            status=200,
        )
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        result = device.get_stats()
        assert "system" in result

    @responses_lib.activate
    def test_raises_on_failure(self, tachyon_login_response):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.GET, f"{BASE_URL}/stats",
                          body=RequestException("timeout"))
        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.login()
        with pytest.raises(Exception, match="Failed to fetch stats"):
            device.get_stats()


# ---------------------------------------------------------------------------
# set_hostname / change_hostname
# ---------------------------------------------------------------------------


class TestSetHostname:
    def test_updates_hostname_in_config(self):
        device = TachyonDevice("10.0.0.1", "admin", "pass")
        config = {"system": {"hostname": "old-name"}}
        result = device.set_hostname(config, "new-name")
        assert result["system"]["hostname"] == "new-name"

    def test_returns_config_dict(self):
        device = TachyonDevice("10.0.0.1", "admin", "pass")
        config = {"system": {"hostname": "old"}}
        result = device.set_hostname(config, "new")
        assert isinstance(result, dict)


class TestChangeHostname:
    @responses_lib.activate
    def test_change_hostname_end_to_end(
        self, tachyon_login_response, tachyon_config_response, tachyon_push_response
    ):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.GET, f"{BASE_URL}/config",
                          json=tachyon_config_response, status=200)
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/config",
                          json=tachyon_push_response, status=200)
        responses_lib.add(responses_lib.DELETE, f"{BASE_URL}/login", status=200)

        device = TachyonDevice("192.168.1.1", "admin", "pass")
        device.change_hostname("new-hostname")
        # Verify push was called (no assertion error raised means test passed)
        assert len(responses_lib.calls) == 4

    @responses_lib.activate
    def test_change_hostname_logs_out_on_failure(
        self, tachyon_login_response, tachyon_config_response
    ):
        responses_lib.add(responses_lib.POST, f"{BASE_URL}/login",
                          json=tachyon_login_response, status=200)
        responses_lib.add(responses_lib.GET, f"{BASE_URL}/config",
                          body=Exception("network error"))
        responses_lib.add(responses_lib.DELETE, f"{BASE_URL}/login", status=200)

        device = TachyonDevice("192.168.1.1", "admin", "pass")
        with pytest.raises(Exception):
            device.change_hostname("new-hostname")
        # logout should still have been called (token cleared)
        assert device.token is None
