#!/bin/bash
# scripts/weekly-s3-backup.sh — Full weekly backup to S3
set -euo pipefail

# Source env vars (handles KEY=VALUE lines, skips comments)
while IFS='=' read -r key value; do
  [[ "$key" =~ ^[A-Z] ]] && export "$key=$value" 2>/dev/null || true
done < ~/.hermes/.env 2>/dev/null || true

# Use the plugin's Python environment
PLUGIN_DIR="$HOME/.hermes/plugins/cloudify-hermes"
VENV_DIR="$HOME/Documents/Work/personal/cloudify-hermes/.venv"

if [ -d "$VENV_DIR" ]; then
  source "$VENV_DIR/bin/activate"
elif [ -d "$PLUGIN_DIR" ]; then
  cd "$PLUGIN_DIR"
fi

exec python -m cloudify_hermes.cli push all