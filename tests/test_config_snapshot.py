import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cloudify_hermes.sync.config_snapshot import ConfigSnapshot, strip_secrets

def test_strip_secrets_removes_api_keys():
    config = {
        "model": {"api_key": "sk-secret123"},
        "providers": {"openai": {"api_key": "sk-abc"}},
        "mcp_servers": {"github": {"env": {"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_secret"}}},
        "memory": {"provider": "openviking"},
        "display": {"personality": "technical"},
    }
    stripped = strip_secrets(config)
    assert "api_key" not in stripped.get("model", {})
    assert "api_key" not in stripped.get("providers", {}).get("openai", {})
    assert "GITHUB_PERSONAL_ACCESS_TOKEN" not in stripped.get("mcp_servers", {}).get("github", {}).get("env", {})
    assert stripped["memory"]["provider"] == "openviking"
    assert stripped["display"]["personality"] == "technical"

def test_strip_secrets_preserves_non_secret_keys():
    config = {"model": {"default": "glm-5.2", "api_key": "secret"}, "agent": {"max_turns": 90}}
    stripped = strip_secrets(config)
    assert stripped["model"]["default"] == "glm-5.2"
    assert "api_key" not in stripped["model"]
    assert stripped["agent"]["max_turns"] == 90

@patch("cloudify_hermes.sync.config_snapshot.S3Backend")
def test_config_snapshot_push(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({
        "model": {"default": "test", "api_key": "secret"},
        "memory": {"provider": "openviking"},
    }))
    snap = ConfigSnapshot(backend=mock_backend, config_path=config_file, agent_id="test")
    snap.snapshot()
    mock_backend.put.assert_called_once()
    args = mock_backend.put.call_args
    assert "config-snapshots/" in args[0][0]
    uploaded = yaml.safe_load(args[1]["data"].decode())
    assert "api_key" not in uploaded.get("model", {})

@patch("cloudify_hermes.sync.config_snapshot.S3Backend")
def test_config_snapshot_pull_latest(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    mock_backend.prefix = "cloudify/"
    mock_backend.list.return_value = ["cloudify/config-snapshots/2026-07-19T10-00-00Z.yaml"]
    mock_backend.get.return_value = yaml.dump({"memory": {"provider": "mem0"}}).encode()
    snap = ConfigSnapshot(backend=mock_backend, config_path=tmp_path / "config.yaml", agent_id="test")
    result = snap.pull_latest()
    assert result is not None
    assert result["memory"]["provider"] == "mem0"