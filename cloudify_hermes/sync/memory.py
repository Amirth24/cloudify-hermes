"""Memory log sync — append-only JSONL to S3, mush merge on pull."""
from __future__ import annotations
import json
import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from cloudify_hermes.storage.s3 import S3Backend

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _entry_key(entry: dict) -> str:
    content = entry.get("content", "")
    return hashlib.sha256(content.encode()).hexdigest()


def mush_merge(local: List[dict], remote: List[dict]) -> List[dict]:
    """Idempotent merge of memory entries. Newer timestamp wins. Tombstones remove."""
    by_key: Dict[str, dict] = {}
    all_entries = sorted(local + remote, key=lambda e: e.get("timestamp", ""))
    for entry in all_entries:
        key = _entry_key(entry)
        if entry.get("deleted"):
            by_key.pop(key, None)
        else:
            existing = by_key.get(key)
            if existing is None or entry.get("timestamp", "") >= existing.get("timestamp", ""):
                by_key[key] = entry
    return list(by_key.values())


class MemoryLogSync:
    def __init__(self, backend: S3Backend, memories_dir: Path, agent_id: str):
        self.backend = backend
        self.memories_dir = memories_dir
        self.agent_id = agent_id

    def _read_local_memory(self) -> List[dict]:
        mem_file = self.memories_dir / "MEMORY.md"
        if not mem_file.exists():
            return []
        entries = []
        for line in mem_file.read_text().splitlines():
            line = line.strip()
            if line:
                entries.append({"content": line, "timestamp": _now_iso(), "agent_id": self.agent_id})
        return entries

    def append_log(self):
        entries = self._read_local_memory()
        if not entries:
            return
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        s3_key = f"memory-logs/{ts}.jsonl"
        payload = {
            "timestamp": _now_iso(),
            "agent_id": self.agent_id,
            "entries": entries,
        }
        data = json.dumps(payload, indent=2).encode()
        self.backend.put(s3_key, data)
        logger.info("Appended memory log: %d entries", len(entries))

    def pull(self) -> List[dict]:
        remote_keys = self.backend.list("memory-logs/")
        remote_entries = []
        for key in remote_keys:
            data = self.backend.get(key.replace(f"{self.backend.prefix}", ""))
            if data:
                payload = json.loads(data)
                remote_entries.extend(payload.get("entries", []))
        local = self._read_local_memory()
        merged = mush_merge(local, remote_entries)
        mem_file = self.memories_dir / "MEMORY.md"
        mem_file.write_text("\n".join(e["content"] for e in merged))
        logger.info("Mush-merged memory: %d local + %d remote -> %d merged", len(local), len(remote_entries), len(merged))
        return merged