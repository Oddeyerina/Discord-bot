#!/bin/sh
set -eu
umask 077

db_path="${DB_PATH:-/app/data/dcbot.db}"
backup_dir="${BACKUP_DIR:-/app/data/backups}"
mkdir -p "$backup_dir"
stamp="$(date -u +%Y%m%d-%H%M)"
destination="$backup_dir/dcbot-$stamp.db"
sqlite3 "$db_path" ".backup '$destination'"

ls -1t "$backup_dir"/dcbot-*.db | tail -n +15 | while IFS= read -r old_backup; do
    rm -- "$old_backup"
done
