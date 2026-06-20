#!/usr/bin/env sh
set -eu
: "${DATABASE_URL:?DATABASE_URL is required}"
destination="${1:-backups/ethera-$(date -u +%Y%m%dT%H%M%SZ).dump}"
mkdir -p "$(dirname "$destination")"
pg_dump --format=custom --compress=9 --no-owner --file="$destination" "$DATABASE_URL"
pg_restore --list "$destination" >/dev/null
printf 'Verified backup: %s\n' "$destination"
