import os
import asyncio
import logging
from datetime import timedelta

import requests

from core import db, new_id, iso, now, hash_pw, slugify, fold, ROLE_DEFAULTS
from services import process_image

log = logging.getLogger("seed")

CATEGORIES = [
    ("Najnovije vijesti", None), ("Cazin", None), ("Unsko-sanski kanton", None), ("Bihać", "Unsko-sanski kanton"),
    ("Velika Kladuša", "Unsko-sanski kanton"), ("Bosanska Krupa", "Unsko-sanski kanton"), ("Bužim", "Unsko-sanski kanton"),
    ("Bosanski Petrovac", "Unsko-sanski kanton"), ("Sanski Most", "Unsko-sanski kanton"), ("Ključ", "Unsko-sanski kanton"),
    ("Bosna i Hercegovina", None), ("Region", None), ("Svijet", None), ("Politika", None), ("Hronika", None), ("Društvo", None),
    ("Ekonomija", None), ("Sport", None), ("Kultura", None), ("Zdravlje", None), ("Obrazovanje", None), ("Zanimljivosti", None),
    ("Tehnologija", None), ("Vremenska prognoza", None), ("Video", None), ("Foto vijesti", None),
]
MENU_CATS = ["Cazin", "Unsko-sanski kanton", "Bosna i Hercegovina", "Region", "Svijet", "Hronika", "Sport", "Kultura", "Video"]

PAGES = [("O nama", "o-nama"), ("Redakcija", "redakcija"), ("Kontakt", "kontakt"), ("Impresum", "impresum"),
         ("Politika privatnosti", "politika-privatnosti"), ("Politika kolačića", "politika-kolacica"), ("Uslovi korištenja", "uslovi-koristenja"),
         ("Oglašavanje", "oglasavanje"), ("Ispravke i demantiji", "ispravke-i-demantiji")]

CAMERAS = [
    ("GP Maljevac – kamera 1", "Maljevac (HR) / Velika Kladuša (BiH)", "https://m.hak.hr/cam.asp?id=429", "https://m.hak.hr/kamera.asp?g=2&k=177"),
    ("GP Maljevac – kamera 2", "Maljevac (HR) / Velika Kladuša (BiH)", "https://m.hak.hr/cam.asp?id=430", "https://m.hak.hr/kamera.asp?g=2&k=177"),
    ("GP Maljevac – kamera 3", "Maljevac (HR) / Velika Kladuša (BiH)", "https://m.hak.hr/cam.asp?id=406", "https://m.hak.hr/kamera.asp?g=2&k=177"),
    ("GP Izačić", "Izačić (BiH) / Ličko Petrovo Selo (HR)", "https://m.hak.hr/cam.asp?id=407", "https://m.hak.hr/kamera.asp?g=2&k=179"),
]

DEMO_IMAGES = [
    "https://images.unsplash.com/photo-1777918210754-8d8fc75ed4c5?w=1600&q=80",
    "https://images.unsplash.com/photo-1755162642541-20b93d5ca43f?w=1600&q=80",
    "https://images.unsplash.com/photo-1742741301456-a1b361b42128?w=1600&q=80",
    "https://images.unsplash.com/photo-1780396269429-e20eaa1a1cd2?w=1600&q=80",
    "https://images.unsplash.com/photo-1522778119026-d647f0596c20?w=1600&q=80",
    "https://images.unsplash.com/photo-1786194705972-f81211b72ed5?w=1600&q=80",
    "https://images.unsplash.com/photo-1549615567-101937a79124?w=1600&q=80",
    "https://images.unsplash.com/photo-1489944440615-453fc2b6a9a9?w=1600&q=80",
]
DEMO_ARTICLES = [
    ("cazin", "Primjer glavne vijesti iz Cazina: ovdje ide naslov vaše prve objave", ["Cazin", "lokalno"], True),
    ("unsko-sanski-kanton", "Primjer vijesti iz Unsko-sanskog kantona za rubriku USK", ["USK", "kanton"], False),
    ("kultura", "Primjer kulturne vijesti s foto galerijom iz Krajine", ["kultura", "Krajina"], False),
    ("politika", "Primjer političke vijesti: naslov sjednice ili odluke", ["politika", "vijeće"], False),
    ("sport", "Primjer sportske vijesti: rezultat utakmice lokalnog kluba", ["sport", "nogomet"], False),
    ("region", "Primjer regionalne vijesti: stanje na graničnim prijelazima", ["granica", "promet"], False),
    ("bosna-i-hercegovina", "Primjer vijesti iz Bosne i Hercegovine", ["BiH"], False),
    ("svijet", "Primjer vijesti iz svijeta za rubriku Svijet", ["svijet"], False),
]

