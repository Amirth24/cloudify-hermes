#!/bin/bash
# scripts/weekly-s3-backup.sh — Full weekly backup to S3
set -euo pipefail
source ~/.hermes/.env 2>/dev/null || true
exec python -m cloudify_hermes.cli push all