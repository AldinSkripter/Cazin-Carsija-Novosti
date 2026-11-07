import os
import asyncio
import re
import time
import random
import hashlib
import hmac
import secrets as pysecrets
from html import escape
from datetime import timedelta

import httpx
import jwt
from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from pydantic import BaseModel

from core import db, new_id, iso, now, fold, get_settings, client_ip, rate_limit, strip_tags, secret, JWT_ALG, permissions_for
from articles_common import query_articles, enrich, publish_due, public_filter, CARD
from services import get_object, process_image, put_object, APP_NAME, send_email, email_template
from newsletter import auto_digest, base_url

router = APIRouter(prefix="/api")
PUBLIC_SETTINGS = ["site_name", "tagline", "logo_url", "logo_mobile_url", "favicon_url", "social_image", "contact_email", "phone",
                   "address", "social", "main_menu", "footer_menu", "footer_text", "ga4_id", "plausible_domain", "comments_enabled",
                   "show_views", "newsletter_enabled", "maintenance_mode", "maintenance_message", "google_site_verification",
                   "adsense_client", "site_url", "publisher_name"]


async def optional_perms(request: Request):
    token = request.cookies.get("access_token")
    try:
        p = jwt.decode(token, secret(), algorithms=[JWT_ALG])
        u = await db.users.find_one({"id": p["sub"]}, {"_id": 0})
        if u and await db.sessions.find_one({"id": p["sid"], "revoked": False}):
            return await permissions_for(u)
    except Exception:
        pass
    return []


@router.get("/public/settings")
async def public_settings():
    s = await get_settings()
    return {k: s.get(k) for k in PUBLIC_SETTINGS}


@router.get("/public/categories")
async def public_categories():
    return await db.categories.find({"visible": True}, {"_id": 0}).sort("order", 1).to_list(500)


@router.get("/public/articles")
async def list_articles(category: str = None, tag: str = None, author: str = None, q: str = None, date_from: str = None,
                        date_to: str = None, sort: str = "latest", video: bool = False, gallery: bool = False, page: int = 1, limit: int = 12):
    return await query_articles(category, tag, author, q, date_from, date_to, sort, video, gallery, max(page, 1), min(limit, 50))


async def resolve_block(b, used):
    t, lim = b.get("type"), int(b.get("limit") or 6)
    res = None
    if t == "hero":
        pinned = await db.articles.find(public_filter({"is_pinned": True}), CARD).sort("published_at", -1).limit(5).to_list(5)
        rest = await db.articles.find(public_filter({"id": {"$nin": [p["id"] for p in pinned]}}), CARD).sort("published_at", -1).limit(5 - len(pinned)).to_list(5)
        res = await enrich(pinned + rest)
    elif t in ("latest", "category", "video", "gallery"):
        r = await query_articles(category=b.get("category_slug") if t == "category" else None, video=t == "video",
                                 gallery=t == "gallery", limit=lim, exclude=list(used) if b.get("dedupe", True) else None)
        res = r["items"]
        if not res and used and t != "latest":
            res = (await query_articles(category=b.get("category_slug") if t == "category" else None, video=t == "video",
                                        gallery=t == "gallery", limit=lim))["items"]
    elif t == "most_read":
        res = (await query_articles(sort="popular", limit=lim))["items"]
    elif t == "manual":
        ids = b.get("article_ids") or []
        docs = await db.articles.find(public_filter({"id": {"$in": ids}}), CARD).to_list(50)
        res = await enrich(sorted(docs, key=lambda a: ids.index(a["id"])))
    if res is not None:
        if t in ("hero", "manual"):
            used.update(a["id"] for a in res)
        b["articles"] = res
    return b


@router.get("/public/home")
async def home(request: Request, preview: bool = False):
    await publish_due()
    doc = await db.settings.find_one({"key": "homepage"}, {"_id": 0}) or {}
    blocks = (doc.get("value") or {}).get("published", [])
    if preview and "homepage.manage" in await optional_perms(request):
        blocks = (doc.get("value") or {}).get("draft", blocks)
    used = set()
    out = []
    for b in sorted(blocks, key=lambda x: x.get("order", 0)):
        if b.get("visible", True):
            out.append(await resolve_block(dict(b), used))
    return {"blocks": out}