DEFAULT_SETTINGS = {
    "site_name": "Cazin Čaršija Novosti", "publisher_name": "Cazin Čaršija Novosti", "tagline": "Prve i najbrže vijesti iz Cazina i Krajine",
    "logo_url": "/logo-web.webp", "logo_mobile_url": "/icon-192.png", "favicon_url": "/favicon.ico", "social_image": "/icon-512.png",
    "contact_email": "[unesite kontakt e-mail]", "phone": "[unesite telefon]", "address": "[unesite adresu redakcije], Cazin, BiH",
    "social": {"facebook": "", "instagram": "", "youtube": "", "tiktok": "", "x": ""},
    "footer_text": "Sva prava zadržana. Prenošenje sadržaja dozvoljeno uz navođenje izvora i link.",
    "ga4_id": "", "plausible_domain": "", "google_site_verification": "", "adsense_client": "", "site_url": "",
    "comments_enabled": True, "comments_require_approval": True, "show_views": True, "ai_enabled": True, "newsletter_enabled": True,
    "maintenance_mode": False, "maintenance_message": "Portal je trenutno u održavanju.", "cache_seconds": 30,
}

HOME_BLOCKS = [
    {"type": "hero", "title": "Izdvojeno"}, {"type": "ad", "ad_position": "home_top", "title": "Reklama"},
    {"type": "latest", "title": "Najnovije vijesti", "limit": 8}, {"type": "cameras", "title": "Kamere uživo sa granica"},
    {"type": "category", "title": "Cazin i Krajina", "category_slug": "cazin", "limit": 4},
    {"type": "category", "title": "Unsko-sanski kanton", "category_slug": "unsko-sanski-kanton", "limit": 4},
    {"type": "video", "title": "Video vijesti", "limit": 4}, {"type": "gallery", "title": "Foto galerije", "limit": 4},
    {"type": "category", "title": "Bosna i Hercegovina", "category_slug": "bosna-i-hercegovina", "limit": 4},
    {"type": "category", "title": "Region", "category_slug": "region", "limit": 4},
    {"type": "category", "title": "Svijet", "category_slug": "svijet", "limit": 4},
    {"type": "category", "title": "Sport", "category_slug": "sport", "limit": 4}, {"type": "popular_tags", "title": "Popularne teme"},
]


async def heal_category_links():
    from routes_admin import rename_category_links, remove_category_links
    cats = await db.categories.find({}, {"_id": 0, "slug": 1, "name": 1, "description": 1, "seo_title": 1}).to_list(500)
    slugs = {c["slug"] for c in cats}
    hp = (await db.settings.find_one({"key": "homepage"}) or {}).get("value") or {}
    site = (await db.settings.find_one({"key": "site"}) or {}).get("value") or {}
    used = {b.get("category_slug") for k in ("draft", "published") for b in hp.get(k) or [] if b.get("category_slug")}
    used |= {m["url"][len("/kategorija/"):] for k in ("main_menu", "footer_menu") for m in site.get(k) or [] if str(m.get("url", "")).startswith("/kategorija/")}
    for old in used - slugs:
        match = [c for c in cats if old in (slugify((c.get("description") or "").replace("Vijesti –", "")), slugify((c.get("seo_title") or "").split(" – ")[0]))]
        if len(match) == 1:
            await rename_category_links(old, match[0]["slug"], match[0]["name"], None)
            await db.categories.update_one({"slug": match[0]["slug"]}, {"$addToSet": {"old_slugs": old}})
            log.info("Popravljen link rubrike %s -> %s", old, match[0]["slug"])
        elif not match and not await db.categories.find_one({"old_slugs": old}):
            await remove_category_links({"slug": old})
            log.info("Uklonjen link obrisane rubrike %s", old)
    for c in cats:
        guess = slugify((c.get("seo_title") or "").split(" – ")[0])
        if guess and guess != c["slug"] and guess not in slugs:
            await db.categories.update_one({"slug": c["slug"]}, {"$addToSet": {"old_slugs": guess}})


async def ensure_notices_category():
    if await db.categories.find_one({"slug": "obavjestenja"}):
        return
    await db.categories.insert_one({"id": new_id(), "name": "Obavještenja", "slug": "obavjestenja", "description": "Obavještenja o smrti, dženaze i komemoracije",
                                    "parent_id": None, "seo_title": "Obavještenja – Cazin Čaršija Novosti", "seo_description": "Obavještenja o smrti i dženazama iz Cazina i Krajine.",
                                    "image": "", "color": "#475569", "visible": True, "show_in_menu": True, "hide_from_home": True, "order": 90, "created_at": iso()})
    s = (await db.settings.find_one({"key": "site"}) or {}).get("value")
    if s and not any(m.get("url") == "/kategorija/obavjestenja" for m in s.get("main_menu", [])):
        menu = s.get("main_menu", [])
        at = next((i for i, m in enumerate(menu) if m.get("url") == "/kamere"), len(menu))
        menu.insert(at, {"label": "Obavještenja", "url": "/kategorija/obavjestenja"})
        await db.settings.update_one({"key": "site"}, {"$set": {"value.main_menu": menu}})


