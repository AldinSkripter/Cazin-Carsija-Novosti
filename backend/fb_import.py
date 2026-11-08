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
from services import process_image
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


async def fetch_posts(page_url: str) -> list:
    url = f"https://www.facebook.com/plugins/page.php?href={quote(page_url, safe='')}&tabs=timeline&width=500&height=3000&locale=bs_BA"
    async with httpx.AsyncClient(timeout=25, follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "bs,hr;q=0.9,en;q=0.8"}) as c:
        r = await c.get(url)
    i = r.text.find('"timelinePosts":')
    if r.status_code != 200 or i < 0:
        raise HTTPException(502, "Facebook trenutno ne vraća objave stranice. Pokušajte ponovo za nekoliko minuta.")
    posts, _ = json.JSONDecoder().raw_decode(r.text[i + len('"timelinePosts":'):])
    return [p for p in posts if (p.get("message") or "").strip()]


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


async def run_import(user, limit=8, remove_samples=False, auto=False, operator=None):
    async with IMPORT_LOCK:
        settings = await get_settings()
        page = (settings.get("social") or {}).get("facebook") or "https://www.facebook.com/cazin.carsija"
        posts = (await fetch_posts(page))[:limit]
        cat = await db.categories.find_one({"slug": "cazin"}, {"id": 1}) or await db.categories.find_one({}, {"id": 1})
        imported, skipped = [], 0
        for p in reversed(posts):
            key, h = f"fb-{p.get('createdTime')}", post_hash(p["message"])
            if await db.articles.find_one({"$or": [{"fb_post_key": key}, {"fb_post_hash": h}]}, {"_id": 1}):
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
            data = await prepare(ArticleIn(title=title, summary=summary, body=html_body, tags=tags, category_id=cat and cat["id"],
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
            imported.append(title)
        removed = 0
        if remove_samples:
            res = await db.articles.update_many({"tags": "primjer", "body": {"$regex": "primjer članka"}, "deleted": {"$ne": True}},
                                                {"$set": {"deleted": True, "status": "archived"}})
            removed = res.modified_count
        await db.settings.update_one({"key": "fb_auto"}, {"$set": {"value.last_run": iso(), "value.last_imported": len(imported), "value.last_error": None}}, upsert=True)
        if imported or not auto:
            await audit(operator or user, "facebook.import", "article", "", f"{'auto: ' if auto else ''}uvezeno {len(imported)}, preskočeno {skipped}, obrisano probnih {removed}")
        return {"imported": imported, "skipped": skipped, "removed_samples": removed}


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
    return await run_import({**user, "id": author["id"], "name": author["name"]}, int(body.get("limit") or 8), bool(body.get("remove_samples")), operator=user)


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
