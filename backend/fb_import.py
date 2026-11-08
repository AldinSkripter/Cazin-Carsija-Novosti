import re
import os
import hmac
import json
import hashlib
import logging
import html
import asyncio
import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from pymongo.errors import DuplicateKeyError

from core import db, new_id, iso, require, audit, get_settings
from services import process_image, ai_generate
from routes_articles import ArticleIn, prepare, save_version

router = APIRouter(prefix="/api/admin/facebook")
cron_router = APIRouter(prefix="/api/cron")
IMPORT_LOCK = asyncio.Lock()
log = logging.getLogger("fb_import")
SMALL = {"za", "na", "u", "i", "s", "sa", "o", "od", "do", "iz", "po", "uz", "je", "se", "li", "ne", "a", "te", "ili", "pri", "ko", "što", "sve", "će", "su", "bez", "čak", "ali", "kad", "ima"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def clean_line(s: str) -> str:
    s = "".join(c for c in s if unicodedata.category(c) not in ("So", "Sk", "Cs", "Co", "Mn") and c not in "\u200d\ufe0f")
    return re.sub(r"\s+", " ", s).strip(" \u201e\u201c\u201d\"'-–")


def make_title(line: str) -> str:
    t = clean_line(line)
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        words = t.lower().split(" ")
        t = " ".join(w.upper() if any(ch.isdigit() for ch in w) or (len(w.strip("!?.,:")) <= 3 and w.strip("!?.,:") not in SMALL) else w for w in words)
        t = t[:1].upper() + t[1:]
    return t[:200] or "Vijest"


def parse_post(msg: str):
    lines = [ln.rstrip() for ln in msg.replace("\r", "").split("\n")]
    while lines and not clean_line(lines[0]):
        lines.pop(0)
    title = make_title(lines[0]) if lines else "Vijest"
    rest, tags = [], []
    for ln in lines[1:]:
        if ln.strip() and all(w.startswith("#") for w in ln.split()):
            tags += [w.lstrip("#") for w in ln.split() if len(w) > 1]
        else:
            rest.append(ln)
    paras = [p.strip() for p in "\n".join(rest).split("\n\n") if p.strip()]
    lead = clean_line(paras[0]) if paras else ""
    summary = lead[:220].rsplit(" ", 1)[0] + "…" if len(lead) > 220 else lead
    if len(paras) > 1 and len(lead) <= 220:
        paras = paras[1:]
    body = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paras) or f"<p>{html.escape(msg.strip())}</p>"
    return title, summary, body, tags[:10]


async def fetch_live(page_url: str) -> list:
    url = f"https://www.facebook.com/plugins/page.php?href={quote(page_url, safe='')}&tabs=timeline&width=500&height=3000&locale=bs_BA"
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "bs,hr;q=0.9,en;q=0.8"}) as c:
        r = await c.get(url)
    i = r.text.find('"timelinePosts":')
    if r.status_code != 200 or i < 0:
        raise HTTPException(502, "Facebook trenutno ne vraća objave stranice. Pokušajte ponovo za nekoliko minuta.")
    posts, _ = json.JSONDecoder().raw_decode(r.text[i + len('"timelinePosts":'):])
    return [p for p in posts if (p.get("message") or "").strip()]


CACHE_FIELDS = ("message", "createdTime", "photoURL", "attachmentType")


async def fetch_posts(page_url: str, hours: int = 24) -> list:
    try:
        live = await fetch_live(page_url)
    except HTTPException:
        live = []
    for p in live:
        await db.fb_posts.update_one({"key": post_key(p)}, {"$set": {k: p.get(k) for k in CACHE_FIELDS}, "$setOnInsert": {"first_seen": iso()}}, upsert=True)
    since = datetime.now(timezone.utc).timestamp() - hours * 3600
    cached = await db.fb_posts.find({"createdTime": {"$gte": since}}, {"_id": 0}).to_list(500)
    if not live and not cached:
        raise HTTPException(502, "Facebook trenutno ne vraća objave stranice. Pokušajte ponovo za nekoliko minuta.")
    merged = {post_key(p): p for p in cached}
    merged.update({post_key(p): p for p in live})
    return sorted(merged.values(), key=lambda p: p.get("createdTime") or 0, reverse=True)