async def seed_all():
    for key, (name, perms) in ROLE_DEFAULTS.items():
        await db.roles.update_one({"key": key}, {"$setOnInsert": {"key": key, "name": name, "permissions": perms}}, upsert=True)
    await db.roles.update_one({"key": "super_admin"}, {"$set": {"permissions": ROLE_DEFAULTS["super_admin"][1]}})

    email = os.environ["ADMIN_EMAIL"].lower()
    admin = await db.users.find_one({"email": email})
    if not admin:
        admin = {"id": new_id(), "email": email, "name": "Vlasnik portala", "slug": "redakcija", "role": "super_admin",
                 "password_hash": hash_pw(os.environ["ADMIN_PASSWORD"]), "active": True, "show_public": True, "totp_enabled": False,
                 "bio": "Redakcija portala Cazin Čaršija Novosti.", "created_at": iso(), "deleted": False}
        await db.users.insert_one(admin)

    if not await db.settings.find_one({"key": "site"}):
        await db.settings.insert_one({"key": "site", "value": DEFAULT_SETTINGS})

    if not await db.categories.count_documents({}):
        ids = {}
        for i, (name, parent) in enumerate(CATEGORIES):
            cid = new_id()
            ids[name] = cid
            await db.categories.insert_one({"id": cid, "name": name, "slug": slugify(name), "description": f"Vijesti – {name}", "parent_id": ids.get(parent),
                                            "seo_title": f"{name} – Cazin Čaršija Novosti", "seo_description": f"Najnovije vijesti iz rubrike {name}.",
                                            "image": "", "color": "", "visible": True, "show_in_menu": name in MENU_CATS, "order": i, "created_at": iso()})
        s = (await db.settings.find_one({"key": "site"}))["value"]
        s["main_menu"] = [{"label": "Naslovna", "url": "/"}] + [{"label": n, "url": f"/kategorija/{slugify(n)}"} for n in MENU_CATS] + [{"label": "Kamere", "url": "/kamere"}]
        s["footer_menu"] = [{"label": t, "url": f"/stranica/{sl}"} for t, sl in PAGES] + [{"label": "Autori", "url": "/autori"}, {"label": "Arhiva", "url": "/arhiva"},
                                                                                       {"label": "Prijavite vijest", "url": "/prijavite-vijest"}, {"label": "RSS", "url": "/api/rss.xml"}]
        await db.settings.update_one({"key": "site"}, {"$set": {"value": s}})

    await ensure_notices_category()
    await heal_category_links()

    if not await db.pages.count_documents({}):
        for t, sl in PAGES:
            await db.pages.insert_one({"id": new_id(), "title": t, "slug": sl, "published": True, "created_at": iso(), "seo_title": t, "seo_description": "",
                                       "content": f"<p>[Ovdje unesite tekst stranice „{t}“ iz admin panela → Stranice. Pravne tekstove prilagodite propisima države sjedišta izdavača.]</p>"})

    if not await db.cameras.count_documents({}):
        for i, (n, loc, img, page) in enumerate(CAMERAS):
            await db.cameras.insert_one({"id": new_id(), "name": n, "location": loc, "image_url": img, "page_url": page, "refresh_seconds": 60,
                                         "order": i, "active": True, "description": "Izvor: HAK (Hrvatski autoklub)", "created_at": iso()})

    if not await db.settings.find_one({"key": "homepage"}):
        blocks = [{**b, "id": new_id(), "order": i, "visible": True, "limit": b.get("limit", 6), "dedupe": True} for i, b in enumerate(HOME_BLOCKS)]
        await db.settings.insert_one({"key": "homepage", "value": {"draft": blocks, "published": blocks}})

    if not await db.settings.find_one({"key": "hak_synced_v1"}):
        await sync_hak_cameras()
        await db.settings.insert_one({"key": "hak_synced_v1", "value": True})

    if not await db.articles.count_documents({}) and not await db.settings.find_one({"key": "demo_seeded"}):
        await db.settings.insert_one({"key": "demo_seeded", "value": True})
        asyncio.create_task(seed_demo_articles(admin["id"]))


PRIORITY = ["Maljevac", "Izačić", "Hrvatska Kostajnica", "Gornji Varoš", "Stara Gradiška", "Bosanska Gradiška", "Kamensko", "Prisika"]


