"""Tests for cloudify_hermes.config."""
from __future__ import annotations

import os

from cloudify_hermes.config import load_cloudify_config


def test_load_defaults_when_no_cloudify_section(tmp_hermes_home):
    """When config.yaml has no `cloudify` section, defaults are returned."""
    # tmp_hermes_home fixture writes an empty config.yaml
    cfg = load_cloudify_config()
    assert cfg["enabled"] is False
    assert cfg["s3"]["prefix"] == "cloudify/"
    assert cfg["s3"]["region"] == "ap-south-1"
    assert cfg["encryption"]["passphrase_env"] == "CLOUDIFY_PASSPHRASE"
    assert cfg["mem0"]["agent_id"] == "hermes"
    assert cfg["sync"]["skills"] is True
    assert cfg["hooks"]["post_tool_call"] is True


def test_load_defaults_when_missing_config_file(tmp_path, monkeypatch):
    """When no config.yaml exists at all, defaults are returned."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cfg = load_cloudify_config()
    assert cfg["enabled"] is False
    assert cfg["s3"]["bucket"] == ""


def test_merge_overrides(tmp_hermes_home):
    """User-provided cloudify keys override defaults, unspecified keys stay default."""
    (tmp_hermes_home / "config.yaml").write_text(
        "cloudify:\n"
        "  enabled: true\n"
        "  s3:\n"
        "    bucket: my-bucket\n"
        "    region: us-east-1\n"
    )
    cfg = load_cloudify_config()
    assert cfg["enabled"] is True
    assert cfg["s3"]["bucket"] == "my-bucket"
    assert cfg["s3"]["region"] == "us-east-1"
    # unspecified s3 defaults preserved
    assert cfg["s3"]["prefix"] == "cloudify/"
    assert cfg["s3"]["profile"] == ""