@router.get("/public/articles/{slug}")
async def article_detail(slug: str):
    await publish_due()
    a = await db.articles.find_one({"slug": slug, "deleted": {"$ne": True}}, {"_id": 0, "search_text": 0})
    if not a or a["status"] != "published":
        red = await db.redirects.find_one({"from_path": f"/vijesti/{slug}"}, {"_id": 0})
        if red:
            return {"redirect": red["to_path"], "code": red.get("code", 301)}
        if a and a.get("was_published"):
            raise HTTPException(410, "Članak je uklonjen")
        raise HTTPException(404, "Članak nije pronađen")
    await enrich([a])
    rel_f = public_filter({"id": {"$ne": a["id"]}, "$or": [{"category_id": a.get("category_id")}, {"tags": {"$in": a.get("tags", [])}}]})
    related = await db.articles.find(rel_f, CARD).sort("published_at", -1).limit(6).to_list(6)
    a["related"] = await enrich(related)
    s = await get_settings()
    if not s.get("show_views", True) or not a.get("show_views", True):
        a.pop("views", None)
    a["comments_open"] = bool(s.get("comments_enabled") and a.get("allow_comments", True))
    return a


@router.get("/public/breaking")
async def breaking():
    t = iso()
    f = {"active": True, "$and": [{"$or": [{"start_at": {"$in": [None, ""]}}, {"start_at": {"$lte": t}}]},
                                  {"$or": [{"end_at": {"$in": [None, ""]}}, {"end_at": {"$gte": t}}]}]}
    items = await db.breaking_news.find(f, {"_id": 0}).sort([("priority", -1), ("created_at", -1)]).to_list(10)
    for b in items:
        if b.get("article_id"):
            a = await db.articles.find_one({"id": b["article_id"], "status": "published"}, {"slug": 1})
            b["article_slug"] = a["slug"] if a else None
    return items


@router.get("/public/tags/popular")
async def popular_tags(limit: int = 15):
    pipe = [{"$match": public_filter({"published_at": {"$gte": iso(now() - timedelta(days=30))}})}, {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}, "views": {"$sum": "$views"}}}, {"$sort": {"views": -1, "count": -1}}, {"$limit": limit}]
    return [{"name": r["_id"], "count": r["count"]} async for r in db.articles.aggregate(pipe)]


@router.get("/public/authors")
async def authors():
    return await db.users.find({"active": True, "deleted": {"$ne": True}, "show_public": {"$ne": False}, "role": {"$in": ["super_admin", "chief_editor", "editor", "journalist", "author"]}},
                               {"_id": 0, "id": 1, "name": 1, "slug": 1, "bio": 1, "avatar": 1, "role": 1}).to_list(200)


@router.get("/public/authors/{slug}")
async def author(slug: str):
    u = await db.users.find_one({"slug": slug, "deleted": {"$ne": True}}, {"_id": 0, "id": 1, "name": 1, "slug": 1, "bio": 1, "avatar": 1, "role": 1})
    if not u:
        raise HTTPException(404, "Autor nije pronađen")
    return u


