import re
import json
import html
import asyncio
import unicodedata
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Depends, Body

from core import db, new_id, iso, require, audit, get_settings
from services import process_image
from routes_articles import ArticleIn, prepare, save_version

router = APIRouter(prefix="/api/admin/facebook")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def clean_line(s: str) -> str:
    s = "".join(c for c in s if unicodedata.category(c) not in ("So", "Sk", "Cs", "Co", "Mn") and c not in "\u200d\ufe0f")
    return re.sub(r"\s+", " ", s).strip(" \u201e\u201c\u201d\"'-–")


def make_title(line: str) -> str:
    t = clean_line(line)
    letters = [c for c in t if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        words = t.lower().split(" ")
        t = " ".join(w.upper() if any(ch.isdigit() for ch in w) else w for w in words)
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
    body = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paras) or f"<p>{html.escape(msg.strip())}</p>"
    plain = clean_line(" ".join(paras))
    summary = plain[:220].rsplit(" ", 1)[0] + "…" if len(plain) > 220 else plain
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


@router.post("/import")
async def import_posts(body: dict = Body(default={}), user=Depends(require("articles.publish"))):
    settings = await get_settings()
    page = (settings.get("social") or {}).get("facebook") or "https://www.facebook.com/cazin.carsija"
    posts = (await fetch_posts(page))[: int(body.get("limit") or 8)]
    cat = await db.categories.find_one({"slug": "cazin"}, {"id": 1}) or await db.categories.find_one({}, {"id": 1})
    imported, skipped = [], 0
    for p in reversed(posts):
        key = f"fb-{p.get('createdTime')}"
        if await db.articles.find_one({"fb_post_key": key}):
            skipped += 1
            continue
        title, summary, html_body, tags = parse_post(p["message"])
        img = None
        if p.get("photoURL"):
            try:
                img = await save_image(p["photoURL"], user)
            except Exception:
                img = None
        aid = new_id()
        data = await prepare(ArticleIn(title=title, summary=summary, body=html_body, tags=tags, category_id=cat and cat["id"],
                                       source="Facebook stranica Cazin Čaršija Novosti", featured_image=img).model_dump(), aid, user)
        pub = datetime.fromtimestamp(p.get("createdTime") or 0, timezone.utc).isoformat() if p.get("createdTime") else iso()
        data.update(id=aid, status="published", published_at=pub, published_by=user["id"], was_published=True, created_by=user["id"],
                    created_at=iso(), views=0, deleted=False, fb_post_key=key)
        await db.articles.insert_one(data)
        await save_version(data, user, "Uvezeno sa Facebooka")
        imported.append(title)
    removed = 0
    if body.get("remove_samples"):
        res = await db.articles.update_many({"tags": "primjer", "body": {"$regex": "primjer članka"}, "deleted": {"$ne": True}},
                                            {"$set": {"deleted": True, "status": "archived"}})
        removed = res.modified_count
    await audit(user, "facebook.import", "article", "", f"uvezeno {len(imported)}, preskočeno {skipped}, obrisano probnih {removed}")
    return {"imported": imported, "skipped": skipped, "removed_samples": removed}
