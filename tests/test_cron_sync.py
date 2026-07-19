import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from cloudify_hermes.sync.cron import CronSync

@patch("cloudify_hermes.sync.cron.S3Backend")
def test_cron_push_uploads_jobs(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    jobs = [{"id": "abc123", "name": "test-job", "schedule": "0 9 * * *", "prompt": "test"}]
    (cron_dir / "jobs.json").write_text(json.dumps(jobs))
    sync = CronSync(backend=mock_backend, cron_dir=cron_dir, agent_id="test-agent")
    pushed = sync.push()
    assert len(pushed) == 1
    assert pushed[0]["name"] == "test-job"

@patch("cloudify_hermes.sync.cron.S3Backend")
def test_cron_pull_merges_jobs(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    mock_backend.list.return_value = ["cloudify/cron/abc123.json"]
    mock_backend.get.return_value = json.dumps({
        "id": "abc123", "name": "pulled-job", "schedule": "0 10 * * *", "prompt": "pulled"
    }).encode()
    mock_backend.prefix = "cloudify/"
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    (cron_dir / "jobs.json").write_text("[]")
    sync = CronSync(backend=mock_backend, cron_dir=cron_dir, agent_id="test-agent")
    pulled = sync.pull()
    assert len(pulled) == 1
    assert pulled[0]["name"] == "pulled-job"

@patch("cloudify_hermes.sync.cron.S3Backend")
def test_cron_push_skips_jobs_without_id(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    cron_dir = tmp_path / "cron"
    cron_dir.mkdir()
    jobs = [{"name": "no-id-job", "schedule": "0 9 * * *"}]
    (cron_dir / "jobs.json").write_text(json.dumps(jobs))
    sync = CronSync(backend=mock_backend, cron_dir=cron_dir, agent_id="test-agent")
    pushed = sync.push()
    assert len(pushed) == 0
    mock_backend.put.assert_not_called()