@router.get("/public/pages/{slug}")
async def page(slug: str):
    p = await db.pages.find_one({"slug": slug, "published": True}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Stranica nije pronađena")
    return p


# ---------- Ads ----------
@router.get("/public/ads")
async def ads(positions: str):
    t = iso()
    out = {}
    for pos in positions.split(",")[:12]:
        f = {"position": pos, "active": True, "$and": [{"$or": [{"start_at": {"$in": [None, ""]}}, {"start_at": {"$lte": t}}]},
                                                      {"$or": [{"end_at": {"$in": [None, ""]}}, {"end_at": {"$gte": t}}]}]}
        cands = [c for c in await db.ad_campaigns.find(f, {"_id": 0}).to_list(30)
                 if not c.get("max_impressions") or c.get("impressions", 0) < c["max_impressions"]]
        if cands:
            c = random.choices(cands, weights=[max(int(c.get("weight") or 1), 1) for c in cands])[0]
            out[pos] = {k: c.get(k) for k in ("id", "name", "type", "image_url", "mobile_image_url", "html_code", "sponsored_label", "position", "alt")}
    return out


@router.post("/public/ads/{cid}/impression")
async def ad_impression(cid: str, request: Request):
    rate_limit(f"imp:{client_ip(request)}:{cid}", 30, 60)
    await db.ad_campaigns.update_one({"id": cid}, {"$inc": {"impressions": 1}})
    await db.ad_events.insert_one({"campaign_id": cid, "type": "impression", "day": iso()[:10], "created_at": iso()})
    return {"ok": True}


@router.get("/public/ads/{cid}/click")
async def ad_click(cid: str):
    c = await db.ad_campaigns.find_one({"id": cid}, {"_id": 0})
    if not c or not str(c.get("target_url", "")).startswith(("http://", "https://")):
        raise HTTPException(404, "Oglas nije pronađen")
    await db.ad_campaigns.update_one({"id": cid}, {"$inc": {"clicks": 1}})
    await db.ad_events.insert_one({"campaign_id": cid, "type": "click", "day": iso()[:10], "created_at": iso()})
    return RedirectResponse(c["target_url"], status_code=302)


# ---------- Cameras & Weather ----------
_cam_cache = {}


@router.get("/public/cameras")
async def cameras():
    return await db.cameras.find({"active": True}, {"_id": 0}).sort("order", 1).to_list(100)


@router.get("/public/cameras/{cid}/image")
async def camera_image(cid: str):
    cam = await db.cameras.find_one({"id": cid, "active": True}, {"_id": 0})
    if not cam or not cam.get("image_url"):
        raise HTTPException(404, "Kamera nije pronađena")
    ttl = max(int(cam.get("refresh_seconds") or 60), 15)
    hit = _cam_cache.get(cid)
    if not hit or time.time() - hit[0] > ttl:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
                r = await c.get(cam["image_url"], headers={"User-Agent": "Mozilla/5.0 CCN-Portal"})
            if r.status_code != 200 or not r.headers.get("content-type", "").startswith("image"):
                raise ValueError
            hit = (time.time(), r.content, r.headers["content-type"])
            _cam_cache[cid] = hit
        except Exception:
            if not hit:
                raise HTTPException(502, "Kamera trenutno nije dostupna")
    return Response(hit[1], media_type=hit[2], headers={"Cache-Control": f"public, max-age={ttl}"})


_weather = [0.0, None]


@router.get("/public/weather")
async def weather():
    if _weather[1] and time.time() - _weather[0] < 900:
        return _weather[1]
    url = ("https://api.open-meteo.com/v1/forecast?latitude=44.9667&longitude=15.9428&current=temperature_2m,relative_humidity_2m,"
           "weather_code,wind_speed_10m&daily=weather_code,temperature_2m_max,temperature_2m_min&timezone=Europe%2FSarajevo&forecast_days=5")
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            data = (await c.get(url)).json()
        _weather[:] = [time.time(), data]
    except Exception:
        if not _weather[1]:
            raise HTTPException(502, "Prognoza nije dostupna")
    return _weather[1]


# ---------- Comments ----------
class CommentIn(BaseModel):
    name: str
    email: str = ""
    content: str
    parent_id: str | None = None
    website: str = ""


@router.get("/public/articles/{aid}/comments")
async def get_comments(aid: str):
    return await db.comments.find({"article_id": aid, "status": "approved"}, {"_id": 0, "email": 0, "ip_hash": 0}).sort("created_at", 1).to_list(500)


def ip_hash(request):
    return hashlib.sha256(client_ip(request).encode()).hexdigest()[:24]


@router.post("/public/articles/{aid}/comments")
async def post_comment(aid: str, body: CommentIn, request: Request):
    if body.website:
        return {"ok": True, "status": "pending"}
    rate_limit(f"comment:{client_ip(request)}", 5, 300)
    s = await get_settings()
    a = await db.articles.find_one({"id": aid, "status": "published"}, {"allow_comments": 1})
    if not s.get("comments_enabled") or not a or not a.get("allow_comments", True):
        raise HTTPException(403, "Komentari su isključeni")
    name, content = body.name.strip()[:60], strip_tags(body.content)[:2000]
    if len(name) < 2 or len(content) < 3:
        raise HTTPException(400, "Unesite ime i komentar")
    ih = ip_hash(request)
    if await db.blocked_users.find_one({"$or": [{"ip_hash": ih}, {"email": body.email.lower().strip() or "-"}]}):
        raise HTTPException(403, "Komentarisanje vam je onemogućeno")
    spam = len(re.findall(r"https?://", content)) > 2
    status = "spam" if spam else ("pending" if s.get("comments_require_approval", True) else "approved")
    doc = {"id": new_id(), "article_id": aid, "parent_id": body.parent_id, "name": name, "email": body.email.lower().strip()[:120],
           "content": content, "status": status, "reports": 0, "ip_hash": ih, "created_at": iso()}
    await db.comments.insert_one(doc)
    return {"ok": True, "status": status}


@router.post("/public/comments/{cid}/report")
async def report_comment(cid: str, request: Request):
    rate_limit(f"report:{client_ip(request)}", 10, 600)
    await db.comments.update_one({"id": cid}, {"$inc": {"reports": 1}})
    return {"ok": True}


# ---------- Submit news ----------
@router.post("/public/submit-news")
async def submit_news(request: Request, name: str = Form(...), contact: str = Form(...), title: str = Form(...),
                      description: str = Form(...), consent_data: bool = Form(False), consent_rights: bool = Form(False),
                      website: str = Form(""), photos: list[UploadFile] = File(default=[])):
    if website:
        return {"ok": True}
    rate_limit(f"submit:{client_ip(request)}", 3, 600)
    if not (consent_data and consent_rights):
        raise HTTPException(400, "Potrebne su obje saglasnosti")
    if len(title.strip()) < 5 or len(description.strip()) < 20:
        raise HTTPException(400, "Naslov ili opis su prekratki")
    sid = new_id()
    stored = []
    for f in photos[:5]:
        raw = await f.read()
        try:
            mid, variants, w, h = await asyncio.to_thread(process_image, raw)
        except ValueError as e:
            raise HTTPException(400, str(e))
        stored.append({"id": mid, **variants})
    await db.submissions.insert_one({"id": sid, "name": name[:100], "contact": contact[:150], "title": title[:200],
                                     "description": strip_tags(description)[:8000], "photos": stored, "status": "new",
                                     "consent_data": True, "consent_rights": True, "ip_hash": ip_hash(request), "created_at": iso()})
    return {"ok": True}


# ---------- Newsletter ----------
@router.post("/public/newsletter/subscribe")
async def subscribe(body: dict, request: Request):
    rate_limit(f"nl:{client_ip(request)}", 5, 600)
    email = str(body.get("email", "")).strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or not body.get("consent"):
        raise HTTPException(400, "Unesite ispravan e-mail i potvrdite saglasnost")
    freq = body.get("frequency") if body.get("frequency") in ("daily", "weekly") else "weekly"
    ex = await db.newsletter_subscribers.find_one({"email": email})
    if ex and ex.get("status") == "confirmed":
        return {"ok": True, "message": "Već ste prijavljeni."}
    token = pysecrets.token_urlsafe(24)
    await db.newsletter_subscribers.update_one({"email": email}, {"$set": {
        "email": email, "status": "pending", "frequency": freq, "token": token, "consent_at": iso(), "consent_ip_hash": ip_hash(request),
        "consent_text": "Saglasan/na sam s primanjem newslettera i politikom privatnosti."}, "$setOnInsert": {"id": new_id(), "created_at": iso()}}, upsert=True)
    origin = request.headers.get("origin", "")
    sent = False
    if origin.startswith("https://"):
        html = email_template("Potvrdite prijavu na newsletter", "<p>Kliknite na dugme da potvrdite prijavu.</p>",
                              f"{origin}/newsletter?potvrda={token}", "Potvrdi prijavu")
        sent = await send_email(to=email, subject="Potvrdite prijavu na newsletter", html=html)
    return {"ok": True, "message": "Poslali smo vam e-mail za potvrdu." if sent else "Prijava zaprimljena, potvrda će uskoro stići."}


@router.post("/cron/newsletter/{kind}")
async def cron_newsletter(kind: str, request: Request):
    # Cron endpoints must ack 2xx immediately; enqueue/background the actual work.
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].encode(), os.environ["WEBHOOK_CRON_SECRET"].encode()):
        raise HTTPException(401, "Unauthorized")
    if kind not in ("daily", "weekly"):
        raise HTTPException(400, "Invalid kind")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid body")
    run_id = request.headers.get("x-webhook-id") or (body or {}).get("run_id") or new_id()
    try:
        await db.cron_runs.insert_one({"_id": f"nl:{run_id}", "kind": kind, "at": iso()})
    except Exception:
        return {"ok": True, "duplicate": True}
    asyncio.create_task(auto_digest(kind, base_url(await get_settings(), request)))
    return {"ok": True}


