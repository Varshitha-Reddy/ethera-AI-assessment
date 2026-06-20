#!/usr/bin/env sh
set -eu
: "${DATABASE_URL:?DATABASE_URL must point to the restore target}"
: "${1:?Usage: restore.sh BACKUP.dump}"
pg_restore --list "$1" >/dev/null
pg_restore --clean --if-exists --no-owner --exit-on-error --dbname="$DATABASE_URL" "$1"
printf 'Restore completed; run application smoke tests before switching traffic.\n'
