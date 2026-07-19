import json
import yaml
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cloudify_hermes.onboard.bootstrap import Onboard


def _make_backend(mock_s3_cls, skill_bytes=b"---\nname: test-skill\n---\n# Test"):
    """Build a prefix-aware mock backend."""
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    mock_backend.prefix = "cloudify/"

    def _list(prefix=""):
        if prefix.startswith("skills"):
            return ["cloudify/skills/test-skill/SKILL.md"]
        if prefix.startswith("cron"):
            return []
        if prefix.startswith("config-snapshots"):
            return []
        return []

    def _get(key):
        if key.endswith("SKILL.md"):
            return skill_bytes
        return None

    mock_backend.list.side_effect = _list
    mock_backend.get.side_effect = _get
    return mock_backend


@patch("cloudify_hermes.onboard.bootstrap.S3Backend")
def test_onboard_pulls_skills(mock_s3_cls, tmp_path):
    mock_backend = _make_backend(mock_s3_cls)
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("model:\n  default: test")
    onboard = Onboard(
        backend=mock_backend,
        skills_dir=skills_dir,
        cron_dir=cron_dir,
        config_path=config_path,
        agent_id="new-agent",
    )
    result = onboard.run()
    assert result["skills_pulled"] == 1
    assert (skills_dir / "test-skill" / "SKILL.md").exists()


@patch("cloudify_hermes.onboard.bootstrap.S3Backend")
def test_onboard_is_idempotent(mock_s3_cls, tmp_path):
    mock_backend = _make_backend(mock_s3_cls)
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    config_path = tmp_path / "config.yaml"
    config_path.write_text("model:\n  default: test")
    onboard = Onboard(mock_backend, skills_dir, cron_dir, config_path, "new-agent")
    result1 = onboard.run()
    result2 = onboard.run()
    assert result1["skills_pulled"] == 1
    assert result2["skills_pulled"] == 0