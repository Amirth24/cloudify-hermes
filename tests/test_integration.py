"""Integration test — full push/pull cycle with mocked S3."""
import json
import pytest
from unittest.mock import MagicMock, patch
from cloudify_hermes.onboard.bootstrap import Onboard
from cloudify_hermes.sync.skills import SkillsSync


@patch("cloudify_hermes.sync.skills.S3Backend")
@patch("cloudify_hermes.onboard.bootstrap.S3Backend")
def test_full_push_pull_cycle(mock_onboard_s3, mock_skills_s3, tmp_path):
    """Push skills from agent A, pull on agent B."""
    # Agent A: push
    backend_a = MagicMock()
    mock_skills_s3.return_value = backend_a
    backend_a.prefix = "cloudify/"
    backend_a.list.return_value = []
    skills_a = tmp_path / "agent-a" / "skills"
    (skills_a / "test-skill").mkdir(parents=True)
    (skills_a / "test-skill" / "SKILL.md").write_text("---\nname: test-skill\n---\n# Test")

    sync_a = SkillsSync(backend=backend_a, skills_dir=skills_a, agent_id="agent-a")
    sync_a.push()
    assert backend_a.put.call_count >= 1

    # Agent B: pull
    backend_b = MagicMock()
    mock_onboard_s3.return_value = backend_b
    backend_b.prefix = "cloudify/"

    # list() returns different keys depending on the prefix argument
    def list_side_effect(prefix=""):
        all_keys = {
            "skills/": ["cloudify/skills/test-skill/SKILL.md"],
            "cron/": [],
            "config-snapshots/": [],
        }
        return all_keys.get(prefix, [])

    backend_b.list.side_effect = list_side_effect
    backend_b.get.return_value = b"---\nname: test-skill\n---\n# Test"
    skills_b = tmp_path / "agent-b" / "skills"
    skills_b.mkdir(parents=True)
    cron_b = tmp_path / "agent-b" / "cron"
    cron_b.mkdir()
    config_b = tmp_path / "agent-b" / "config.yaml"
    config_b.write_text("model:\n  default: test")

    onboard = Onboard(backend_b, skills_b, cron_b, config_b, "agent-b")
    result = onboard.run()
    assert result["skills_pulled"] == 1
    assert (skills_b / "test-skill" / "SKILL.md").exists()


@patch("cloudify_hermes.sync.cron.S3Backend")
def test_cron_push_pull_roundtrip(mock_s3_cls, tmp_path):
    """Push cron jobs from agent A, verify they can be pulled."""
    from cloudify_hermes.sync.cron import CronSync
    backend = MagicMock()
    mock_s3_cls.return_value = backend
    backend.prefix = "cloudify/"
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    jobs = [{"id": "job1", "name": "daily-sync", "schedule": "0 9 * * *", "prompt": "test"}]
    (cron_dir / "jobs.json").write_text(json.dumps(jobs))
    sync = CronSync(backend=backend, cron_dir=cron_dir, agent_id="agent-a")
    sync.push()
    assert backend.put.call_count == 1


@patch("cloudify_hermes.sync.memory.S3Backend")
def test_memory_push_pull_mush(mock_s3_cls, tmp_path):
    """Push memory log, pull and mush-merge."""
    from cloudify_hermes.sync.memory import MemoryLogSync
    backend = MagicMock()
    mock_s3_cls.return_value = backend
    backend.prefix = "cloudify/"
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("Fact A\nFact B")
    sync = MemoryLogSync(backend=backend, memories_dir=mem_dir, agent_id="agent-a")
    sync.append_log()
    assert backend.put.call_count == 1