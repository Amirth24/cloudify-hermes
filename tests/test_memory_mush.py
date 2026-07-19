import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from cloudify_hermes.sync.memory import MemoryLogSync, mush_merge

def test_mush_merge_no_duplicates():
    local = [{"content": "A", "timestamp": "2026-01-01T00:00:00Z"}]
    remote = [{"content": "A", "timestamp": "2026-01-01T00:00:00Z"}, {"content": "B", "timestamp": "2026-01-02T00:00:00Z"}]
    result = mush_merge(local, remote)
    assert len(result) == 2
    contents = [r["content"] for r in result]
    assert "A" in contents and "B" in contents

def test_mush_merge_tombstone_skips():
    local = [{"content": "A", "timestamp": "2026-01-01T00:00:00Z"}]
    remote = [{"content": "A", "timestamp": "2026-01-01T00:00:00Z"}, {"content": "A", "timestamp": "2026-01-02T00:00:00Z", "deleted": True}]
    result = mush_merge(local, remote)
    assert len(result) == 0

def test_mush_merge_newer_wins():
    local = [{"content": "A", "timestamp": "2026-01-01T00:00:00Z", "value": "old"}]
    remote = [{"content": "A", "timestamp": "2026-01-02T00:00:00Z", "value": "new"}]
    result = mush_merge(local, remote)
    assert len(result) == 1
    assert result[0]["value"] == "new"

@patch("cloudify_hermes.sync.memory.S3Backend")
def test_memory_append_log(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("Test entry\nAnother entry")
    sync = MemoryLogSync(backend=mock_backend, memories_dir=mem_dir, agent_id="test-agent")
    sync.append_log()
    mock_backend.put.assert_called_once()
    args = mock_backend.put.call_args
    assert "memory-logs/" in args[0][0]

@patch("cloudify_hermes.sync.memory.S3Backend")
def test_memory_pull_merges(mock_s3_cls, tmp_path):
    mock_backend = MagicMock()
    mock_s3_cls.return_value = mock_backend
    mock_backend.prefix = "cloudify/"
    mock_backend.list.return_value = ["cloudify/memory-logs/2026-01-01T00-00-00Z.jsonl"]
    mock_backend.get.return_value = json.dumps({
        "timestamp": "2026-01-01T00:00:00Z",
        "agent_id": "remote-agent",
        "entries": [{"content": "Remote fact", "timestamp": "2026-01-01T00:00:00Z"}]
    }).encode()
    mem_dir = tmp_path / "memories"
    mem_dir.mkdir()
    (mem_dir / "MEMORY.md").write_text("Local fact")
    sync = MemoryLogSync(backend=mock_backend, memories_dir=mem_dir, agent_id="test-agent")
    merged = sync.pull()
    contents = [e["content"] for e in merged]
    assert "Local fact" in contents
    assert "Remote fact" in contents