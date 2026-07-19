"""Cloudify configuration loader — reads from ~/.hermes/config.yaml cloudify section."""
from __future__ import annotations
import os
from typing import Any, Dict
from pathlib import Path
import yaml

_DEFAULTS: Dict[str, Any] = {
    "enabled": False,
    "s3": {"bucket": "", "prefix": "cloudify/", "region": "ap-south-1", "profile": "", "role_arn": "", "external_id": ""},
    "encryption": {"passphrase_env": "CLOUDIFY_PASSPHRASE"},
    "mem0": {"api_key_env": "MEM0_API_KEY", "user_id": "", "agent_id": "hermes", "knowledge_graphs": {}},
    "sync": {"skills": True, "cron": True, "memory": True, "config": True, "viking": True},
    "hooks": {"post_tool_call": True, "on_session_end": True},
}

def _get_hermes_home() -> Path:
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"

def load_cloudify_config() -> Dict[str, Any]:
    """Load cloudify config from config.yaml, merged with defaults."""
    config_path = _get_hermes_home() / "config.yaml"
    if not config_path.exists():
        return dict(_DEFAULTS)
    with open(config_path) as f:
        full = yaml.safe_load(f) or {}
    cloudify = full.get("cloudify", {})
    result = dict(_DEFAULTS)
    for k, v in _DEFAULTS.items():
        if isinstance(v, dict) and k in cloudify:
            result[k] = {**v, **cloudify[k]}
        elif k in cloudify:
            result[k] = cloudify[k]
    return result