async def save_image(url: str, user):
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers={"User-Agent": UA}) as c:
        r = await c.get(url)
    r.raise_for_status()
    mid, variants, w, h = await asyncio.to_thread(process_image, r.content)
    doc = {"id": mid, "filename": "facebook.jpg", **variants, "width": w, "height": h, "alt": "", "caption": "", "credit": "Facebook – Cazin Čaršija Novosti",
           "source": "Facebook", "category": "facebook", "size": len(r.content), "uploaded_by": user["name"], "uploaded_by_id": user["id"],
           "created_at": iso(), "deleted": False, "search": "facebook uvoz"}
    await db.media.insert_one(doc)
    return {"id": mid, **variants, "alt": "", "credit": doc["credit"]}


def post_hash(msg: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", msg).strip().lower()[:300].encode()).hexdigest()


JUNK = re.compile(r"\b(traži se posao|tražim posao|potražnja za poslom|traži posao|stan za iznajmljivanje|stan za izdavanje|izdaje se (stan|kuća|soba|poslovni|apartman|garsonjera)|izdajem|iznajmljuje se|traži se stan|tražim stan|na prodaju|prodajem|prodaje se|kupujem|mali oglas|mali oglasi)\b", re.I)


def junk_reason(p):
    if not p.get("photoURL"):
        return "bez slike"
    return "oglas" if JUNK.search(p.get("message") or "") else None


def is_junk(p) -> bool:
    return junk_reason(p) is not None


TOPIC_RULES = {
    "obavjestenja": [(r"obavještavamo vas o smrti|obavještenje o smrti|smrtovnic|dženaz|rahmetli|preselio na ahiret|preselila na ahiret|posljednji ispraćaj|ukop će se obaviti|klanjanje dženaze", 5),
                     (r"preminu(o|la)|tužnu vijest|s tugom|sa tugom|izraz\w* saučešć|saučešć|komemoracij|vječna pamet|neka mu je rahmet|neka joj je rahmet", 2)],
    "sport": [(r"utakmic|nogomet|fudbal|košark|rukomet|odbojk|\bnk [a-zčćžšđ]|\bfk [a-zčćžšđ]|\bok [a-zčćžšđ]\w+ (pobijed|izgubi)|\brk [a-zčćžšđ]|\bkk [a-zčćžšđ]", 3),
              (r"\bgol\b|golov|turnir|prvenstv|\bligi?\b|ligu\b|trener|sportaš|sportist|medalj|karate|džudo|kik-?boks|boks|šahov|maraton|atleti|stadion|navijač|\bdres|sezon\w* (u|na) ligi|plasman|finale|polufinale|kupš", 1)],
    "hronika": [(r"policij|uhapšen|uhaps|lišen\w* slobode|krivičn\w* djel|ubist|ubijen|pljačk|razbojništv|tužilaštv|pritvor|optužnic|vozilom udario|saobraćajn\w* nesreć|poginu|teško povrijeđ", 3),
                (r"nesreć|požar|vatrogas|krađ|ukraden|nestal\w* osob|nestao|nestala|povrijeđen|sudar|prijavljen\w* policij|droga|narkotik|\bmup\b", 2)],
    "politika": [(r"gradsk\w* vijeć|općinsk\w* vijeć|skupštin\w* usk|vlad[aeiu] usk|parlament|zastupničk|izborn\w* (kampanj|komisij)|lokaln\w* izbor|opći izbor", 3),
                 (r"načelnik|gradonačelnik|ministar|ministarstv|stranka|stranke|kandidat|vijećnik|sjednic|premijer|predsjedništv|\bsda\b|\bsdp\b|\bnip\b|\bdf\b|\bsnsd\b|\bhdz\b", 2)],
    "zdravlje": [(r"dom zdravlja|bolnic|kantonaln\w* bolnic|\bkbc\b|\bukc\b|hitna pomoć|vakcin|epidemij", 3), (r"doktor|ljekar|pacijent|zdravstv|ambulant|liječen|operacij|bolest|gripa|virus", 1)],
    "obrazovanje": [(r"osnovn\w* škol|srednj\w* škol|gimnazij|fakultet|univerzitet|maturant|upis u škol|polugodišt|nastavn\w* godin", 3), (r"škol|učeni|student|nastavni|profesor|vrtić|đak|đaci", 1)],
    "kultura": [(r"izložb|koncert|festival|pozorišt|teatar|promocij\w* knjig|književn|muzej|galerij\w* (umjetn|slika)|smotr\w* folklor", 3),
                (r"umjetn|slikar|pjesni|knjig|kultur|folklor|bakrorez|reljef|tradicij|zavičaj|predstav\w* (u|na)|film", 1)],
    "ekonomija": [(r"investic|privred|preduzeć|zapošljav|nov\w* radn\w* mjest|tvornic|fabrik|izvoz|inflacij|\bkm\b.*(milion|hiljad)|budžet", 3),
                  (r"firma|kompanij|poduzetni|cijen[aeu]|plat[aeu]|penzij|otvoren\w* (nov\w* )?(market|prodavnic|radnj|trgovin)|poljoprivred", 1)],
    "vremenska-prognoza": [(r"vremensk\w* prognoz|meteorološ|\bfhmz\b|upozorenje (na|zbog) (kiš|snijeg|olu|nevrem|vruć)|narandžast\w* upozorenj|žut\w* upozorenj", 3),
                           (r"snijeg|olujn|nevrijeme|nevremen|padavin|temperatur|toplotn\w* tal|mraz|poplav", 1)],
    "tehnologija": [(r"internet|aplikacij|umjetn\w* inteligencij|\bai\b|softver|pametn\w* telefon|5g|optik", 2)],
    "drustvo": [(r"humanitarn|donacij|volonter|udruženj|akcij\w* (čišćenj|prikupljanj)|pomoć porodic|socijaln|penzioner|mladi|žene|djec\w* (bez|sa)|tradicionaln\w* manifestacij", 2),
                (r"porodic|zajednic|građan|stanovni|selo|mjesn\w* zajednic|džamij|ramazan|bajram|iftar", 1)],
    "zanimljivosti": [(r"zanimljiv|nevjerovatn|rekord|neobičn|vijest dana", 2)],
}
PLACE_RULES = [
    ("bihac", r"bihać|bihac"), ("velika-kladusa", r"velik\w* kladuš|kladuš"), ("bosanska-krupa", r"bosansk\w* krup|\bkrup[aiu]\b"),
    ("buzim", r"bužim|buzim"), ("bosanski-petrovac", r"bosansk\w* petrovc|bosanski petrovac|petrovc"), ("sanski-most", r"sansk\w* most|sanskom mostu"),
    ("kljuc", r"ključ\b|ključu\b"), ("cazin", r"cazin"),
]
SCOPE_RULES = [("unsko-sanski-kanton", r"unsko-sansk|\busk\b"), ("bosna-i-hercegovina", r"\bbih\b|bosn\w* i hercegovin|federacij\w* bih|sarajev|mostar|tuzl|zenic|banj\w* luk"),
               ("region", r"hrvatsk|srbij|crn\w* gor|sloveni|zagreb|beograd"), ("svijet", r"njemačk|austrij|amerik|\bsad\b|evropsk\w* unij|rusij|ukrajin|turskoj|turska")]
AI_TOPICS = {"sport": "sport", "hronika": "crna hronika, policija, nesreće", "politika": "politika, vlast, vijeće, izbori", "drustvo": "društvo, humanitarno, zajednica",
             "ekonomija": "ekonomija, posao, firme", "kultura": "kultura, umjetnost, događaji", "zdravlje": "zdravlje", "obrazovanje": "škole i obrazovanje",
             "vremenska-prognoza": "vrijeme i prognoza", "tehnologija": "tehnologija", "zanimljivosti": "zanimljivosti", "obavjestenja": "obavještenje o smrti, dženaza",
             "lokalno": "opća lokalna vijest bez posebne teme"}


def topic_scores(t: str) -> dict:
    return {slug: sum(w * len(re.findall(rx, t)) for rx, w in rules) for slug, rules in TOPIC_RULES.items()}


def detect_place(t: str):
    hits = {s: len(re.findall(rx, t)) for s, rx in PLACE_RULES}
    place = max((s for s in hits if hits[s] and s != "cazin"), key=lambda s: hits[s], default=None)
    if place and hits[place] >= hits["cazin"]:
        return place
    if hits["cazin"]:
        return "cazin"
    return next((s for s, rx in SCOPE_RULES if re.search(rx, t)), "cazin")


def detect_categories(text: str, topic=None):
    t = text.lower()
    scores = topic_scores(t)
    if scores["obavjestenja"] >= 4:
        return "obavjestenja", []
    if topic is None:
        best = max(scores, key=scores.get)
        topic = best if scores[best] >= 3 else None
    if topic in (None, "lokalno"):
        return detect_place(t), []
    if topic == "obavjestenja":
        return "obavjestenja", []
    return topic, [detect_place(t)]


async def ai_topic(text: str):
    if os.environ.get("AI_PROVIDER") == "off":
        return None
    opts = "\n".join(f"{k} = {v}" for k, v in AI_TOPICS.items())
    prompt = (f"Razvrstaj objavu lokalnog portala u JEDNU rubriku. Odgovori SAMO oznakom s lijeve strane, bez ikakvog drugog teksta.\n{opts}\n\n"
              f"Objava:\n{text[:1500]}")
    try:
        ans = (await asyncio.wait_for(ai_generate(prompt), 90)).strip().lower()
    except Exception as e:
        log.info("AI rubrika nije dostupna: %s", e)
        return None
    return next((k for k in sorted(AI_TOPICS, key=len, reverse=True) if k in ans), None)


async def resolve_categories(text: str, forced: str = None):
    if forced:
        primary, extra = forced, ([detect_place(text.lower())] if forced not in [s for s, _ in PLACE_RULES] + ["obavjestenja"] else [])
    else:
        primary, extra = detect_categories(text, await ai_topic(text))
    cats = {c["slug"]: c["id"] async for c in db.categories.find({"slug": {"$in": [primary, *extra, "cazin"]}}, {"slug": 1, "id": 1})}
    main = cats.get(primary) or cats.get("cazin")
    if not main:
        c = await db.categories.find_one({}, {"id": 1})
        main = c and c["id"]
    return main, [cats[s] for s in extra if s in cats and cats[s] != main]


def post_key(p) -> str:
    return f"fb-{p.get('createdTime')}"


async def post_status(key: str, h: str) -> str:
    if await db.articles.find_one({"$or": [{"fb_post_key": key}, {"fb_post_hash": h}]}, {"_id": 1}):
        return "imported"
    return "ignored" if await db.fb_ignored.find_one({"key": key}, {"_id": 1}) else "new"


@router.get("/posts")
async def list_posts(user=Depends(require("articles.publish"))):
    settings = await get_settings()
    page = (settings.get("social") or {}).get("facebook") or "https://www.facebook.com/cazin.carsija"
    out = []
    for p in await fetch_posts(page):
        title, summary, _, _ = parse_post(p["message"])
        created = datetime.fromtimestamp(p["createdTime"], timezone.utc).isoformat() if p.get("createdTime") else None
        out.append({"key": post_key(p), "title": title, "summary": summary, "image": p.get("photoURL"), "created_at": created,
                    "suggested": not is_junk(p), "reason": junk_reason(p), "category": detect_categories(p["message"])[0], "status": await post_status(post_key(p), post_hash(p["message"]))})
    return out


async def run_import(user, limit=8, remove_samples=False, auto=False, operator=None, keys=None, max_age_hours=None, forced=None):
    async with IMPORT_LOCK:
        settings = await get_settings()
        page = (settings.get("social") or {}).get("facebook") or "https://www.facebook.com/cazin.carsija"
        posts = (await fetch_posts(page))[:max(limit, 50)]
        imported, skipped, ignored = [], 0, 0
        min_ts = datetime.now(timezone.utc).timestamp() - max_age_hours * 3600 if max_age_hours else 0
        for p in reversed(posts):
            key, h = post_key(p), post_hash(p["message"])
            if keys is not None and key not in keys:
                if await post_status(key, h) == "new":
                    await db.fb_ignored.update_one({"key": key}, {"$setOnInsert": {"key": key, "hash": h, "at": iso()}}, upsert=True)
                    ignored += 1
                continue
            if (p.get("createdTime") or 0) < min_ts or (keys is None and is_junk(p)):
                continue
            status = await post_status(key, h)
            if status == "imported" or (status == "ignored" and keys is None):
                skipped += 1
                continue
            title, summary, html_body, tags = parse_post(p["message"])
            img = None
            if p.get("photoURL"):
                try:
                    img = await save_image(p["photoURL"], user)
                except Exception as e:
                    log.warning("FB slika nije preuzeta: %s", e)
            aid = new_id()
            cat_id, extra_ids = await resolve_categories(p["message"], (forced or {}).get(key))
            data = await prepare(ArticleIn(title=title, summary=summary, body=html_body, tags=tags, category_id=cat_id, category_ids=extra_ids,
                                           source="Facebook stranica Cazin Čaršija Novosti", featured_image=img).model_dump(), aid, user)
            pub = datetime.fromtimestamp(p["createdTime"], timezone.utc).isoformat() if p.get("createdTime") else iso()
            data.update(id=aid, status="published", published_at=pub, published_by=user["id"], was_published=True, created_by=user["id"],
                        created_at=iso(), views=0, deleted=False, fb_post_key=key, fb_post_hash=h)
            try:
                await db.articles.insert_one(data)
            except DuplicateKeyError:
                skipped += 1
                continue
            await save_version(data, user, "Automatski uvezeno sa Facebooka" if auto else "Uvezeno sa Facebooka")
            await db.fb_ignored.delete_one({"key": key})
            imported.append(title)
        removed = 0
        if remove_samples:
            res = await db.articles.update_many({"tags": "primjer", "body": {"$regex": "primjer članka"}, "deleted": {"$ne": True}},
                                                {"$set": {"deleted": True, "status": "archived"}})
            removed = res.modified_count
        await db.settings.update_one({"key": "fb_auto"}, {"$set": {"value.last_run": iso(), "value.last_imported": len(imported), "value.last_error": None}}, upsert=True)
        if imported or not auto:
            await audit(operator or user, "facebook.import", "article", "", f"{'auto: ' if auto else ''}uvezeno {len(imported)}, preskočeno {skipped}, obrisano probnih {removed}")
        return {"imported": imported, "skipped": skipped, "ignored": ignored, "removed_samples": removed}


async def auto_state():
    s = await db.settings.find_one({"key": "fb_auto"}, {"_id": 0}) or {}
    return {"enabled": True, "last_run": None, "last_imported": 0, "author_id": None, **(s.get("value") or {})}


async def import_author(fallback=None):
    st = await auto_state()
    u = st.get("author_id") and await db.users.find_one({"id": st["author_id"], "active": True, "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1})
    return u or fallback or await db.users.find_one({"role": "super_admin", "active": True, "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1}, sort=[("created_at", 1)])


@router.post("/import")
async def import_posts(body: dict = Body(default={}), user=Depends(require("articles.publish"))):
    author = await import_author() or user
    keys = body.get("keys")
    if keys is not None and not isinstance(keys, list):
        raise HTTPException(400, "Neispravan izbor objava")
    return await run_import({**user, "id": author["id"], "name": author["name"]}, int(body.get("limit") or 8), bool(body.get("remove_samples")),
                            operator=user, keys=set(keys) if keys is not None else None, forced=await valid_forced(body.get("categories")))


async def valid_forced(m):
    if not isinstance(m, dict) or not m:
        return None
    slugs = {c["slug"] async for c in db.categories.find({}, {"slug": 1})}
    return {k: v for k, v in m.items() if isinstance(v, str) and v in slugs}


@router.get("/auto")
async def get_auto(user=Depends(require("articles.publish"))):
    return await auto_state()


@router.put("/auto")
async def set_auto(body: dict = Body(...), user=Depends(require("articles.publish"))):
    upd = {}
    if "enabled" in body:
        upd["value.enabled"] = bool(body["enabled"])
    if "author_id" in body:
        if body["author_id"] and not await db.users.find_one({"id": body["author_id"], "active": True, "deleted": {"$ne": True}}):
            raise HTTPException(400, "Nepoznat autor")
        upd["value.author_id"] = body["author_id"] or None
    await db.settings.update_one({"key": "fb_auto"}, {"$set": upd}, upsert=True)
    await audit(user, "facebook.auto", "settings", "fb_auto", json.dumps(body, ensure_ascii=False)[:200])
    return await auto_state()


async def auto_job():
    if not (await auto_state())["enabled"]:
        return
    owner = await import_author()
    if not owner:
        return
    try:
        res = await run_import(owner, 8, auto=True)
        log.info("FB auto uvoz: %s novih, %s preskočeno", len(res["imported"]), res["skipped"])
    except Exception as e:
        log.warning("FB auto uvoz nije uspio: %s", e)
        await db.settings.update_one({"key": "fb_auto"}, {"$set": {"value.last_error": f"{iso()}: {getattr(e, 'detail', e)}"[:300]}}, upsert=True)


@cron_router.post("/facebook-import")
async def cron_fb(request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].encode(), os.environ["WEBHOOK_CRON_SECRET"].encode()):
        raise HTTPException(401, "Unauthorized")
    if IMPORT_LOCK.locked():
        return {"ok": True, "busy": True}
    asyncio.create_task(auto_job())
    return {"ok": True}
