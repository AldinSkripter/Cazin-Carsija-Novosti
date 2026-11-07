#!/usr/bin/env bash
# Backup baze i slika u deploy/data/backups (čuva zadnjih 14 dana)
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; cd "$D"
. ./.env
T=$(date +%F-%H%M); mkdir -p data/backups
docker compose exec -T mongo sh -c "mongodump --quiet --archive --gzip --db $DB_NAME" > "data/backups/db-$T.gz"
tar -czf "data/backups/media-$T.tar.gz" -C data media
find data/backups -type f -mtime +14 -delete
echo "✔ Backup: data/backups/db-$T.gz, media-$T.tar.gz"