@router.get("/public/newsletter/confirm")
async def nl_confirm(token: str):
    r = await db.newsletter_subscribers.update_one({"token": token}, {"$set": {"status": "confirmed", "confirmed_at": iso()}})
    if not r.matched_count:
        raise HTTPException(400, "Link nije ispravan")
    return {"ok": True}


@router.get("/public/newsletter/unsubscribe")
async def nl_unsub(token: str):
    r = await db.newsletter_subscribers.update_one({"token": token}, {"$set": {"status": "unsubscribed", "unsubscribed_at": iso()}})
    if not r.matched_count:
        raise HTTPException(400, "Link nije ispravan")
    return {"ok": True}


# ---------- Analytics & consent ----------
def classify_source(ref: str, host: str):
    ref = (ref or "").lower()
    if not ref or host in ref:
        return "direktno"
    for k, v in (("google", "pretraživači"), ("bing", "pretraživači"), ("yahoo", "pretraživači"), ("facebook", "društvene mreže"),
                 ("instagram", "društvene mreže"), ("t.co", "društvene mreže"), ("twitter", "društvene mreže"), ("x.com", "društvene mreže"),
                 ("viber", "društvene mreže"), ("whatsapp", "društvene mreže")):
        if k in ref:
            return v
    return "ostale stranice"


