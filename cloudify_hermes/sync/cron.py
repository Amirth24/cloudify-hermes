"""Cron jobs sync engine — push/pull to S3 with LWW."""
from __future__ import annotations
import json
import logging
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from cloudify_hermes.storage.s3 import S3Backend

logger = logging.getLogger(__name__)


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CronSync:
    def __init__(self, backend: S3Backend, cron_dir: Path, agent_id: str):
        self.backend = backend
        self.cron_dir = cron_dir
        self.agent_id = agent_id

    def _load_local_jobs(self) -> List[dict]:
        jobs_file = self.cron_dir / "jobs.json"
        if not jobs_file.exists():
            return []
        data = json.loads(jobs_file.read_text() or "[]")
        # Hermes stores jobs as {"jobs": [...], "updated_at": "..."}
        if isinstance(data, dict) and "jobs" in data:
            return data["jobs"]
        if isinstance(data, list):
            return data
        return []

    def _save_local_jobs(self, jobs: List[dict]):
        jobs_file = self.cron_dir / "jobs.json"
        # Preserve Hermes format
        from datetime import datetime, timezone
        payload = {
            "jobs": jobs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        jobs_file.write_text(json.dumps(payload, indent=2))

    def push(self) -> List[dict]:
        jobs = self._load_local_jobs()
        pushed = []
        for job in jobs:
            job_id = job.get("id", "")
            if not job_id:
                continue
            s3_key = f"cron/{job_id}.json"
            data = json.dumps(job, indent=2).encode()
            meta = {"agent_id": self.agent_id, "pushed_at": _now_iso(), "checksum": _checksum(data)}
            self.backend.put(s3_key, data, metadata=meta)
            pushed.append(job)
            logger.info("Pushed cron job: %s (%s)", job.get("name"), job_id)
        return pushed

    def pull(self) -> List[dict]:
        remote_keys = self.backend.list("cron/")
        remote_keys = [k for k in remote_keys if k.endswith(".json") and "/jobs.json" not in k]
        local_jobs = self._load_local_jobs()
        local_by_id = {j["id"]: j for j in local_jobs if "id" in j}
        pulled = []
        for key in remote_keys:
            data = self.backend.get(key.replace(f"{self.backend.prefix}", ""))
            if not data:
                continue
            job = json.loads(data)
            job_id = job.get("id", "")
            if not job_id:
                continue
            if job_id in local_by_id:
                local_jobs = [j for j in local_jobs if j.get("id") != job_id]
            local_jobs.append(job)
            pulled.append(job)
            logger.info("Pulled cron job: %s (%s)", job.get("name"), job_id)
        self._save_local_jobs(local_jobs)
        return pulled

    def enqueue_push(self):
        try:
            self.push()
        except Exception as e:
            logger.warning("Cron push failed: %s", e)