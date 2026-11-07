# CČN – instalacija na VPS (Plesk)

Sve se instalira jednom komandom. Skripta radi na Ubuntu 20.04/22.04/24.04, Debian 11/12 i AlmaLinux/Rocky 8/9, sa Pleskom ili bez njega.

## Prije pokretanja
1. U DNS-u domene napravite **A zapis** `@` i `www` koji pokazuju na IP vašeg VPS-a (zbog besplatnog SSL-a).
2. Kod prebacite na server na jedan od dva načina:
   - **GitHub:** u Emergentu kliknite „Save to GitHub“, pa na serveru:
     `git clone https://github.com/KORISNIK/REPO.git /opt/ccn`
   - **ZIP:** preuzmite kod, raspakujte ga i u Plesk File Manageru ili preko SFTP-a ga stavite u `/opt/ccn`.

## Instalacija (jedna komanda)
```bash
sudo bash /opt/ccn/deploy/install.sh
```
Skripta pita samo za domenu, e-mail vlasnika i (ako želite prenos) lozinku sa starog sajta. Ostalo radi sama:
- instalira Docker, MongoDB bazu, backend i frontend,
- u Pleskom kreira domenu (ako ne postoji), sanduče `noreply@domena` za besplatno slanje e-mailova (uz DKIM potpis) i preusmjeri nginx na portal,
- izda besplatni SSL (Let's Encrypt) i uključi preusmjeravanje na https,
- preuzme **besplatni AI model** (Qwen 2.5, radi na vašem serveru, bez plaćanja) prema RAM-u: 3,5 GB+ → 3b, 12 GB+ → 7b,
- prenese sve vijesti, slike, kamere, korisnike i postavke sa starog sajta,
- podesi automatski newsletter (dnevni u 19h, sedmični nedjeljom u 19h) i dnevni backup u 03:30.

Ako nešto pukne (npr. DNS još nije propagiran), skriptu pokrenite ponovo. Nastavlja tamo gdje je stala i ništa ne briše.

## Svakodnevno
| Šta | Komanda |
|---|---|
| Ažuriranje na novu verziju | `sudo bash /opt/ccn/deploy/update.sh` |
| Ručni backup | `sudo bash /opt/ccn/deploy/backup.sh` |
| Logovi | `cd /opt/ccn/deploy && docker compose logs -f backend` |
| Restart | `cd /opt/ccn/deploy && docker compose restart` |

## Gdje su podaci
- Baza: `/opt/ccn/deploy/data/mongo`
- Slike: `/opt/ccn/deploy/data/media`
- Backupi: `/opt/ccn/deploy/data/backups` (čuva se 14 dana)
- Podešavanja i lozinke: `/opt/ccn/deploy/.env` (ne dijelite ovu datoteku)

## Napomene
- Bez Pleska skripta sama pokreće Caddy (automatski SSL). E-mailove tada treba podesiti ručno: upišite `SMTP_*` podatke u `deploy/.env` i pokrenite `docker compose up -d`.
- Ako u Pleskom e-mailovi ne stižu: Plesk → Tools & Settings → Mail Server Settings → uključite SMTP i provjerite da port 25 nije blokiran. Kod nekih hosting firmi port 25 za izlaznu poštu treba otključati kod podrške.
- Besplatni AI radi na procesoru servera, pa jedan prijedlog traje 20–90 sekundi. Kvalitet je dobar za sažetke i naslove, ali tekst uvijek provjerite.
