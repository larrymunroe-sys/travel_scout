#!/usr/bin/env bash
set -e

# Travel Scout — Local Database & Itinerary Backup Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"
echo "=== Travel Scout: Saving Local Backup ==="
python3 scout/backup.py --action backup --folder backups/local || python scout/backup.py --action backup --folder backups/local
echo "[SUCCESS] Backup complete. Saved to backups/local and backups/itineraries_backup.json"
