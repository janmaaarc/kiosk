#!/usr/bin/env bash
# Nightly SQLite backup. Uses Python's sqlite3.Connection.backup()
# (online, lock-safe) so it's safe while the kiosk is running.
#
# Usage:
#   scripts/backup_db.sh            # backup into REFERENCE/backups/
#   scripts/backup_db.sh /some/dir  # backup into /some/dir
#
# Cron example (3:00 AM daily, keep 30 days):
#   0 3 * * * /opt/kiosk/scripts/backup_db.sh >> /opt/kiosk/logs/backup.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SRC="$PROJECT_ROOT/database.db"
DEST_DIR="${1:-$PROJECT_ROOT/REFERENCE/backups}"
RETENTION_DAYS="${KIOSK_BACKUP_RETENTION_DAYS:-30}"

PYTHON="${KIOSK_PYTHON:-$PROJECT_ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

if [[ ! -f "$SRC" ]]; then
    echo "source database not found: $SRC" >&2
    exit 1
fi

mkdir -p "$DEST_DIR"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
DEST="$DEST_DIR/kiosk-$STAMP.db"

"$PYTHON" - "$SRC" "$DEST" <<'PY'
import sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
with sqlite3.connect(src) as s, sqlite3.connect(dst) as d:
    s.backup(d)
PY

gzip -9 "$DEST"

echo "backup: $DEST.gz ($(du -h "$DEST.gz" | cut -f1))"

find "$DEST_DIR" -type f -name 'kiosk-*.db.gz' -mtime +"$RETENTION_DAYS" -print -delete \
    | sed 's/^/pruned: /' || true
