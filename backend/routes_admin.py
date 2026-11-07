import json
import re
import asyncio
from datetime import timedelta

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Body
from fastapi.responses import Response

from core import (db, new_id, iso, now, slugify, sanitize_html, strip_tags, require, audit, client_ip, PERMISSIONS,
                  get_current_user, hash_pw, get_settings, fold)
from routes_auth import check_pw_policy
from services import process_image, ai_generate
from newsletter import build_campaign, start_send, resolve_base, render_email
from services import send_email

router = APIRouter(prefix="/api/admin")
COERCE = {"str": lambda v: str(v or "").strip(), "int": lambda v: int(v or 0), "bool": bool, "list": lambda v: list(v or []),
          "html": lambda v: sanitize_html(str(v or "")), "any": lambda v: v}


def crud(path, coll, perm, fields, sort=("order", 1), hook=None, log=True):
    def build(body, existing=None):
        doc = {k: COERCE[t](body.get(k)) for k, t in fields.items() if k in body}
        return doc

    @router.get(f"/{path}", name=f"list_{path}")
    async def _list(user=Depends(require(perm))):
        return await db[coll].find({"deleted": {"$ne": True}}, {"_id": 0}).sort(*sort).to_list(1000)

    @router.post(f"/{path}", name=f"create_{path}")
    async def _create(body: dict = Body(...), user=Depends(require(perm))):
        doc = build(body)
        doc.update(id=new_id(), created_at=iso(), created_by=user["name"])
        if hook:
            doc = await hook(doc, user, None)
        await db[coll].insert_one(doc)
        if log:
            await audit(user, f"{path}.create", path, doc["id"], str(doc.get("name") or doc.get("title") or ""))
        doc.pop("_id", None)
        return doc

    @router.put(f"/{path}/{{item_id}}", name=f"update_{path}")
    async def _update(item_id: str, body: dict = Body(...), user=Depends(require(perm))):
        ex = await db[coll].find_one({"id": item_id}, {"_id": 0})
        if not ex:
            raise HTTPException(404, "Nije pronađeno")
        doc = build(body, ex)
        doc["updated_at"] = iso()
        if hook:
            doc = await hook(doc, user, ex)
        await db[coll].update_one({"id": item_id}, {"$set": doc})
        if log:
            await audit(user, f"{path}.update", path, item_id, str(doc.get("name") or doc.get("title") or ex.get("name") or ex.get("title") or ""))
        return {**ex, **doc}

    @router.delete(f"/{path}/{{item_id}}", name=f"delete_{path}")
    async def _delete(item_id: str, user=Depends(require(perm))):
        r = await db[coll].delete_one({"id": item_id})
        if not r.deleted_count:
            raise HTTPException(404, "Nije pronađeno")
        await audit(user, f"{path}.delete", path, item_id)
        return {"ok": True}


async def cat_hook(doc, user, ex):
    doc["slug"] = slugify(doc.get("slug") or doc.get("name", ""))
    if await db.categories.find_one({"slug": doc["slug"], "id": {"$ne": (ex or doc)["id"]}}):
        raise HTTPException(400, "Slug već postoji")
    return doc


async def tag_hook(doc, user, ex):
    doc["slug"] = slugify(doc.get("name", ""))
    return doc


async def ad_hook(doc, user, ex):
    if doc.get("type") in ("html", "adsense") and "settings.manage" not in user["permissions"]:
        raise HTTPException(403, "Samo Super Admin može unositi vanjski reklamni kod")
    if "settings.manage" not in user["permissions"]:
        doc.pop("html_code", None)
    if doc.get("target_url") and not doc["target_url"].startswith(("http://", "https://")):
        raise HTTPException(400, "Odredišni URL mora počinjati sa http(s)://")
    if not ex:
        doc.update(impressions=0, clicks=0)
    return doc


async def page_hook(doc, user, ex):
    doc["slug"] = slugify(doc.get("slug") or doc.get("title", ""))
    return doc


async def cam_hook(doc, user, ex):
    for k in ("image_url", "page_url"):
        if doc.get(k) and not doc[k].startswith(("http://", "https://")):
            raise HTTPException(400, "URL mora počinjati sa http(s)://")
    return doc


crud("categories", "categories", "categories.manage", {"name": "str", "slug": "str", "description": "str", "parent_id": "any", "seo_title": "str",
     "seo_description": "str", "image": "str", "color": "str", "visible": "bool", "show_in_menu": "bool", "order": "int"}, hook=cat_hook)
