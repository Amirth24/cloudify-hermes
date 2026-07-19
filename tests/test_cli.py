"""Tests for cloudify_hermes.cli — CLI entry point."""
import pytest
from unittest.mock import patch, MagicMock
from cloudify_hermes.cli import cmd_status, main


def test_cmd_status_shows_config(capsys, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", "/tmp/fake-hermes")
    with patch("cloudify_hermes.cli.load_cloudify_config") as mock_cfg:
        mock_cfg.return_value = {
            "enabled": True,
            "s3": {
                "bucket": "test-bucket",
                "prefix": "cloudify/",
                "region": "ap-south-1",
                "profile": "",
            },
            "mem0": {
                "agent_id": "test-agent",
                "user_id": "amirth",
                "api_key_env": "MEM0_API_KEY",
                "knowledge_graphs": {},
            },
            "sync": {"skills": True, "cron": True, "memory": True, "config": True, "viking": True},
            "hooks": {"post_tool_call": True, "on_session_end": True},
        }
        cmd_status(MagicMock())
        captured = capsys.readouterr()
        assert "Enabled: True" in captured.out
        assert "test-bucket" in captured.out
        assert "test-agent" in captured.out


def test_cli_main_no_args_exits():
    with pytest.raises(SystemExit):
        main()