async def sync_hak_cameras():
    """Adds every HAK border-crossing camera (scraped list in hak_cameras.json) that is not in the DB yet."""
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).parent / "hak_cameras.json").read_text(encoding="utf-8"))
    data.sort(key=lambda c: (PRIORITY.index(c["crossing"]) if c["crossing"] in PRIORITY else 99))
    seen = {}
    for i, c in enumerate(data):
        crossing = c["crossing"].rstrip(".")
        label = c["label"] or ("Pogled na prijelaz (BiH strana)" if c["side"] == "BiH strana" else "Pogled na prijelaz")
        key = f"{crossing}|{label}"
        seen[key] = seen.get(key, 0) + 1
        name = f"GP {crossing} – {label}" + (f" ({seen[key]})" if seen[key] > 1 else "")
        url = f"https://m.hak.hr/cam.asp?id={c['id']}"
        fields = {"name": name, "location": f"{crossing} · {c['side']}", "group": c["group"], "order": i,
                  "page_url": f"https://m.hak.hr/kamera.asp?g=2&k={c['k']}", "description": "Izvor: HAK (Hrvatski autoklub)"}
        await db.cameras.update_one({"image_url": url}, {"$set": fields, "$setOnInsert": {
            "id": new_id(), "image_url": url, "refresh_seconds": max(int(c.get("refresh") or 60), 30), "active": True, "created_at": iso()}}, upsert=True)


def _fetch(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


async def seed_demo_articles(admin_id):
    cats = {c["slug"]: c["id"] for c in await db.categories.find({}, {"slug": 1, "id": 1}).to_list(100)}
    media = []
    for url in DEMO_IMAGES:
        try:
            raw = await asyncio.to_thread(_fetch, url)
            mid, variants, w, h = await asyncio.to_thread(process_image, raw)
            doc = {"id": mid, "filename": "primjer.jpg", **variants, "width": w, "height": h, "alt": "Ilustracija", "caption": "",
                   "credit": "Unsplash (ilustracija)", "source": "Unsplash", "category": "primjer", "search": "primjer unsplash ilustracija",
                   "uploaded_by": "Sistem", "created_at": iso(), "deleted": False}
            await db.media.insert_one(doc)
            media.append({k: doc[k] for k in ("id", "large", "medium", "thumb", "alt", "credit")})
        except Exception as e:
            log.error("demo image failed: %s", e)
    body = ("<p>Ovo je <strong>primjer članka</strong> koji pokazuje kako izgleda objava na portalu. Zamijenite ga stvarnom vijesti ili ga obrišite "
            "u admin panelu (Članci → filtriraj „primjer“).</p><h2>Podnaslov unutar teksta</h2><p>Tekst je prilagođen čitanju na mobitelu: veća slova, "
            "ugodan prored i jasni naslovi.</p><blockquote>Ovako izgleda citat unutar članka.</blockquote><ul><li>Lista – stavka jedan</li><li>Lista – stavka dva</li></ul>")
    for i, (cat, title, tags, pinned) in enumerate(DEMO_ARTICLES):
        img = media[i % len(media)] if media else None
        pub = iso(now() - timedelta(hours=i * 3 + 1))
        gallery = media[:4] if cat == "kultura" else []
        await db.articles.insert_one({
            "id": new_id(), "title": title, "subtitle": "Primjer podnaslova koji ukratko objašnjava suštinu vijesti.",
            "summary": "Primjer kratkog sažetka koji se prikazuje na naslovnoj stranici i u rezultatima pretrage.", "body": body,
            "slug": slugify(title), "status": "published", "category_id": cats.get(cat), "category_ids": [], "tags": tags + ["primjer"],
            "tags_folded": [fold(t) for t in tags + ["primjer"]], "author_ids": [admin_id], "source": "Redakcija", "source_author": "",
            "featured_image": img, "gallery": gallery, "video_urls": [], "seo_title": "", "seo_description": "", "canonical_url": "",
            "social_image": "", "publish_at": None, "published_at": pub, "created_at": pub, "updated_at": pub, "is_breaking": i == 0,
            "is_pinned": pinned, "is_exclusive": i == 2, "is_sponsored": False, "allow_comments": True, "show_views": True, "views": (8 - i) * 37,
            "deleted": False, "was_published": True, "has_video": False, "created_by": admin_id, "is_demo": True,
            "search_text": fold(f"{title} {' '.join(tags)} primjer {body}")})
    first = await db.articles.find_one({"is_breaking": True}, {"id": 1, "title": 1})
    if first:
        await db.breaking_news.insert_one({"id": new_id(), "title": "PRIMJER: Ovdje se prikazuje hitna vijest – uredite je u modulu Breaking News",
                                           "article_id": first["id"], "priority": 5, "active": True, "start_at": "", "end_at": "",
                                           "created_by": "Sistem", "created_at": iso()})
