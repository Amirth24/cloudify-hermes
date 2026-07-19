---
name: cloudify
description: "Cloud sync for Hermes — skills, cron, memory, config to S3. Mem0 bridge. One-command onboarding."
version: 0.1.0
author: amirth
tags: [sync, backup, s3, mem0, onboarding, cloud]
---

# Cloudify Hermes

Syncs skills, cron jobs, memory, and config to AWS S3. Bridges OpenViking → Mem0.

## Commands

- `cloudify push [all|skills|cron|memory|config|viking]` — Push to S3
- `cloudify pull [all|skills|cron|memory|config]` — Pull from S3
- `cloudify onboard` — Set up a new agent from S3
- `cloudify status` — Show config
- `cloudify mem0-sync` — Push OV entries to Mem0

## Setup

1. Add `cloudify` section to `~/.hermes/config.yaml` (see README)
2. Set `CLOUDIFY_PASSPHRASE` and `MEM0_API_KEY` in `.env`
3. `hermes plugins install <git-url>`
4. `cloudify onboard` on new agents

## Sync Labels

Skills sync by default. To opt out, add `cloudify: false` to SKILL.md frontmatter:

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

## Architecture

- **Skills/Cron**: Bidirectional sync, LWW, git-versioned in S3
- **Memory**: Append-only logs, mush merge on pull
- **Config**: Secrets-stripped snapshots, diff-apply on restore
- **Mem0**: Central universal store, hourly OV → Mem0 push
- **OpenViking**: Local + primary, weekly encrypted backup