crud("tags", "tags", "categories.manage", {"name": "str", "description": "str"}, sort=("name", 1), hook=tag_hook)
crud("breaking", "breaking_news", "breaking.manage", {"title": "str", "article_id": "any", "url": "str", "priority": "int", "active": "bool",
     "start_at": "str", "end_at": "str"}, sort=("created_at", -1))
crud("advertisers", "advertisers", "ads.manage", {"name": "str", "contact": "str", "email": "str", "phone": "str", "notes": "str"}, sort=("name", 1))
crud("campaigns", "ad_campaigns", "ads.manage", {"name": "str", "advertiser_id": "any", "position": "str", "type": "str", "image_url": "str",
     "mobile_image_url": "str", "alt": "str", "target_url": "str", "html_code": "any", "start_at": "str", "end_at": "str", "active": "bool",
     "max_impressions": "int", "weight": "int", "sponsored_label": "str"}, sort=("created_at", -1), hook=ad_hook)
crud("pages", "pages", "pages.manage", {"title": "str", "slug": "str", "content": "html", "seo_title": "str", "seo_description": "str",
     "published": "bool"}, sort=("title", 1), hook=page_hook)
crud("redirects", "redirects", "settings.manage", {"from_path": "str", "to_path": "str", "code": "int"}, sort=("created_at", -1))
crud("cameras", "cameras", "cameras.manage", {"name": "str", "location": "str", "image_url": "str", "page_url": "str", "refresh_seconds": "int",
     "order": "int", "active": "bool", "description": "str", "group": "str"}, hook=cam_hook)


# ---------- Dashboard & analytics ----------
async def traffic(days: int):
    since = iso(now() - timedelta(days=days))[:10]
    m = {"type": "pageview", "day": {"$gte": since}}
    per_day = [{"day": r["_id"], "pageviews": r["pv"], "sessions": len(r["s"]), "users": len(r["u"])} async for r in db.events.aggregate([
        {"$match": m}, {"$group": {"_id": "$day", "pv": {"$sum": 1}, "s": {"$addToSet": "$session_id"}, "u": {"$addToSet": "$visitor_id"}}}, {"$sort": {"_id": 1}}])]
    tot = [r async for r in db.events.aggregate([{"$match": m}, {"$group": {"_id": None, "pv": {"$sum": 1}, "s": {"$addToSet": "$session_id"}, "u": {"$addToSet": "$visitor_id"}}}])]
    t = tot[0] if tot else {"pv": 0, "s": [], "u": []}
    return m, per_day, {"pageviews": t["pv"], "sessions": len(t["s"]), "users": len(t["u"])}


