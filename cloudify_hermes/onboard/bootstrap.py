"""Onboarding bootstrap — pull skills, cron, and config from S3."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict

from cloudify_hermes.storage.s3 import S3Backend
from cloudify_hermes.sync.skills import SkillsSync
from cloudify_hermes.sync.cron import CronSync
from cloudify_hermes.sync.config_snapshot import ConfigSnapshot

logger = logging.getLogger(__name__)


class Onboard:
    """Onboarding bootstrap orchestrator.

    Pulls skills, cron jobs, and the latest config snapshot from S3 for a
    freshly provisioned agent. Each sub-step delegates to the existing sync
    engines, so onboarding is idempotent — re-running picks up only deltas.
    """

    def __init__(
        self,
        backend: S3Backend,
        skills_dir: Path,
        cron_dir: Path,
        config_path: Path,
        agent_id: str,
    ):
        self.backend = backend
        self.skills_dir = skills_dir
        self.cron_dir = cron_dir
        self.config_path = config_path
        self.agent_id = agent_id

    def run(self) -> Dict[str, int]:
        """Pull everything from S3. Returns counts of what was pulled."""
        results: Dict[str, int] = {
            "skills_pulled": 0,
            "cron_pulled": 0,
            "config_applied": 0,
        }

        skills_sync = SkillsSync(self.backend, self.skills_dir, self.agent_id)
        pulled_skills = skills_sync.pull()
        results["skills_pulled"] = len(pulled_skills)

        cron_sync = CronSync(self.backend, self.cron_dir, self.agent_id)
        pulled_cron = cron_sync.pull()
        results["cron_pulled"] = len(pulled_cron)

        config_snap = ConfigSnapshot(self.backend, self.config_path, self.agent_id)
        remote_config = config_snap.pull_latest()
        if remote_config:
            config_snap.apply(remote_config, self.config_path)
            results["config_applied"] = 1

        logger.info(
            "Onboarding complete: %d skills, %d cron, config=%s",
            results["skills_pulled"],
            results["cron_pulled"],
            bool(results["config_applied"]),
        )
        return results