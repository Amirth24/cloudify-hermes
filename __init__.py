"""Cloudify Hermes — cloud sync plugin."""
from __future__ import annotations
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)
_PLUGIN_CTX = None

def register(ctx) -> None:
    """Register hooks and CLI commands with Hermes."""
    global _PLUGIN_CTX
    _PLUGIN_CTX = ctx
    from cloudify_hermes.config import load_cloudify_config
    cfg = load_cloudify_config()
    if not cfg.get("enabled", False):
        logger.debug("cloudify-hermes: disabled, skipping hook registration")
        return
    from cloudify_hermes.sync import skills, cron, memory, config_snapshot
    if cfg.get("hooks", {}).get("post_tool_call", True):
        @ctx.hook("post_tool_call")
        def _on_post_tool_call(tool_name: str, tool_args: dict, tool_result: Any, **kwargs):
            if tool_name in ("skill_manage", "cronjob"):
                try:
                    if tool_name == "skill_manage" and cfg.get("sync", {}).get("skills", True):
                        skills.enqueue_push()
                    elif tool_name == "cronjob" and cfg.get("sync", {}).get("cron", True):
                        cron.enqueue_push()
                except Exception as e:
                    logger.warning("cloudify post_tool_call sync failed: %s", e)
    if cfg.get("hooks", {}).get("on_session_end", True):
        @ctx.hook("on_session_end")
        def _on_session_end(**kwargs):
            try:
                if cfg.get("sync", {}).get("memory", True):
                    memory.append_log()
                if cfg.get("sync", {}).get("config", True):
                    config_snapshot.snapshot()
            except Exception as e:
                logger.warning("cloudify on_session_end sync failed: %s", e)