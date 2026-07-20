"""Cloudify configuration loader — reads from ~/.hermes/config.yaml cloudify section."""
from __future__ import annotations
import os
from typing import Any, Dict
from pathlib import Path
import yaml

from cloudify_hermes.env import CloudifyEnv


def _get_defaults() -> Dict[str, Any]:
    """Build default config dict from CloudifyEnv (lazy, so env vars are fresh)."""
    _env = CloudifyEnv()
    return {
        "enabled": False,
        "s3": {"bucket": "", "prefix": _env.s3_prefix, "region": _env.s3_region, "profile": "", "role_arn": "", "external_id": ""},
        "encryption": {"passphrase_env": _env.passphrase_env},
        "mem0": {"api_key_env": _env.mem0_api_key_env, "user_id": "", "agent_id": _env.agent_id, "knowledge_graphs": {}},
        "sync": {"skills": True, "cron": True, "memory": True, "config": True, "viking": True},
        "hooks": {"post_tool_call": True, "on_session_end": True},
    }


def _get_hermes_home() -> Path:
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"


def load_cloudify_config() -> Dict[str, Any]:
    """Load cloudify config from config.yaml, merged with defaults."""
    defaults = _get_defaults()
    config_path = _get_hermes_home() / "config.yaml"
    if not config_path.exists():
        return defaults
    with open(config_path) as f:
        full = yaml.safe_load(f) or {}
    cloudify = full.get("cloudify", {})
    result = defaults
    for k, v in defaults.items():
        if isinstance(v, dict) and k in cloudify:
            result[k] = {**v, **cloudify[k]}
        elif k in cloudify:
            result[k] = cloudify[k]
    return result
