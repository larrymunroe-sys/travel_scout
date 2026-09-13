#!/usr/bin/env bash
set -e

# Travel Scout — Reimport Itineraries from Local Backup Folder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"
echo "=== Travel Scout: Reimporting from Local Backup Folder ==="
python3 scout/backup.py --action restore --folder backups/local || python scout/backup.py --action restore --folder backups/local
echo "[SUCCESS] Reimport complete."
