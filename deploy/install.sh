#!/usr/bin/env bash
# CČN – automatska instalacija na VPS (Plesk ili čisti server).
# Pokretanje:  sudo bash deploy/install.sh
# ili s GitHub-a: curl -fsSL https://raw.githubusercontent.com/KORISNIK/REPO/main/deploy/install.sh | sudo REPO=https://github.com/KORISNIK/REPO.git bash
set -Eeuo pipefail

G='\033[1;32m'; Y='\033[1;33m'; R='\033[1;31m'; B='\033[1;36m'; N='\033[0m'
say()  { echo -e "${B}==>${N} $*"; }
ok()   { echo -e "${G}✔${N} $*"; }
warn() { echo -e "${Y}!${N} $*"; }
die()  { echo -e "${R}✘ $*${N}"; exit 1; }
trap 'die "Greška na liniji $LINENO. Pokrenite skriptu ponovo – nastavlja gdje je stala."' ERR

[ "$(id -u)" = 0 ] || die "Pokrenite kao root: sudo bash deploy/install.sh"
ask() { local v="$1" q="$2" d="${3:-}"; if [ -n "${!v:-}" ]; then return; fi
  if [ -t 0 ] || [ -e /dev/tty ]; then read -r -p "$q${d:+ [$d]}: " ans </dev/tty || true; else ans=""; fi
  printf -v "$v" '%s' "${ans:-$d}"; }
asks() { local v="$1" q="$2"; if [ -n "${!v:-}" ]; then return; fi; read -r -s -p "$q: " ans </dev/tty || true; echo; printf -v "$v" '%s' "$ans"; }
rnd() { openssl rand -hex "${1:-24}"; }

# ---------- 1. Paketi ----------
say "Provjeravam sistem…"
. /etc/os-release 2>/dev/null || true
if command -v apt-get >/dev/null; then PM=apt; export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq && apt-get install -y -qq curl git openssl ca-certificates >/dev/null
elif command -v dnf >/dev/null; then PM=dnf; dnf install -y -q curl git openssl ca-certificates >/dev/null
elif command -v yum >/dev/null; then PM=yum; yum install -y -q curl git openssl ca-certificates >/dev/null
else die "Nepodržan sistem (treba apt, dnf ili yum)"; fi
ok "Sistem: ${PRETTY_NAME:-Linux}"

# ---------- 2. Kod ----------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || echo /tmp)"
if [ -f "$SCRIPT_DIR/docker-compose.yml" ]; then APP_DIR="$(dirname "$SCRIPT_DIR")"
else
  APP_DIR="${APP_DIR:-/opt/ccn}"
  ask REPO "Git adresa repozitorija (npr. https://github.com/korisnik/ccn.git)"
  [ -n "$REPO" ] || die "Treba adresa repozitorija ili pokrenite skriptu iz foldera projekta."
  if [ -d "$APP_DIR/.git" ]; then git -C "$APP_DIR" pull -q; else git clone -q "$REPO" "$APP_DIR"; fi
fi
D="$APP_DIR/deploy"; cd "$D"; mkdir -p data/media data/import data/mongo data/backups
ok "Projekt: $APP_DIR"

# ---------- 3. Docker ----------
if ! command -v docker >/dev/null; then
  say "Instaliram Docker (traje 1–2 min)…"
  curl -fsSL https://get.docker.com | sh >/dev/null 2>&1 || die "Docker instalacija nije uspjela"
fi
systemctl enable --now docker >/dev/null 2>&1 || service docker start || true
docker compose version >/dev/null 2>&1 || { [ "$PM" = apt ] && apt-get install -y -qq docker-compose-plugin >/dev/null || $PM install -y -q docker-compose-plugin; }
ok "Docker $(docker --version | awk '{print $3}' | tr -d ,)"

# ---------- 4. Podešavanja ----------
PLESK=0; command -v plesk >/dev/null && PLESK=1
if [ ! -f .env ]; then
  ask DOMAIN "Domena portala (bez https://, npr. cazincarsija.ba)"
  DOMAIN="${DOMAIN#http*://}"; DOMAIN="${DOMAIN%%/*}"; DOMAIN="${DOMAIN#www.}"
  [ -n "$DOMAIN" ] || die "Domena je obavezna"
  ask ADMIN_EMAIL "E-mail vlasnika (admin)" "jonuzovicaldin7@gmail.com"
  ADMIN_PASSWORD="Ccn$(rnd 6)!9"
  MONGO_IMAGE="mongo:7"; grep -q avx /proc/cpuinfo || { MONGO_IMAGE="mongo:4.4"; warn "CPU bez AVX – koristim MongoDB 4.4"; }
  MEM=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
  if [ "$MEM" -ge 12000 ]; then OLLAMA_MODEL="qwen2.5:7b"; elif [ "$MEM" -ge 3500 ]; then OLLAMA_MODEL="qwen2.5:3b"; elif [ "$MEM" -ge 2500 ]; then OLLAMA_MODEL="qwen2.5:1.5b"; else OLLAMA_MODEL=""; fi
  PROFILES=""; AI_PROVIDER="off"
  if [ -n "$OLLAMA_MODEL" ]; then AI_PROVIDER="ollama"; PROFILES="ai"; fi
  [ "$PLESK" = 1 ] || PROFILES="${PROFILES:+$PROFILES,}caddy"
  SMTP_PASSWORD="$(rnd 12)Aa1!"
  SMTP_HOST_V=""; [ "$PLESK" = 1 ] && SMTP_HOST_V="host.docker.internal"
  cat > .env <<EOF