@router.post("/public/track")
async def track(body: dict, request: Request):
    rate_limit(f"track:{client_ip(request)}", 120, 60)
    aid = body.get("article_id")
    doc = {"type": "pageview", "path": str(body.get("path", ""))[:300], "session_id": str(body.get("session_id", ""))[:64],
           "visitor_id": str(body.get("visitor_id", ""))[:64], "device": "mobile" if body.get("mobile") else "desktop",
           "source": classify_source(body.get("referrer", ""), request.headers.get("host", "")), "day": iso()[:10], "created_at": iso()}
    if aid:
        a = await db.articles.find_one({"id": aid, "status": "published"}, {"category_id": 1, "author_ids": 1, "tags": 1})
        if a:
            doc.update(article_id=aid, category_id=a.get("category_id"), author_ids=a.get("author_ids", []), tags=a.get("tags", []))
            await db.articles.update_one({"id": aid}, {"$inc": {"views": 1}})
    await db.events.insert_one(doc)
    return {"ok": True}


@router.post("/public/consent")
async def consent(body: dict, request: Request):
    await db.consents.insert_one({"id": new_id(), "visitor_id": str(body.get("visitor_id", ""))[:64], "analytics": bool(body.get("analytics")),
                                  "marketing": bool(body.get("marketing")), "ip_hash": ip_hash(request), "created_at": iso()})
    return {"ok": True}


@router.post("/public/privacy-request")
async def privacy_request(body: dict, request: Request):
    rate_limit(f"priv:{client_ip(request)}", 3, 600)
    email = str(body.get("email", "")).strip().lower()
    if "@" not in email or body.get("type") not in ("access", "delete", "correction"):
        raise HTTPException(400, "Neispravan zahtjev")
    await db.privacy_requests.insert_one({"id": new_id(), "email": email, "type": body["type"], "message": strip_tags(str(body.get("message", "")))[:2000],
                                          "status": "new", "created_at": iso()})
    return {"ok": True}


# ---------- Media files ----------
@router.get("/media/file/{path:path}")
async def media_file(path: str):
    if not path.startswith(f"{APP_NAME}/media/") or ".." in path:
        raise HTTPException(404, "Nije pronađeno")
    try:
        data, ct = await asyncio.to_thread(get_object, path)  # sync storage call must not block the event loop
    except Exception:
        raise HTTPException(404, "Nije pronađeno")
    return Response(data, media_type=ct, headers={"Cache-Control": "public, max-age=31536000, immutable"})


# ---------- SEO: sitemaps, RSS, robots, share ----------
def site_url(s, request):
    return (s.get("site_url") or f"https://{request.headers.get('host', '')}").rstrip("/")


