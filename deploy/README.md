# CČN – instalacija na VPS s Pleskom i Git ekstenzijom

## Jednom, na početku (5 minuta klikanja + 1 SSH komanda)

1. **DNS:** napravite A zapise `@` i `www` koji pokazuju na IP VPS-a.
2. **Plesk → Websites & Domains → Add Domain:** dodajte domenu, npr. `cazincarsija.ba`.
3. **Kod na GitHub:** u Emergentu kliknite **Save to GitHub**.
4. **Plesk → domena → Git:**
   - Repository URL: adresa vašeg GitHub repozitorija. Ako je repozitorij privatan, Plesk pokaže SSH ključ; dodajte ga na GitHubu: Repo → Settings → Deploy keys → Add.
   - Deployment mode: **Manual** (ili Automatic, ako ćete koristiti webhook).
   - Deployment path: **`/ccn`**. Ne stavljajte ga u `httpdocs`.
   - Kliknite **OK**. Plesk povuče kod u `/var/www/vhosts/DOMENA/ccn`.
5. **SSH (samo ovaj jedan put):**
   ```bash
   sudo bash /var/www/vhosts/DOMENA/ccn/deploy/install.sh
   ```
   Skripta sama prepozna domenu, a vi potvrdite Enter. Pita još e-mail i lozinku starog sajta (za prenos podataka). Sve ostalo radi sama:
   - instalira Docker i bazu,
   - pokrene portal,
   - preusmjeri nginx,
   - izda SSL,
   - napravi besplatni e-mail `noreply@domena`,
   - preuzme besplatni AI,
   - prenese vijesti, slike i korisnike,
   - podesi dnevni backup,
   - uključi **automatsko ažuriranje nakon Git Pull-a**.
6. Ako je skripta na kraju napisala žutu poruku za Git, u Pleskom otvorite **Git → Repository Settings → Enable additional deployment actions** i upišite:
   ```
   date > deploy/.redeploy
   ```
   Za ovo pretplata treba imati uključen SSH pristup: Hosting & DNS → Hosting → SSH access → `/bin/bash (chrooted)`.

## Svaki sljedeći put (bez SSH-a)
1. Ovdje u Emergentu: **Save to GitHub**.
2. Plesk → domena → Git → **Pull Updates** (ili se povuče samo ako je mode Automatic).
3. Portal se sam napravi i restartuje za 1–5 minuta. Prije toga uvijek napravi backup.

Rezultat zadnjeg ažuriranja vidite u Plesk File Manageru: `ccn/deploy/redeploy.log`.

## Korisne SSH komande (samo ako zatreba)
| Šta | Komanda |
|---|---|
| Ručno ažuriranje | `sudo bash /var/www/vhosts/DOMENA/ccn/deploy/update.sh` |
| Ručni backup | `sudo bash /var/www/vhosts/DOMENA/ccn/deploy/backup.sh` |
| Logovi | `cd /var/www/vhosts/DOMENA/ccn/deploy && sudo docker compose logs -f backend` |
| Restart | `cd /var/www/vhosts/DOMENA/ccn/deploy && sudo docker compose restart` |

## Gdje su podaci (Git ih nikad ne dira)
- Baza: `ccn/deploy/data/mongo`
- Slike: `ccn/deploy/data/media`
- Backupi: `ccn/deploy/data/backups` (14 dana)
- Lozinke i podešavanja: `ccn/deploy/.env` (ne dijelite ovu datoteku)

## Napomene
- Skripta radi na Ubuntu 20.04/22.04/24.04, Debianu 11/12 i AlmaLinux/Rocky 8/9.
- Ako e-mailovi ne stižu: neki hosteri blokiraju izlazni port 25, pa to tražite od podrške. U Pleskom provjerite i Mail Server Settings.
- Besplatni AI radi na procesoru servera: jedan prijedlog traje 20–90 sekundi. Tekst uvijek provjerite.
- Bez Pleska skripta sama pokreće Caddy s automatskim SSL-om.
