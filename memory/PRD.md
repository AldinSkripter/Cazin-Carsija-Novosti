# PRD – Cazin Čaršija Novosti

## Original problem statement
Kompletna tehnička i funkcionalna specifikacija (v1.0) za informativni portal „Cazin Čaršija Novosti“: javni portal + napredni CMS (/admin), RBAC (articles.create, edit_own, edit_all, publish, delete, approve, categories.manage, users.manage, ads.manage, settings.manage…), urednički workflow (Nacrt → Na pregledu → Odobreno → Zakazano/Objavljeno → Arhivirano, Odbijeno s obrazloženjem), media library, home page builder, breaking news, oglašavanje, SEO/Google News, statistika, komentari, prijavite vijest, AI modul, newsletter, sigurnost, privatnost, backup. Boje #0B1F3B #00C2B8 #D4A52C #FFFFFF #E6E9EF #E1142B; favicon CČN. Dodatno: „DODAJ LIVE KAMERE SA GRANICA … HAK Kamere Maljevac, Izačić itd“, uređivo iz admina.

User choices: Faza 1 + Faza 2 + kamere; vlastiti logo i favicon (poslani); AI = Claude Sonnet 5.5; kamere kao slike koje se same osvježavaju; prijava e-mail + lozinka.

## Architecture
- React (CRA) + Tailwind + shadcn, tiptap editor; FastAPI + MongoDB; Emergent object storage (slike, WebP varijante, EXIF uklonjen); Emergent managed email (potvrde newslettera, reset lozinke); Claude Sonnet 5.5 via Emergent LLM key.
- Backend: core.py (db, RBAC, sanitizacija, rate limit, audit), routes_auth/public/articles/admin, seed.py, services.py.
- SEO: client meta + JSON-LD NewsArticle, /api/share/{slug} server-rendered OG stranica za društvene mreže, /api/sitemap.xml, /api/news-sitemap.xml, /api/rss.xml, /api/robots.txt, 301 redirekcije, 410 za uklonjene. OpenAPI: /api/docs.
- Lazy scheduler objavljuje zakazane članke pri javnim upitima (max svakih 15 s).

## Personas
Vlasnik/Super Admin, Glavni urednik, Urednik (dodijeljene kategorije), Novinar, Ovlašteni autor, Moderator, Marketing, čitaoci.

## Implemented (2026-11-06)
- 2026-11-07: Newsletter slanje: dugme „Pošalji“ za kampanje (pozadinsko slanje preko Emergent e-mail servisa, link za odjavu u svakom mailu, status/brojač), automatski dnevni (19h) i sedmični (nedjelja 19h, Europe/Sarajevo) pregled preko .emergent/crons.yml → POST /api/cron/newsletter/{daily|weekly} (Bearer WEBHOOK_CRON_SECRET, idempotentno po run_id). Kod: backend/newsletter.py.
- 2026-11-07: Tamni način (prekidač u gornjoj traci i mobilnom meniju, pamti izbor), svih 77 HAK kamera graničnih prijelaza (grupe po granici, pretraga i filteri na /kamere), Breaking traka premještena u sticky header i poravnata, footer potpis „Izradio JonuzovicDesign“ (https://jonuzovicdesign.de), popravljena forma pretrage. (header sa smanjivanjem pri skrolanju, bento hero, boje po kategorijama, novi naslovi sekcija, kamere/vrijeme/najčitanije widgeti, newsletter traka u footeru, nova kolačić kartica, stranica članka: traka napretka čitanja, vrijeme čitanja, inicijal, kartica autora; admin: grupisani meni, brzo dugme „Nova vijest“, nove kartice statistike, prijava).
- Javni portal: header/meni/mobilni meni, pretraga (č/ć/š/đ/ž folding), breaking traka, hero, najnovije, najčitanije, kategorijski blokovi, video, galerije, kamere uživo (HAK Maljevac ×3, Izačić – proxy + auto osvježavanje), vrijeme Cazin (Open-Meteo), popularne teme, reklame, newsletter, cookie consent, footer, statičke stranice, autori, arhiva, prijava vijesti, 404/410.
- CMS: dashboard + grafovi, članci (rich editor, galerija, video, SEO, workflow, autosave, verzije/restore, dupliranje, više autora, breaking/pin/ekskluzivno/sponzorisano, pregled, provjera duplikata), kategorije/podkategorije, oznake, mediji (drag&drop, crop, ALT, usage check), home builder (nacrt/pregled/objava), breaking, reklame (oglašivači, kampanje, prikazi/klikovi, limit, sandbox za vanjski kod samo Super Admin), komentari (moderacija, prijave, blokiranje), prijavljene vijesti → nacrt, newsletter (double opt-in, liste, dnevni/sedmični pregled pripremljen), korisnici + RBAC matrica + dodatne dozvole, 2FA (TOTP), sesije/odjava sa svih uređaja, reset lozinke, postavke (brend, meni, footer, SEO, GA4/Plausible, moduli, održavanje), audit log, statistika (prikazi/sesije/korisnici, kategorije, autori, izvori, uređaji, teme, reklame), backup/restore, zahtjevi za privatnost, AI asistent + evidencija troškova.
- Testing iteration 1: backend 23/23, frontend ~93%; fixes applied (async storage calls, login lockout reset, session pruning, ownership checks, home dedupe, editor save race).

## Backlog
- P0: Unijeti stvarne pravne tekstove i kontakt podatke ([placeholder]); obrisati primjer članke.
- P1: Masovno slanje newslettera preko namjenskog servisa (Mailchimp/Brevo); web push obavijesti; pravi SSR (Next.js) ako bude potreban za SEO; prijevod akcija u audit logu.
- P2: Flutter aplikacije (API spreman), dark mode, sačuvani članci, napredni izvještaji.
