#!/usr/bin/env bash
# Ažuriranje portala na novu verziju koda: sudo bash deploy/update.sh
set -euo pipefail
D="$(cd "$(dirname "$0")" && pwd)"; cd "$D"
[ -d ../.git ] && git -C .. pull --ff-only
bash backup.sh
docker compose up -d --build
docker image prune -f >/dev/null
echo "✔ Portal ažuriran"