DOMAIN=$DOMAIN
SITE_URL=https://$DOMAIN
DB_NAME=ccn
JWT_SECRET=$(rnd 32)
WEBHOOK_CRON_SECRET=$(rnd 32)
ADMIN_EMAIL=$ADMIN_EMAIL
ADMIN_PASSWORD=$ADMIN_PASSWORD
CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
EMAIL_FROM_NAME=Cazin Čaršija Novosti
EMAIL_REPLY_TO=$ADMIN_EMAIL
SMTP_HOST=$SMTP_HOST_V
SMTP_PORT=25
SMTP_USER=noreply@$DOMAIN
SMTP_PASSWORD=$SMTP_PASSWORD
SMTP_FROM=noreply@$DOMAIN
SMTP_VERIFY_TLS=false
AI_PROVIDER=$AI_PROVIDER
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:1.5b}
MONGO_IMAGE=$MONGO_IMAGE
APP_PORT=8080
COMPOSE_PROFILES=$PROFILES
EOF
  chmod 600 .env; FRESH=1
  ok "Podešavanja sačuvana u deploy/.env"
else
  FRESH=0; ok "Postojeća podešavanja (deploy/.env) – nastavljam"
fi
set -a; . ./.env; set +a
sed "s/__SECRET__/$WEBHOOK_CRON_SECRET/g" crontab.template > crontab; chmod 600 crontab

# ---------- 5. Plesk: domena, e-mail, nginx, SSL ----------
if [ "$PLESK" = 1 ]; then
  say "Podešavam Plesk za $DOMAIN…"
  if ! plesk bin site --info "$DOMAIN" >/dev/null 2>&1; then
    IP=$(plesk bin ipmanage --ip_list 2>/dev/null | awk '/S|E/ {for(i=1;i<=NF;i++) if ($i ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/) {split($i,a,"/"); print a[1]; exit}}')
    [ -n "$IP" ] || IP=$(hostname -I | awk '{print $1}')
    plesk bin subscription --create "$DOMAIN" -owner admin -service-plan "Default Domain" -ip "$IP" -login "ccn$(rnd 3)" -passwd "$(rnd 10)Aa1!" >/dev/null \
      && ok "Domena kreirana u Plesku" || die "Ne mogu kreirati domenu. Dodajte $DOMAIN u Plesku (Websites & Domains → Add Domain) i pokrenite skriptu ponovo."
  fi
  plesk bin domain --update "$DOMAIN" -mail_service true >/dev/null 2>&1 || true
  if plesk bin mail --info "noreply@$DOMAIN" >/dev/null 2>&1; then
    plesk bin mail --update "noreply@$DOMAIN" -passwd "$SMTP_PASSWORD" >/dev/null || warn "Lozinka za noreply@$DOMAIN nije ažurirana"
  else
    plesk bin mail --create "noreply@$DOMAIN" -mailbox true -passwd "$SMTP_PASSWORD" >/dev/null || warn "Sanduče noreply@$DOMAIN nije kreirano – kreirajte ga u Plesku (Mail) s lozinkom iz deploy/.env (SMTP_PASSWORD)"
  fi
  plesk bin domain_pref --update "$DOMAIN" -sign_outgoing_mail true >/dev/null 2>&1 || true
  ok "E-mail sanduče noreply@$DOMAIN (besplatno slanje preko Pleska)"
  if command -v ufw >/dev/null && ufw status | grep -q active; then ufw allow from 172.16.0.0/12 to any port 25 proto tcp >/dev/null || true; fi

  NG=$(mktemp)
  cat > "$NG" <<EOF
location ~ ^/(?!\.well-known/) {
    proxy_pass http://127.0.0.1:$APP_PORT;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    client_max_body_size 60m;
    proxy_read_timeout 300s;
}
EOF
  if plesk bin subscription --update-web-server-settings "$DOMAIN" -nginx-serve-static false -additional-nginx-settings-file "$NG" >/dev/null 2>&1 \
    || plesk bin site --update-web-server-settings "$DOMAIN" -nginx-serve-static false -additional-nginx-settings-file "$NG" >/dev/null 2>&1 \
    || plesk bin subscription --update-web-server-settings "$DOMAIN" -additional-nginx-settings-file "$NG" >/dev/null 2>&1; then
    ok "Nginx u Plesku preusmjeren na portal"
  else
    cp "$NG" "$D/plesk-nginx.conf"
    warn "Nginx nije automatski podešen. U Plesku: $DOMAIN → Apache & nginx Settings → Additional nginx directives → zalijepite sadržaj $D/plesk-nginx.conf"
  fi
  rm -f "$NG"
