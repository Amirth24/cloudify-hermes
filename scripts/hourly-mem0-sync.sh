#!/bin/bash
# scripts/hourly-mem0-sync.sh — OV → Mem0 hourly push
set -euo pipefail
source ~/.hermes/.env 2>/dev/null || true
exec python -m cloudify_hermes.cli mem0-sync