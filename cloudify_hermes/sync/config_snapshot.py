"""Config snapshot sync — secrets stripped, versioned snapshots to S3."""
from __future__ import annotations
import logging
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cloudify_hermes.storage.s3 import S3Backend
from cloudify_hermes.utils.secrets import is_secret_key, strip_secrets

__all__ = ["ConfigSnapshot", "strip_secrets"]

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


class ConfigSnapshot:
    """Versioned config snapshot sync with secret stripping on push,
    and secret-preserving diff-apply on restore."""

    def __init__(self, backend: S3Backend, config_path: Path, agent_id: str):
        self.backend = backend
        self.config_path = config_path
        self.agent_id = agent_id

    def snapshot(self):
        """Upload a secrets-stripped config snapshot to S3."""
        if not self.config_path.exists():
            return
        config = yaml.safe_load(self.config_path.read_text()) or {}
        stripped = strip_secrets(config)
        data = yaml.safe_dump(stripped, default_flow_style=False).encode()
        s3_key = f"config-snapshots/{_now_iso()}.yaml"
        meta = {"agent_id": self.agent_id, "snapshot_at": _now_iso()}
        self.backend.put(s3_key, data=data, metadata=meta)
        logger.info("Config snapshot uploaded: %s", s3_key)

    def pull_latest(self) -> Optional[dict]:
        """Pull the latest config snapshot from S3."""
        keys = self.backend.list("config-snapshots/")
        if not keys:
            return None
        latest_key = sorted(keys)[-1].replace(f"{self.backend.prefix}", "")
        data = self.backend.get(latest_key)
        if data:
            return yaml.safe_load(data.decode())
        return None

    def apply(self, remote_config: dict, local_config_path: Path):
        """Apply remote config to local, preserving local secrets."""
        if not local_config_path.exists():
            local_config = {}
        else:
            local_config = yaml.safe_load(local_config_path.read_text()) or {}
        merged = {**local_config, **remote_config}
        self._restore_secrets(local_config, remote_config, merged)
        local_config_path.write_text(yaml.safe_dump(merged, default_flow_style=False))
        logger.info("Config applied from remote snapshot")

    def _restore_secrets(self, local: dict, remote: dict, merged: dict):
        """Walk local config and re-inject any secret keys the snapshot stripped."""
        for k, v in local.items():
            if is_secret_key(k):
                merged[k] = v
            elif isinstance(v, dict) and k in merged and isinstance(merged[k], dict):
                self._restore_secrets(v, remote.get(k, {}), merged[k])