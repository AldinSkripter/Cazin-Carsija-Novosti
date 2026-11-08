#!/usr/bin/env bash
# Ponovno gradi i pokreće portal s trenutnim kodom (Plesk Git ovo poziva automatski nakon "Pull").
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; cd "$D"
LOG="$D/redeploy.log"
exec > >(tee "$LOG") 2>&1
echo "== Ažuriranje $(date '+%F %T') =="
# Git pull samo kad je kod kloniran ručno kao root (Plesk Git sam povlači kod)
if [ -d ../.git ] && [ "$(stat -c %U ../.git)" = root ]; then git -C .. pull --ff-only; fi
sed "s/__SECRET__/$(grep ^WEBHOOK_CRON_SECRET= .env | cut -d= -f2)/g" crontab.template > crontab; chmod 600 crontab
bash backup.sh
docker compose up -d --build --remove-orphans
for i in $(seq 1 60); do curl -fs "http://127.0.0.1:$(grep ^APP_PORT= .env | cut -d= -f2)/api/health" >/dev/null && break; sleep 3; done
if [ ! -f data/import/.legal_v1 ]; then docker compose exec -T backend python legal_pages.py && touch data/import/.legal_v1; fi
docker image prune -f >/dev/null
echo "✔ Portal ažuriran $(date '+%F %T')"
chmod 644 "$LOG"
