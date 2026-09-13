#!/usr/bin/env bash
set -e

# Travel Scout — Local Backup and Git Upload Helper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT_DIR"
echo "=== [1/3] Saving Database to Local Backup Folder ==="
python3 scout/backup.py --action backup --folder backups/local || python scout/backup.py --action backup --folder backups/local

echo "=== [2/3] Staging Itinerary Backup into Git ==="
git add backups/itineraries_backup.json

echo "=== [3/3] Ready to Commit and Push ==="
COMMIT_MSG="${1:-Update code and sync latest itinerary backup}"
git commit -m "$COMMIT_MSG" || true
git push origin main
echo "[SUCCESS] Code and itinerary backup uploaded successfully to Git!"