@router.get("/sitemap.xml")
async def sitemap(request: Request):
    s = await get_settings()
    base = site_url(s, request)
    urls = [f"<url><loc>{base}/</loc><changefreq>hourly</changefreq></url>"]
    for c in await db.categories.find({"visible": True}, {"slug": 1}).to_list(500):
        urls.append(f"<url><loc>{base}/kategorija/{c['slug']}</loc></url>")
    for p in await db.pages.find({"published": True}, {"slug": 1}).to_list(100):
        urls.append(f"<url><loc>{base}/stranica/{p['slug']}</loc></url>")
    async for a in db.articles.find(public_filter(), {"slug": 1, "updated_at": 1, "published_at": 1}).sort("published_at", -1).limit(5000):
        urls.append(f"<url><loc>{base}/vijesti/{a['slug']}</loc><lastmod>{(a.get('updated_at') or a.get('published_at'))[:10]}</lastmod></url>")
    xml = '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(urls) + "</urlset>"
    return Response(xml, media_type="application/xml")


@router.get("/news-sitemap.xml")
async def news_sitemap(request: Request):
    s = await get_settings()
    base, name = site_url(s, request), escape(s.get("publisher_name") or s.get("site_name", ""))
    items = []
    async for a in db.articles.find(public_filter({"published_at": {"$gte": iso(now() - timedelta(days=2))}}), {"slug": 1, "title": 1, "published_at": 1}).limit(1000):
        items.append(f"<url><loc>{base}/vijesti/{a['slug']}</loc><news:news><news:publication><news:name>{name}</news:name>"
                     f"<news:language>bs</news:language></news:publication><news:publication_date>{a['published_at']}</news:publication_date>"
                     f"<news:title>{escape(a['title'])}</news:title></news:news></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">' + "".join(items) + "</urlset>")
    return Response(xml, media_type="application/xml")


@router.get("/rss.xml")
async def rss(request: Request, category: str = None):
    s = await get_settings()
    base = site_url(s, request)
    data = await query_articles(category=category, limit=30)
    items = "".join(f"<item><title>{escape(a['title'])}</title><link>{base}/vijesti/{a['slug']}</link><guid>{base}/vijesti/{a['slug']}</guid>"
                    f"<pubDate>{a['published_at']}</pubDate><description>{escape(a.get('summary') or '')}</description></item>" for a in data["items"])
    xml = (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{escape(s.get("site_name", ""))}</title>'
           f'<link>{base}</link><description>{escape(s.get("tagline", ""))}</description><language>bs</language>{items}</channel></rss>')
    return Response(xml, media_type="application/rss+xml")


@router.get("/robots.txt")
async def robots(request: Request):
    base = site_url(await get_settings(), request)
    txt = f"User-agent: *\nDisallow: /admin\nDisallow: /api/admin\nDisallow: /api/auth\n\nSitemap: {base}/api/sitemap.xml\nSitemap: {base}/api/news-sitemap.xml\n"
    return Response(txt, media_type="text/plain")


@router.get("/share/{slug}", response_class=HTMLResponse)
async def share(slug: str, request: Request):
    """Server-rendered meta page for social crawlers (Facebook, X, Viber), redirects humans to the article."""
    s = await get_settings()
    base = site_url(s, request)
    a = await db.articles.find_one(public_filter({"slug": slug}), {"_id": 0})
    if not a:
        raise HTTPException(404, "Nije pronađeno")
    img = a.get("social_image") or (a.get("featured_image") or {}).get("large") or s.get("social_image") or "/icon-512.png"
    img = img if img.startswith("http") else base + img
    url = f"{base}/vijesti/{slug}"
    t, d = escape(a.get("seo_title") or a["title"]), escape(a.get("seo_description") or a.get("summary") or "")
    html = (f'<!doctype html><html lang="bs"><head><meta charset="utf-8"><title>{t}</title><meta name="description" content="{d}">'
            f'<link rel="canonical" href="{escape(a.get("canonical_url") or url)}"><meta property="og:type" content="article">'
            f'<meta property="og:title" content="{t}"><meta property="og:description" content="{d}"><meta property="og:image" content="{escape(img)}">'
            f'<meta property="og:url" content="{url}"><meta property="og:site_name" content="{escape(s.get("site_name", ""))}">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{t}">'
            f'<meta name="twitter:description" content="{d}"><meta name="twitter:image" content="{escape(img)}">'
            f'<meta http-equiv="refresh" content="0;url={url}"></head><body><a href="{url}">{t}</a></body></html>')
    return HTMLResponse(html)
