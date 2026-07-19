"""Cloudify CLI — push, pull, onboard, status, mem0-sync."""
from __future__ import annotations
import argparse
import json
import sys
import os
from pathlib import Path
from cloudify_hermes.config import load_cloudify_config
from cloudify_hermes.storage.s3 import S3Backend
from cloudify_hermes.sync.skills import SkillsSync
from cloudify_hermes.sync.cron import CronSync
from cloudify_hermes.sync.memory import MemoryLogSync
from cloudify_hermes.sync.config_snapshot import ConfigSnapshot
from cloudify_hermes.sync.mem0_bridge import Mem0Bridge


def _get_hermes_home() -> Path:
    val = os.environ.get("HERMES_HOME", "").strip()
    return Path(val) if val else Path.home() / ".hermes"


def _make_backend(cfg: dict) -> S3Backend:
    s3 = cfg["s3"]
    return S3Backend(
        bucket=s3["bucket"],
        prefix=s3["prefix"],
        region=s3["region"],
        profile=s3.get("profile", ""),
        role_arn=s3.get("role_arn", ""),
        external_id=s3.get("external_id", ""),
    )


def cmd_push(args):
    cfg = load_cloudify_config()
    if not cfg.get("enabled"):
        print("Cloudify is disabled. Set cloudify.enabled: true in config.yaml")
        sys.exit(1)
    backend = _make_backend(cfg)
    home = _get_hermes_home()
    agent_id = cfg.get("mem0", {}).get("agent_id", "hermes")
    if args.what == "skills" or args.what == "all":
        sync = SkillsSync(backend, home / "skills", agent_id)
        pushed = sync.push()
        print(f"Pushed {len(pushed)} skills: {pushed}")
    if args.what == "cron" or args.what == "all":
        sync = CronSync(backend, home / "cron", agent_id)
        pushed = sync.push()
        print(f"Pushed {len(pushed)} cron jobs")
    if args.what == "memory" or args.what == "all":
        sync = MemoryLogSync(backend, home / "memories", agent_id)
        sync.append_log()
        print("Appended memory log")
    if args.what == "config" or args.what == "all":
        sync = ConfigSnapshot(backend, home / "config.yaml", agent_id)
        sync.snapshot()
        print("Uploaded config snapshot")
    if args.what == "viking" or args.what == "all":
        _backup_viking(backend, cfg)
        print("Backed up OpenViking data")


def cmd_pull(args):
    cfg = load_cloudify_config()
    if not cfg.get("enabled"):
        print("Cloudify is disabled.")
        sys.exit(1)
    backend = _make_backend(cfg)
    home = _get_hermes_home()
    agent_id = cfg.get("mem0", {}).get("agent_id", "hermes")
    if args.what == "skills" or args.what == "all":
        sync = SkillsSync(backend, home / "skills", agent_id)
        pulled = sync.pull()
        print(f"Pulled {len(pulled)} skills")
    if args.what == "cron" or args.what == "all":
        sync = CronSync(backend, home / "cron", agent_id)
        pulled = sync.pull()
        print(f"Pulled {len(pulled)} cron jobs")
    if args.what == "memory" or args.what == "all":
        sync = MemoryLogSync(backend, home / "memories", agent_id)
        merged = sync.pull()
        print(f"Mush-merged {len(merged)} memory entries")
    if args.what == "config" or args.what == "all":
        sync = ConfigSnapshot(backend, home / "config.yaml", agent_id)
        remote = sync.pull_latest()
        if remote:
            sync.apply(remote, home / "config.yaml")
            print("Applied config from remote (secrets preserved)")
        else:
            print("No config snapshots found")


def cmd_onboard(args):
    cfg = load_cloudify_config()
    if not cfg.get("enabled"):
        print("Cloudify is disabled. Configure cloudify section in config.yaml first.")
        sys.exit(1)
    backend = _make_backend(cfg)
    home = _get_hermes_home()
    agent_id = cfg.get("mem0", {}).get("agent_id", "hermes")
    # Lazy import: onboard module may not exist yet during parallel task 9.
    from cloudify_hermes.onboard.bootstrap import Onboard
    onboard = Onboard(
        backend,
        home / "skills",
        home / "cron",
        home / "config.yaml",
        agent_id,
    )
    result = onboard.run()
    print(f"Onboarding complete: {json.dumps(result, indent=2)}")


def cmd_status(args):
    cfg = load_cloudify_config()
    print(f"Enabled: {cfg.get('enabled', False)}")
    print(f"S3: {cfg['s3']['bucket']}/{cfg['s3']['prefix']} (region: {cfg['s3']['region']})")
    print(f"Agent ID: {cfg.get('mem0', {}).get('agent_id', 'hermes')}")
    print(f"Mem0 user: {cfg.get('mem0', {}).get('user_id', '')}")
    print(f"Sync: {cfg.get('sync', {})}")
    print(f"Hooks: {cfg.get('hooks', {})}")


def cmd_mem0_sync(args):
    cfg = load_cloudify_config()
    mem0_cfg = cfg.get("mem0", {})
    api_key = os.environ.get(mem0_cfg.get("api_key_env", "MEM0_API_KEY"), "")
    if not api_key:
        print("MEM0_API_KEY not set")
        sys.exit(1)
    bridge = Mem0Bridge(
        ov_endpoint="http://localhost:8765",
        mem0_api_key=api_key,
        user_id=mem0_cfg.get("user_id", ""),
        agent_id=mem0_cfg.get("agent_id", "hermes"),
    )
    bridge.sync()
    print("Mem0 sync complete")


def _backup_viking(backend, cfg):
    import tarfile
    import tempfile
    from cloudify_hermes.storage.crypto import encrypt
    ov_home = Path.home() / ".openviking"
    if not ov_home.exists():
        print("OpenViking not found at ~/.openviking")
        return
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        tmp_path = tmp.name
    with tarfile.open(tmp_path, "w:gz") as tar:
        tar.add(ov_home / "data", arcname="data")
        if (ov_home / "ov.conf").exists():
            tar.add(ov_home / "ov.conf", arcname="ov.conf")
    with open(tmp_path, "rb") as f:
        data = f.read()
    encrypted = encrypt(data, passphrase_env=cfg["encryption"]["passphrase_env"])
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    backend.put(f"viking-backups/{ts}.tar.gz.enc", encrypted)
    os.unlink(tmp_path)


def main():
    parser = argparse.ArgumentParser(
        prog="cloudify",
        description="Cloud sync for Hermes Agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    push = sub.add_parser("push", help="Push local state to S3")
    push.add_argument(
        "what",
        choices=["skills", "cron", "memory", "config", "viking", "all"],
        default="all",
        nargs="?",
    )
    push.set_defaults(func=cmd_push)

    pull = sub.add_parser("pull", help="Pull from S3 to local")
    pull.add_argument(
        "what",
        choices=["skills", "cron", "memory", "config", "all"],
        default="all",
        nargs="?",
    )
    pull.set_defaults(func=cmd_pull)

    onboard = sub.add_parser("onboard", help="Onboard a new agent from S3")
    onboard.set_defaults(func=cmd_onboard)

    status = sub.add_parser("status", help="Show cloudify config")
    status.set_defaults(func=cmd_status)

    mem0 = sub.add_parser("mem0-sync", help="Push OpenViking entries to Mem0")
    mem0.set_defaults(func=cmd_mem0_sync)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()