fi

# ---------- 6. Pokretanje ----------
say "Gradim i pokrećem portal (prvi put 5–10 min)…"
docker compose up -d --build 2>&1 | grep -E "Built|Started|Error|error" || true
for i in $(seq 1 90); do curl -fs "http://127.0.0.1:$APP_PORT/api/health" >/dev/null 2>&1 && break; sleep 3; done
curl -fs "http://127.0.0.1:$APP_PORT/api/health" >/dev/null || { docker compose logs --tail 40 backend; die "Portal se nije pokrenuo"; }
ok "Portal radi lokalno na 127.0.0.1:$APP_PORT"

if [ "$AI_PROVIDER" = ollama ]; then
  say "Preuzimam besplatni AI model $OLLAMA_MODEL (jednom, par minuta)…"
  docker compose exec -T ollama ollama pull "$OLLAMA_MODEL" >/dev/null 2>&1 && ok "AI model spreman" || warn "AI model nije preuzet – pokrenite kasnije: cd $D && docker compose exec ollama ollama pull $OLLAMA_MODEL"
fi

# ---------- 7. Prenos podataka ----------
if [ "$FRESH" = 1 ]; then
  ask MIGRATE "Prenijeti vijesti, slike i korisnike sa starog sajta? (d/n)" "d"
  if [[ "$MIGRATE" =~ ^[dDyY] ]]; then
    ask OLD_URL "Adresa starog sajta" "https://carsija-novosti--4hvpmrhn.preview.emergentagent.com"
    ask OLD_EMAIL "Admin e-mail na starom sajtu" "$ADMIN_EMAIL"
    asks OLD_PASS "Admin lozinka na starom sajtu"
    CJ=$(mktemp); LOGIN=$(curl -s -c "$CJ" -X POST "$OLD_URL/api/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"$OLD_EMAIL\",\"password\":\"$OLD_PASS\"}")
    if echo "$LOGIN" | grep -q requires_2fa; then ask OLD_TOTP "2FA kod"
      curl -s -c "$CJ" -X POST "$OLD_URL/api/auth/login" -H "Content-Type: application/json" -d "{\"email\":\"$OLD_EMAIL\",\"password\":\"$OLD_PASS\",\"totp\":\"$OLD_TOTP\"}" >/dev/null; fi
    if curl -fs -b "$CJ" "$OLD_URL/api/admin/backup" -o data/import/backup.json && grep -q '"_meta"' data/import/backup.json; then
      say "Uvozim podatke i preuzimam slike…"
      docker compose exec -T backend python import_backup.py /data/import/backup.json "$OLD_URL"
      docker compose restart backend >/dev/null; MIGRATED=1; ok "Podaci preneseni"
    else warn "Prijava na stari sajt nije uspjela – podaci nisu preneseni. Kasnije: Admin → Postavke → Vraćanje backupa."; fi
    rm -f "$CJ"
  fi
fi

# ---------- 8. SSL ----------
if [ "$PLESK" = 1 ]; then
  say "Izdajem besplatni SSL (Let's Encrypt)…"
  if plesk bin extension --exec letsencrypt cli.php -d "$DOMAIN" -d "www.$DOMAIN" -m "$ADMIN_EMAIL" >/dev/null 2>&1 \
     || plesk bin extension --exec letsencrypt cli.php -d "$DOMAIN" -m "$ADMIN_EMAIL" >/dev/null 2>&1; then
    plesk bin site --update "$DOMAIN" -ssl-redirect true >/dev/null 2>&1 || true; ok "SSL aktivan"
  else warn "SSL nije izdat – provjerite da DNS (A zapis) za $DOMAIN pokazuje na ovaj server, pa: Plesk → SSL/TLS → Let's Encrypt"; fi
fi

# ---------- 9. Dnevni backup ----------
cat > /etc/cron.d/ccn-backup <<EOF
30 3 * * * root bash $D/backup.sh >/dev/null 2>&1
EOF
ok "Automatski backup svaki dan u 03:30 (čuva 14 dana) u $D/data/backups"

echo
echo -e "${G}══════════════════════════════════════════════${N}"
echo -e "${G} Portal je instaliran!${N}"
echo -e "  Sajt:   https://$DOMAIN"
echo -e "  Admin:  https://$DOMAIN/admin/prijava"
if [ "${MIGRATED:-0}" = 1 ]; then echo -e "  Prijava: vaš postojeći e-mail i lozinka sa starog sajta"
elif [ "$FRESH" = 1 ]; then echo -e "  Prijava: $ADMIN_EMAIL / $ADMIN_PASSWORD  ${Y}(promijenite lozinku nakon prijave)${N}"; fi
echo -e "  AI:     ${AI_PROVIDER/off/isključen (premalo RAM-a)} ${OLLAMA_MODEL:+($OLLAMA_MODEL)}"
echo -e "  Ažuriranje: sudo bash $D/update.sh"
echo -e "${G}══════════════════════════════════════════════${N}"
