"""Skills sync engine — push/pull to S3 with frontmatter opt-out and LWW."""
from __future__ import annotations
import logging
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
import yaml
from cloudify_hermes.storage.s3 import S3Backend

logger = logging.getLogger(__name__)

def parse_frontmatter(skill_path: Path) -> dict:
    text = skill_path.read_text()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}

def should_sync_skill(skill_path: Path) -> bool:
    fm = parse_frontmatter(skill_path)
    return fm.get("cloudify", True) is not False

def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class SkillsSync:
    def __init__(self, backend: S3Backend, skills_dir: Path, agent_id: str):
        self.backend = backend
        self.skills_dir = skills_dir
        self.agent_id = agent_id

    def _iter_local_skills(self):
        if not self.skills_dir.exists():
            return
        for skill_md in self.skills_dir.rglob("SKILL.md"):
            if ".archive" in skill_md.parts or ".curator_backups" in skill_md.parts:
                continue
            rel = skill_md.relative_to(self.skills_dir)
            parts = rel.parts
            if len(parts) >= 2:
                category = parts[0] if len(parts) > 2 else ""
                name = parts[-2] if len(parts) >= 2 else parts[0]
                yield (category, name, skill_md)

    def push(self) -> List[str]:
        pushed = []
        for category, name, skill_path in self._iter_local_skills():
            if not should_sync_skill(skill_path):
                logger.debug("Skipping skill (opt-out): %s", name)
                continue
            skill_dir = skill_path.parent
            rel_dir = skill_dir.relative_to(self.skills_dir)
            for file_path in skill_dir.rglob("*"):
                if file_path.is_file() and "__pycache__" not in file_path.parts:
                    rel_file = file_path.relative_to(self.skills_dir)
                    s3_key = f"skills/{rel_file}"
                    data = file_path.read_bytes()
                    meta = {"agent_id": self.agent_id, "pushed_at": _now_iso(), "checksum": _checksum(data)}
                    self.backend.put(s3_key, data, metadata=meta)
            pushed.append(name)
            logger.info("Pushed skill: %s", name)
        return pushed

    def pull(self) -> List[str]:
        pulled = []
        keys = self.backend.list("skills/")
        skill_keys = [k for k in keys if k.endswith("SKILL.md")]
        for key in skill_keys:
            rel_key = key.replace(f"{self.backend.prefix}skills/", "")
            local_path = self.skills_dir / rel_key
            if local_path.exists():
                local_data = local_path.read_bytes()
                remote_data = self.backend.get(f"skills/{rel_key}")
                if remote_data and _checksum(remote_data) == _checksum(local_data):
                    logger.debug("Skill unchanged, skipping: %s", rel_key)
                    continue
            data = self.backend.get(f"skills/{rel_key}")
            if data:
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_bytes(data)
                pulled.append(rel_key)
                logger.info("Pulled skill: %s", rel_key)
        return pulled

    def enqueue_push(self):
        try:
            self.push()
        except Exception as e:
            logger.warning("Skills push failed: %s", e)