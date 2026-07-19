import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cloudify_hermes.sync.skills import SkillsSync, should_sync_skill, parse_frontmatter

def test_should_sync_skill_default_true(tmp_path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: test\ndescription: test\n---\n# Test")
    assert should_sync_skill(skill_md) is True

def test_should_sync_skill_opt_out(tmp_path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("---\nname: test\ndescription: test\ncloudify: false\n---\n# Test")
    assert should_sync_skill(skill_md) is False

def test_should_sync_skill_no_frontmatter(tmp_path):
    skill_md = tmp_path / "SKILL.md"
    skill_md.write_text("# No frontmatter here")
    assert should_sync_skill(skill_md) is True

@patch("cloudify_hermes.sync.skills.S3Backend")
def test_skills_push_uploads_syncable_skills(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    skills_dir = tmp_path / "skills"
    (skills_dir / "syncable").mkdir(parents=True)
    (skills_dir / "syncable" / "SKILL.md").write_text("---\nname: syncable\n---\n# Sync")
    (skills_dir / "local-only").mkdir(parents=True)
    (skills_dir / "local-only" / "SKILL.md").write_text("---\nname: local\ncloudify: false\n---\n# Local")
    sync = SkillsSync(backend=mock_backend, skills_dir=skills_dir, agent_id="test-agent")
    pushed = sync.push()
    assert len(pushed) == 1
    assert "syncable" in pushed[0]

@patch("cloudify_hermes.sync.skills.S3Backend")
def test_skills_pull_downloads_and_merges(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    mock_backend.list.return_value = ["cloudify/skills/pulled/SKILL.md"]
    mock_backend.get.return_value = b"---\nname: pulled\n---\n# Pulled skill"
    mock_backend.prefix = "cloudify/"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    sync = SkillsSync(backend=mock_backend, skills_dir=skills_dir, agent_id="test-agent")
    pulled = sync.pull()
    assert len(pulled) == 1
    assert (skills_dir / "pulled" / "SKILL.md").exists()