async def group_by(m, field, limit=10):
    pipe = [{"$match": m}]
    if field in ("author_ids", "tags"):
        pipe.append({"$unwind": f"${field}"})
    pipe += [{"$group": {"_id": f"${field}", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": limit}]
    return [{"key": r["_id"], "count": r["count"]} async for r in db.events.aggregate(pipe) if r["_id"]]


@router.get("/dashboard")
async def dashboard(days: int = 7, user=Depends(get_current_user)):
    today = iso()[:10]
    base = {"deleted": {"$ne": True}}
    c = lambda extra: db.articles.count_documents({**base, **extra})
    _, per_day, totals = await traffic(days)
    top = await db.articles.find({**base, "status": "published"}, {"_id": 0, "id": 1, "title": 1, "views": 1, "slug": 1}).sort("views", -1).limit(8).to_list(8)
    privileged = await db.users.count_documents({"role": {"$in": ["super_admin", "chief_editor", "editor"]}, "active": True, "totp_enabled": {"$ne": True}})
    warnings = []
    if privileged:
        warnings.append(f"{privileged} administrator(a)/urednik(a) nema uključenu dvofaktorsku autentifikaciju.")
    pc = await db.comments.count_documents({"status": "pending"})
    if pc:
        warnings.append(f"{pc} komentar(a) čeka moderaciju.")
    ns = await db.submissions.count_documents({"status": "new"})
    if ns:
        warnings.append(f"{ns} novih prijavljenih vijesti čeka provjeru.")
    return {
        "published": await c({"status": "published"}), "published_today": await c({"status": "published", "published_at": {"$gte": today}}),
        "drafts": await c({"status": "draft"}), "review": await c({"status": "review"}), "scheduled": await c({"status": "scheduled"}),
        "rejected": await c({"status": "rejected"}),
        "active_journalists": await db.users.count_documents({"active": True, "role": {"$in": ["journalist", "author", "editor", "chief_editor"]}}),
        "active_campaigns": await db.ad_campaigns.find({"active": True}, {"_id": 0, "name": 1, "position": 1, "impressions": 1, "clicks": 1}).to_list(20),
        "top_articles": top, "traffic": per_day, "totals": totals,
        "recent_activity": await db.audit_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(12).to_list(12), "warnings": warnings,
    }


@router.get("/analytics")
async def analytics(days: int = 30, user=Depends(require("analytics.view"))):
    m, per_day, totals = await traffic(days)
    cats = {c["id"]: c["name"] for c in await db.categories.find({}, {"id": 1, "name": 1}).to_list(500)}
    users = {u["id"]: u["name"] for u in await db.users.find({}, {"id": 1, "name": 1}).to_list(500)}
    titles = {}
    top_art = await group_by({**m, "article_id": {"$exists": True}}, "article_id", 10)
    for a in await db.articles.find({"id": {"$in": [x["key"] for x in top_art]}}, {"id": 1, "title": 1}).to_list(10):
        titles[a["id"]] = a["title"]
    since = iso(now() - timedelta(days=days))[:10]
    ads = [r async for r in db.ad_events.aggregate([{"$match": {"day": {"$gte": since}}}, {"$group": {"_id": {"c": "$campaign_id", "t": "$type"}, "n": {"$sum": 1}}}])]
    camp = {c["id"]: c for c in await db.ad_campaigns.find({}, {"_id": 0, "id": 1, "name": 1, "position": 1}).to_list(500)}
    perf = {}
    for r in ads:
        cid = r["_id"]["c"]
        p = perf.setdefault(cid, {"name": camp.get(cid, {}).get("name", cid), "position": camp.get(cid, {}).get("position"), "impression": 0, "click": 0})
        p[r["_id"]["t"]] = r["n"]
    return {
        "totals": totals, "per_day": per_day,
        "by_category": [{"name": cats.get(x["key"], "?"), "count": x["count"]} for x in await group_by(m, "category_id")],
        "by_author": [{"name": users.get(x["key"], "?"), "count": x["count"]} for x in await group_by(m, "author_ids")],
        "sources": [{"name": x["key"], "count": x["count"]} for x in await group_by(m, "source")],
        "devices": [{"name": x["key"], "count": x["count"]} for x in await group_by(m, "device")],
        "top_articles": [{"title": titles.get(x["key"], "?"), "count": x["count"]} for x in top_art],
        "top_tags": [{"name": x["key"], "count": x["count"]} for x in await group_by(m, "tags")],
        "ads": [{**v, "ctr": round(100 * v["click"] / v["impression"], 2) if v["impression"] else 0} for v in perf.values()],
    }


# ---------- Media ----------
@router.get("/media")
async def media_list(q: str = "", category: str = "", page: int = 1, user=Depends(require("media.manage", "articles.create"))):
    f = {"deleted": {"$ne": True}}
    if q:
        f["search"] = {"$regex": re.escape(fold(q))}
    if category:
        f["category"] = category
    total = await db.media.count_documents(f)
    items = await db.media.find(f, {"_id": 0}).sort("created_at", -1).skip((page - 1) * 40).limit(40).to_list(40)
    return {"items": items, "total": total}


def media_search(d):
    return fold(" ".join(str(d.get(k, "")) for k in ("filename", "alt", "caption", "credit", "source", "category")))


@router.post("/media")
async def media_upload(files: list[UploadFile] = File(...), user=Depends(require("media.manage", "articles.create"))):
    out = []
    for f in files[:20]:
        raw = await f.read()
        try:
            mid, variants, w, h = await asyncio.to_thread(process_image, raw)
        except ValueError as e:
            raise HTTPException(400, f"{f.filename}: {e}")
        doc = {"id": mid, "filename": (f.filename or "")[:150], **variants, "width": w, "height": h, "alt": "", "caption": "", "credit": "",
               "source": "", "category": "", "size": len(raw), "uploaded_by": user["name"], "uploaded_by_id": user["id"], "created_at": iso(), "deleted": False}
        doc["search"] = media_search(doc)
        await db.media.insert_one(doc)
        doc.pop("_id", None)
        out.append(doc)
    await audit(user, "media.upload", "media", ",".join(d["id"] for d in out), f"{len(out)} datoteka")
    return out


@router.put("/media/{mid}")
async def media_update(mid: str, body: dict, user=Depends(require("media.manage", "articles.create"))):
    upd = {k: str(body.get(k, ""))[:500] for k in ("alt", "caption", "credit", "source", "category") if k in body}
    ex = await db.media.find_one({"id": mid}, {"_id": 0})
    if not ex:
        raise HTTPException(404, "Nije pronađeno")
    ex.update(upd)
    upd["search"] = media_search(ex)
    await db.media.update_one({"id": mid}, {"$set": upd})
    return ex


async def media_usage(mid):
    f = {"deleted": {"$ne": True}, "$or": [{"featured_image.id": mid}, {"gallery.id": mid}, {"body": {"$regex": re.escape(mid)}}]}
    return await db.articles.find(f, {"_id": 0, "id": 1, "title": 1, "status": 1}).to_list(100)


@router.get("/media/{mid}/usage")
async def usage(mid: str, user=Depends(require("media.manage", "articles.create"))):
    return await media_usage(mid)


@router.post("/media/{mid}/crop")
async def crop(mid: str, body: dict, user=Depends(require("media.manage"))):
    from services import get_object
    ex = await db.media.find_one({"id": mid}, {"_id": 0})
    if not ex:
        raise HTTPException(404, "Nije pronađeno")
    raw, _ = await asyncio.to_thread(get_object, ex["large"].replace("/api/media/file/", ""))
    scale = min(1600, ex["width"]) / ex["width"]
    c = {k: float(body[k]) * scale for k in ("x", "y", "w", "h")}
    nid, variants, w, h = await asyncio.to_thread(process_image, raw, c)
    doc = {**ex, "id": nid, **variants, "width": w, "height": h, "filename": f"crop-{ex['filename']}", "created_at": iso(), "uploaded_by": user["name"]}
    await db.media.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.delete("/media/{mid}")
async def media_delete(mid: str, force: bool = False, user=Depends(require("media.manage"))):
    used = await media_usage(mid)
    if used and not force:
        raise HTTPException(409, f"Fotografija se koristi u {len(used)} članak(a): " + "; ".join(u["title"] for u in used[:3]))
    await db.media.update_one({"id": mid}, {"$set": {"deleted": True}})
    await audit(user, "media.delete", "media", mid)
    return {"ok": True}


# ---------- Home page builder ----------
@router.get("/homepage")
async def get_home(user=Depends(require("homepage.manage"))):
    d = await db.settings.find_one({"key": "homepage"}, {"_id": 0})
    return (d or {}).get("value", {"draft": [], "published": []})


@router.put("/homepage")
async def save_home(body: dict, user=Depends(require("homepage.manage"))):
    blocks = [{k: b.get(k) for k in ("id", "type", "title", "category_slug", "article_ids", "limit", "visible", "order", "ad_position", "dedupe", "style")}
              for b in body.get("blocks", [])][:40]
    for i, b in enumerate(blocks):
        b["order"], b["id"] = i, b.get("id") or new_id()
    await db.settings.update_one({"key": "homepage"}, {"$set": {"value.draft": blocks, "value.draft_updated": iso()}}, upsert=True)
    return {"ok": True}


@router.post("/homepage/publish")
async def publish_home(user=Depends(require("homepage.manage"))):
    d = await db.settings.find_one({"key": "homepage"}, {"_id": 0})
    await db.settings.update_one({"key": "homepage"}, {"$set": {"value.published": d["value"].get("draft", []), "value.published_at": iso()}})
    await audit(user, "homepage.publish", "homepage")
    return {"ok": True}


# ---------- Comments ----------
@router.get("/comments")
async def comments(status: str = "pending", user=Depends(require("comments.moderate"))):
    f = {"reports": {"$gt": 0}} if status == "reported" else {"status": status}
    items = await db.comments.find(f, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    titles = {a["id"]: a["title"] for a in await db.articles.find({"id": {"$in": list({c["article_id"] for c in items})}}, {"id": 1, "title": 1}).to_list(200)}
    for c in items:
        c["article_title"] = titles.get(c["article_id"], "")
    return items


@router.post("/comments/{cid}/moderate")
async def moderate(cid: str, body: dict, user=Depends(require("comments.moderate"))):
    action = body.get("action")
    c = await db.comments.find_one({"id": cid}, {"_id": 0})
    if not c:
        raise HTTPException(404, "Nije pronađeno")
    if action in ("approved", "rejected", "spam"):
        await db.comments.update_one({"id": cid}, {"$set": {"status": action, "reports": 0, "moderated_by": user["name"], "moderated_at": iso()}})
    elif action == "block":
        await db.blocked_users.insert_one({"id": new_id(), "ip_hash": c["ip_hash"], "email": c.get("email") or "-", "name": c["name"],
                                           "reason": body.get("reason", ""), "blocked_by": user["name"], "created_at": iso()})
        await db.comments.update_one({"id": cid}, {"$set": {"status": "rejected"}})
    elif action == "delete":
        await db.comments.delete_one({"id": cid})
    else:
        raise HTTPException(400, "Nepoznata akcija")
    await audit(user, f"comment.{action}", "comment", cid, c["content"][:100])
    return {"ok": True}


@router.get("/blocked")
async def blocked(user=Depends(require("comments.moderate"))):
    return await db.blocked_users.find({}, {"_id": 0, "ip_hash": 0}).sort("created_at", -1).to_list(500)


@router.delete("/blocked/{bid}")
async def unblock(bid: str, user=Depends(require("comments.moderate"))):
    await db.blocked_users.delete_one({"id": bid})
    await audit(user, "comment.unblock", "blocked", bid)
    return {"ok": True}


# ---------- Submissions ----------
@router.get("/submissions")
async def submissions(user=Depends(require("submissions.manage"))):
    return await db.submissions.find({}, {"_id": 0, "ip_hash": 0}).sort("created_at", -1).to_list(300)


@router.post("/submissions/{sid}/status")
async def submission_status(sid: str, body: dict, user=Depends(require("submissions.manage"))):
    st = body.get("status")
    if st not in ("new", "checking", "used", "rejected"):
        raise HTTPException(400, "Neispravan status")
    await db.submissions.update_one({"id": sid}, {"$set": {"status": st, "note": str(body.get("note", ""))[:1000], "handled_by": user["name"]}})
    await audit(user, f"submission.{st}", "submission", sid)
    return {"ok": True}


@router.post("/submissions/{sid}/to-draft")
async def submission_to_draft(sid: str, user=Depends(require("articles.create"))):
    s = await db.submissions.find_one({"id": sid}, {"_id": 0})
    if not s:
        raise HTTPException(404, "Nije pronađeno")
    aid = new_id()
    paragraphs = "".join(f"<p>{p}</p>" for p in s["description"].split("\n") if p.strip())
    gallery = [{"id": p["id"], "large": p["large"], "medium": p["medium"], "thumb": p["thumb"], "alt": "", "credit": f"Čitalac: {s['name']}"} for p in s["photos"]]
    await db.articles.insert_one({"id": aid, "title": s["title"], "subtitle": "", "summary": "", "body": paragraphs, "slug": slugify(s["title"]) + "-" + aid[:4],
                                  "status": "draft", "category_id": None, "category_ids": [], "tags": [], "tags_folded": [], "author_ids": [user["id"]],
                                  "source": f"Prijava čitaoca ({s['name']})", "source_author": s["name"], "featured_image": gallery[0] if gallery else None,
                                  "gallery": gallery, "video_urls": [], "created_by": user["id"], "created_at": iso(), "updated_at": iso(), "views": 0,
                                  "deleted": False, "was_published": False, "search_text": fold(s["title"] + " " + s["description"]), "allow_comments": True, "show_views": True})
    await db.submissions.update_one({"id": sid}, {"$set": {"status": "used", "article_id": aid}})
    await audit(user, "submission.to_draft", "article", aid, s["title"])
    return {"id": aid}


# ---------- Newsletter ----------
@router.get("/newsletter/subscribers")
async def subscribers(user=Depends(require("newsletter.manage"))):
    return await db.newsletter_subscribers.find({}, {"_id": 0, "token": 0}).sort("created_at", -1).to_list(5000)


@router.delete("/newsletter/subscribers/{sid}")
async def del_subscriber(sid: str, user=Depends(require("newsletter.manage"))):
    await db.newsletter_subscribers.delete_one({"id": sid})
    await audit(user, "newsletter.subscriber_delete", "subscriber", sid)
    return {"ok": True}


@router.get("/newsletter/campaigns")
async def campaigns(user=Depends(require("newsletter.manage"))):
    return await db.newsletter_campaigns.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/newsletter/campaigns")
async def create_campaign(body: dict, user=Depends(require("newsletter.manage"))):
    doc = await build_campaign(body.get("kind", "manual"), body.get("article_ids"), body.get("count"), body.get("subject"), body.get("intro"), user["name"])
    await db.newsletter_campaigns.insert_one(doc)
    doc.pop("_id", None)
    await audit(user, "newsletter.campaign_create", "campaign", doc["id"], doc["subject"])
    return doc


@router.post("/newsletter/campaigns/{cid}/send")
async def send_camp(cid: str, request: Request, user=Depends(require("newsletter.manage"))):
    camp = await db.newsletter_campaigns.find_one({"id": cid}, {"_id": 0, "subject": 1, "article_ids": 1})
    if not camp:
        raise HTTPException(404, "Kampanja ne postoji")
    if not camp["article_ids"]:
        raise HTTPException(400, "Kampanja nema vijesti")
    if not await db.newsletter_subscribers.count_documents({"status": "confirmed"}):
        raise HTTPException(400, "Nema potvrđenih pretplatnika")
    if not await start_send(cid, await resolve_base(request)):
        raise HTTPException(409, "Kampanja je već poslana ili se šalje")
    await audit(user, "newsletter.campaign_send", "campaign", cid, camp["subject"])
    return {"ok": True}


@router.put("/newsletter/campaigns/{cid}")
async def edit_camp(cid: str, body: dict, user=Depends(require("newsletter.manage"))):
    upd = {"subject": str(body.get("subject") or "").strip()[:200], "intro": strip_tags(str(body.get("intro") or ""))[:2000]}
    if not upd["subject"]:
        raise HTTPException(400, "Naslov je obavezan")
    r = await db.newsletter_campaigns.update_one({"id": cid, "status": {"$in": ["draft", "failed"]}}, {"$set": upd})
    if not r.matched_count:
        raise HTTPException(409, "Poslana kampanja se ne može mijenjati")
    return {"ok": True}


@router.get("/newsletter/campaigns/{cid}/preview")
async def preview_camp(cid: str, request: Request, user=Depends(require("newsletter.manage"))):
    camp = await db.newsletter_campaigns.find_one({"id": cid}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "Kampanja ne postoji")
    return {"html": await render_email(camp, await resolve_base(request), "pregled")}


@router.post("/newsletter/campaigns/{cid}/test")
async def test_camp(cid: str, request: Request, user=Depends(require("newsletter.manage"))):
    camp = await db.newsletter_campaigns.find_one({"id": cid}, {"_id": 0})
    if not camp:
        raise HTTPException(404, "Kampanja ne postoji")
    html = await render_email(camp, await resolve_base(request), "proba")
    if not await send_email(to=user["email"], subject=f"[PROBA] {camp['subject']}", html=html):
        raise HTTPException(502, "Slanje probnog e-maila nije uspjelo")
    return {"ok": True, "email": user["email"]}


@router.delete("/newsletter/campaigns/{cid}")
async def del_campaign(cid: str, user=Depends(require("newsletter.manage"))):
    await db.newsletter_campaigns.delete_one({"id": cid})
    return {"ok": True}


# ---------- Users & roles ----------
USER_FIELDS = {"_id": 0, "password_hash": 0, "totp_secret": 0, "totp_pending": 0}


@router.get("/users")
async def users(user=Depends(require("users.manage"))):
    return await db.users.find({"deleted": {"$ne": True}}, USER_FIELDS).sort("created_at", 1).to_list(500)


@router.get("/users/directory")
async def directory(user=Depends(get_current_user)):
    return await db.users.find({"deleted": {"$ne": True}, "active": True}, {"_id": 0, "id": 1, "name": 1, "role": 1}).to_list(500)


async def validate_user_payload(body, ex=None):
    roles = [r["key"] async for r in db.roles.find({}, {"key": 1})]
    out = {}
    for k in ("name", "bio", "avatar"):
        if k in body:
            out[k] = str(body[k] or "").strip()[:500]
    if "role" in body:
        if body["role"] not in roles:
            raise HTTPException(400, "Nepoznata uloga")
        out["role"] = body["role"]
    for k in ("extra_permissions", "assigned_categories"):
        if k in body:
            out[k] = [p for p in body[k] if k != "extra_permissions" or p in PERMISSIONS]
    for k in ("active", "show_public"):
        if k in body:
            out[k] = bool(body[k])
    if out.get("name"):
        out["slug"] = slugify(out["name"])
    return out


@router.post("/users")
async def create_user(body: dict, request: Request, user=Depends(require("users.manage"))):
    email = str(body.get("email", "")).strip().lower()
    if "@" not in email or not body.get("name"):
        raise HTTPException(400, "Unesite ime i ispravan e-mail")
    if await db.users.find_one({"email": email, "deleted": {"$ne": True}}):
        raise HTTPException(400, "Korisnik s tim e-mailom već postoji")
    check_pw_policy(str(body.get("password", "")))
    doc = await validate_user_payload({"role": "journalist", "active": True, **body})
    doc.update(id=new_id(), email=email, password_hash=hash_pw(body["password"]), created_at=iso(), totp_enabled=False, deleted=False)
    await db.users.insert_one(doc)
    await audit(user, "user.create", "user", doc["id"], f"{email} ({doc['role']})", client_ip(request))
    return {k: v for k, v in doc.items() if k not in ("_id", "password_hash")}


@router.put("/users/{uid}")
async def update_user(uid: str, body: dict, user=Depends(require("users.manage"))):
    ex = await db.users.find_one({"id": uid}, USER_FIELDS)
    if not ex:
        raise HTTPException(404, "Nije pronađeno")
    upd = await validate_user_payload(body, ex)
    if uid == user["id"] and (upd.get("role", ex["role"]) != ex["role"] or upd.get("active") is False):
        raise HTTPException(400, "Ne možete promijeniti vlastitu ulogu ili deaktivirati sebe")
    if body.get("password"):
        check_pw_policy(body["password"])
        upd["password_hash"] = hash_pw(body["password"])
    await db.users.update_one({"id": uid}, {"$set": upd})
    if upd.get("active") is False or "password_hash" in upd:
        await db.sessions.update_many({"user_id": uid}, {"$set": {"revoked": True}})
    await audit(user, "user.update", "user", uid, ", ".join(k for k in upd if k != "password_hash") + (" +lozinka" if "password_hash" in upd else ""))
    return {"ok": True}


@router.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(require("users.manage"))):
    if uid == user["id"]:
        raise HTTPException(400, "Ne možete obrisati sebe")
    await db.users.update_one({"id": uid}, {"$set": {"deleted": True, "active": False}})
    u = await db.users.find_one({"id": uid}, {"email": 1})
    if u:
        await db.users.update_one({"id": uid}, {"$set": {"email": f"deleted-{uid[:8]}-{u['email']}"}})
    await db.sessions.update_many({"user_id": uid}, {"$set": {"revoked": True}})
    await audit(user, "user.delete", "user", uid)
    return {"ok": True}


@router.get("/roles")
async def roles(user=Depends(get_current_user)):
    return {"roles": await db.roles.find({}, {"_id": 0}).to_list(50), "permissions": PERMISSIONS}


@router.put("/roles/{key}")
async def update_role(key: str, body: dict, user=Depends(require("users.manage"))):
    if key == "super_admin":
        raise HTTPException(400, "Uloga Super Admin uvijek ima sve dozvole")
    perms = [p for p in body.get("permissions", []) if p in PERMISSIONS]
    await db.roles.update_one({"key": key}, {"$set": {"permissions": perms, **({"name": body["name"]} if body.get("name") else {})}}, upsert=True)
    await audit(user, "role.update", "role", key, ", ".join(perms))
    return {"ok": True}


# ---------- Settings, audit, backup, privacy ----------
SECRET_KEYS = {"ai_api_key"}


@router.get("/settings")
async def settings_get(user=Depends(require("settings.manage"))):
    return await get_settings()


@router.put("/settings")
async def settings_put(body: dict, user=Depends(require("settings.manage"))):
    cur = await get_settings()
    cur.update({k: v for k, v in body.items() if k not in SECRET_KEYS})
    if "footer_text" in cur:
        cur["footer_text"] = strip_tags(str(cur["footer_text"]))
    await db.settings.update_one({"key": "site"}, {"$set": {"value": cur}}, upsert=True)
    await audit(user, "settings.update", "settings", "", ", ".join(body.keys()))
    return cur


@router.get("/audit")
async def audit_list(q: str = "", page: int = 1, user=Depends(require("audit.view"))):
    f = {"$or": [{"action": {"$regex": re.escape(q)}}, {"user_name": {"$regex": re.escape(q), "$options": "i"}}, {"details": {"$regex": re.escape(q), "$options": "i"}}]} if q else {}
    total = await db.audit_logs.count_documents(f)
    return {"items": await db.audit_logs.find(f, {"_id": 0}).sort("created_at", -1).skip((page - 1) * 50).limit(50).to_list(50), "total": total}


@router.get("/privacy-requests")
async def privacy_list(user=Depends(require("settings.manage"))):
    return await db.privacy_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("/privacy-requests/{rid}")
async def privacy_update(rid: str, body: dict, user=Depends(require("settings.manage"))):
    await db.privacy_requests.update_one({"id": rid}, {"$set": {"status": str(body.get("status", "done")), "handled_by": user["name"]}})
    await audit(user, "privacy.update", "privacy", rid, str(body.get("status")))
    return {"ok": True}


BACKUP_COLLS = ["articles", "article_versions", "categories", "tags", "media", "pages", "breaking_news", "advertisers", "ad_campaigns",
                "comments", "blocked_users", "submissions", "newsletter_subscribers", "newsletter_campaigns", "settings", "roles", "users",
                "redirects", "cameras", "privacy_requests"]


@router.get("/backup")
async def backup(user=Depends(require("settings.manage"))):
    data = {c: await db[c].find({}, {"_id": 0}).to_list(None) for c in BACKUP_COLLS}
    data["_meta"] = {"created_at": iso(), "by": user["email"], "collections": BACKUP_COLLS}
    await audit(user, "system.backup", "system")
    return Response(json.dumps(data, default=str, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="ccn-backup-{iso()[:10]}.json"'})


@router.post("/restore")
async def restore(file: UploadFile = File(...), user=Depends(require("settings.manage"))):
    try:
        data = json.loads(await file.read())
        assert isinstance(data.get("_meta"), dict)
    except Exception:
        raise HTTPException(400, "Neispravna backup datoteka")
    restored = {}
    for c in BACKUP_COLLS:
        docs = data.get(c)
        if isinstance(docs, list) and docs:
            await db[c].delete_many({})
            await db[c].insert_many(docs)
            restored[c] = len(docs)
    await audit(user, "system.restore", "system", "", json.dumps(restored))
    return {"ok": True, "restored": restored}


# ---------- AI ----------
AI_PROMPTS = {
    "titles": "Predloži 5 novinarskih naslova (svaki u novom redu, bez numeracije) za sljedeći tekst:",
    "subtitle": "Predloži jedan podnaslov (do 25 riječi) za sljedeći tekst:",
    "summary": "Napiši kratki sažetak (2-3 rečenice) sljedećeg teksta:",
    "proofread": "Provjeri pravopis i gramatiku (bosanski standard). Navedi samo pronađene greške u formatu 'pogrešno → ispravno', svaku u novom redu. Ako nema grešaka napiši 'Nema grešaka.':",
    "tags": "Predloži 5-8 oznaka (tagova) odvojenih zarezom i jednu najprikladniju kategoriju u zadnjem redu u formatu 'Kategorija: X' za tekst:",
    "seo": "Napiši SEO meta opis (do 155 znakova) za sljedeći tekst:",
    "facebook": "Napiši nacrt objave za Facebook (do 60 riječi, bez izmišljanja, bez hashtag spama) za sljedeći tekst:",
    "newsletter": "Napiši kratki uvod za newsletter koji sažima sljedeće naslove vijesti (do 80 riječi):",
}


@router.post("/ai/{action}")
async def ai(action: str, body: dict, request: Request, user=Depends(require("ai.use"))):
    s = await get_settings()
    if not s.get("ai_enabled", True):
        raise HTTPException(403, "AI modul je isključen u postavkama")
    if action not in AI_PROMPTS:
        raise HTTPException(400, "Nepoznata AI funkcija")
    text = strip_tags(str(body.get("text", "")))[:12000]
    if len(text) < 30:
        raise HTTPException(400, "Tekst je prekratak za AI obradu")
    try:
        result = await ai_generate(f"{AI_PROMPTS[action]}\n\n---\n{text}\n---")
    except Exception as e:
        raise HTTPException(502, f"AI servis nije dostupan: {str(e)[:120]}")
    cost = round((len(text) / 4 * 3 + len(result) / 4 * 15) / 1_000_000, 5)
    await db.ai_usage_logs.insert_one({"id": new_id(), "user_id": user["id"], "user_name": user["name"], "action": action,
                                       "article_id": body.get("article_id"), "input_chars": len(text), "output_chars": len(result),
                                       "est_cost_usd": cost, "model": "claude-sonnet-5-5", "created_at": iso()})
    return {"result": result.strip(), "notice": "AI prijedlog – obavezno provjerite prije korištenja."}


@router.get("/ai/usage")
async def ai_usage(user=Depends(require("settings.manage"))):
    items = await db.ai_usage_logs.find({}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    total = sum(i.get("est_cost_usd", 0) for i in await db.ai_usage_logs.find({}, {"est_cost_usd": 1}).to_list(None))
    return {"items": items, "total_cost_usd": round(total, 4)}
