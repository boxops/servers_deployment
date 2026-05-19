"""
Unit tests for ansible/zabbix/scripts/snmpwalker.py

subprocess calls are mocked; file I/O uses tmp_path.
"""

import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call

# conftest.py adds ansible/zabbix/scripts to sys.path
from snmpwalker import SNMPWalker


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestSNMPWalkerInit:
    def test_stores_host(self):
        w = SNMPWalker("192.168.1.1", "public")
        assert w.host == "192.168.1.1"

    def test_stores_community(self):
        w = SNMPWalker("192.168.1.1", "private")
        assert w.community == "private"

    def test_default_version(self):
        w = SNMPWalker("192.168.1.1", "public")
        assert w.version == "2c"

    def test_custom_version(self):
        w = SNMPWalker("192.168.1.1", "public", version="1")
        assert w.version == "1"


# ---------------------------------------------------------------------------
# run_snmpwalk
# ---------------------------------------------------------------------------


class TestRunSnmpwalk:
    def test_calls_snmpwalk_with_correct_args(self, sample_snmpwalk_output):
        w = SNMPWalker("192.168.1.1", "public", "2c")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=sample_snmpwalk_output)
            w.run_snmpwalk("1.3.6.1.2.1")

        args = mock_run.call_args[0][0]
        assert "snmpwalk" in args
        assert "-v2c" in args
        assert "-c" in args
        assert "public" in args
        assert "192.168.1.1" in args
        assert "1.3.6.1.2.1" in args

    def test_returns_stripped_stdout(self, sample_snmpwalk_output):
        w = SNMPWalker("192.168.1.1", "public")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=sample_snmpwalk_output + "\n")
            result = w.run_snmpwalk("1.3.6.1.2.1")
        assert result == sample_snmpwalk_output.strip()

    def test_raises_runtime_error_on_failure(self):
        w = SNMPWalker("192.168.1.1", "public")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="No response")
            with pytest.raises(RuntimeError, match="snmpwalk failed"):
                w.run_snmpwalk("1.3.6.1.2.1")

    def test_version_passed_as_flag(self):
        w = SNMPWalker("10.0.0.1", "public", "1")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            w.run_snmpwalk("1.3.6.1")
        args = mock_run.call_args[0][0]
        assert "-v1" in args


# ---------------------------------------------------------------------------
# save_snmpwalk_output
# ---------------------------------------------------------------------------


class TestSaveSnmpwalkOutput:
    def test_writes_output_to_file(self, tmp_path, sample_snmpwalk_output):
        out_file = tmp_path / "output.txt"
        w = SNMPWalker("192.168.1.1", "public")
        w.save_snmpwalk_output(sample_snmpwalk_output, str(out_file))
        assert out_file.read_text() == sample_snmpwalk_output

    def test_prints_confirmation(self, tmp_path, sample_snmpwalk_output, capsys):
        out_file = tmp_path / "output.txt"
        w = SNMPWalker("192.168.1.1", "public")
        w.save_snmpwalk_output(sample_snmpwalk_output, str(out_file))
        captured = capsys.readouterr()
        assert "saved" in captured.out.lower()

    def test_default_filename(self, tmp_path, sample_snmpwalk_output, monkeypatch):
        monkeypatch.chdir(tmp_path)
        w = SNMPWalker("192.168.1.1", "public")
        w.save_snmpwalk_output(sample_snmpwalk_output)
        assert (tmp_path / "snmpwalk_output.txt").exists()


# ---------------------------------------------------------------------------
# parse_snmpwalk_output (static)
# ---------------------------------------------------------------------------


class TestParseSnmpwalkOutput:
    def test_parses_known_output(self, sample_snmpwalk_output, sample_snmpwalk_parsed):
        result = SNMPWalker.parse_snmpwalk_output(sample_snmpwalk_output)
        assert result == sample_snmpwalk_parsed

    def test_replaces_iso_with_1(self):
        output = "iso.3.6.1.2.1.1.1.0 = STRING: hello\n"
        result = SNMPWalker.parse_snmpwalk_output(output)
        assert "1.3.6.1.2.1.1.1.0" in result

    def test_skips_lines_without_equals(self):
        output = "no equals here\n1.2.3.0 = STRING: yes\n"
        result = SNMPWalker.parse_snmpwalk_output(output)
        assert "no equals here" not in result
        assert "1.2.3.0" in result

    def test_empty_input_returns_empty_dict(self):
        result = SNMPWalker.parse_snmpwalk_output("")
        assert result == {}

    def test_multiple_equals_in_value(self):
        output = "1.2.3.0 = STRING: key=value=extra\n"
        result = SNMPWalker.parse_snmpwalk_output(output)
        assert result["1.2.3.0"] == "STRING: key=value=extra"

    def test_strips_whitespace_from_keys(self):
        output = "  1.2.3.0  = STRING: trimmed\n"
        result = SNMPWalker.parse_snmpwalk_output(output)
        assert "1.2.3.0" in result


# ---------------------------------------------------------------------------
# load_snmpwalk_from_file (static)
# ---------------------------------------------------------------------------


class TestLoadSnmpwalkFromFile:
    def test_loads_file_content(self, tmp_path, sample_snmpwalk_output):
        f = tmp_path / "walk.txt"
        f.write_text(sample_snmpwalk_output)
        result = SNMPWalker.load_snmpwalk_from_file(str(f))
        assert result == sample_snmpwalk_output

    def test_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            SNMPWalker.load_snmpwalk_from_file("/nonexistent/path/walk.txt")

    def test_empty_file_returns_empty_string(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = SNMPWalker.load_snmpwalk_from_file(str(f))
        assert result == ""


# ---------------------------------------------------------------------------
# Round-trip: save → load → parse
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_save_load_parse_roundtrip(self, tmp_path, sample_snmpwalk_output, sample_snmpwalk_parsed):
        out_file = tmp_path / "walk.txt"
        w = SNMPWalker("192.168.1.1", "public")
        w.save_snmpwalk_output(sample_snmpwalk_output, str(out_file))
        loaded = SNMPWalker.load_snmpwalk_from_file(str(out_file))
        parsed = SNMPWalker.parse_snmpwalk_output(loaded)
        assert parsed == sample_snmpwalk_parsed
