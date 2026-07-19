# Cloudify Hermes

Cloud sync for Hermes Agent. Synchronizes skills, cron jobs, memory logs, and config snapshots to AWS S3. Bridges OpenViking → Mem0 for central knowledge. One-command onboarding for new agents.

## Install

```bash
hermes plugins install https://github.com/Amirth24/cloudify-hermes
```

## Configure

Add to `~/.hermes/config.yaml`:

```yaml
cloudify:
  enabled: true
  s3:
    bucket: "your-bucket"
    prefix: "cloudify/"
    region: "ap-south-1"
    profile: ""              # Optional: AWS profile from ~/.aws/credentials
    role_arn: ""             # IAM role ARN to assume (preferred over access keys)
    external_id: ""          # Optional: external ID for cross-account role assumption
  encryption:
    passphrase_env: "CLOUDIFY_PASSPHRASE"
  mem0:
    api_key_env: "MEM0_API_KEY"
    user_id: "amirth"
    agent_id: "hermes-laptop"
  sync:
    skills: true
    cron: true
    memory: true
    config: true
    viking: true
  hooks:
    post_tool_call: true
    on_session_end: true
```

Set in `~/.hermes/.env`:
```
CLOUDIFY_PASSPHRASE=your-strong-passphrase
MEM0_API_KEY=your-mem0-api-key
```

## Usage

| Command | Description |
|---------|-------------|
| `cloudify push all` | Push everything to S3 |
| `cloudify pull all` | Pull everything from S3 |
| `cloudify onboard` | Set up a new agent from S3 |
| `cloudify status` | Show config |
| `cloudify mem0-sync` | Push OV → Mem0 |

## Sync Labels

All agent-created skills sync by default. Opt out by adding `cloudify: false` to SKILL.md frontmatter:

```yaml
---
name: local-only-skill
cloudify: false
---
```

## Scheduled Sync

Cron jobs (set up via `hermes cron create`):
- **Hourly**: `scripts/hourly-mem0-sync.sh` — OV → Mem0
- **Weekly**: `scripts/weekly-s3-backup.sh` — Full S3 backup

## S3 Layout

```
s3://<bucket>/cloudify/
├── skills/                    # Git-versioned skill files
├── cron/                      # Cron job JSON definitions
├── memory-logs/               # Append-only timestamped JSONL
├── config-snapshots/          # Secrets-stripped YAML snapshots
├── viking-backups/            # Encrypted OpenViking tarballs
└── manifest.json              # Latest state pointer
```

## Architecture

- **Skills/Cron**: Bidirectional sync, LWW, git-versioned in S3
- **Memory**: Append-only logs, mush merge on pull (idempotent, tombstones supported)
- **Config**: Secrets-stripped snapshots, diff-apply on restore (preserves local secrets)
- **Mem0**: Central universal store, hourly OV → Mem0 push with knowledge graph categories
- **OpenViking**: Local + primary, weekly encrypted tarball backup

## Plugin Hooks

| Hook | Action |
|------|--------|
| `post_tool_call` | If tool was `skill_manage` or `cronjob` → sync to S3 |
| `on_session_end` | Append memory log + snapshot config to S3 |

## Testing

```bash
cd cloudify-hermes
source .venv/bin/activate
pytest tests/ -v
```

## License

MIT