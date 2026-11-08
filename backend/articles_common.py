import re
import time
from datetime import timedelta

from fastapi import HTTPException

from core import db, iso, now, fold

CARD = {"_id": 0, "body": 0, "search_text": 0}
_last_publish = [0.0]


async def publish_due():
    """Lazy scheduler: publishes scheduled articles whose time has come."""
    if time.time() - _last_publish[0] < 15:
        return
    _last_publish[0] = time.time()
    due = await db.articles.find({"status": "scheduled", "publish_at": {"$lte": iso()}, "deleted": {"$ne": True}}, {"id": 1, "publish_at": 1}).to_list(200)
    for a in due:
        await db.articles.update_one({"id": a["id"]}, {"$set": {"status": "published", "published_at": a["publish_at"], "was_published": True}})
        await db.audit_logs.insert_one({"id": a["id"] + "-sched", "user_name": "Sistem", "action": "article.auto_published",
                                        "entity": "article", "entity_id": a["id"], "details": "", "created_at": iso()})


def public_filter(extra=None):
    q = {"status": "published", "deleted": {"$ne": True}}
    q.update(extra or {})
    return q


async def category_map():
    cats = await db.categories.find({}, {"_id": 0}).to_list(500)
    return {c["id"]: c for c in cats}


async def enrich(items, cats=None):
    cats = cats or await category_map()
    uids = {u for a in items for u in a.get("author_ids", [])}
    users = {u["id"]: u for u in await db.users.find({"id": {"$in": list(uids)}}, {"_id": 0, "id": 1, "name": 1, "slug": 1, "avatar": 1, "bio": 1}).to_list(200)}
    for a in items:
        c = cats.get(a.get("category_id"))
        a["category"] = {"id": c["id"], "name": c["name"], "slug": c["slug"], "color": c.get("color")} if c else None
        a["authors"] = [users[u] for u in a.get("author_ids", []) if u in users]
    return items


async def category_ids_with_children(slug):
    cat = await db.categories.find_one({"$or": [{"slug": slug}, {"old_slugs": slug}]}, {"_id": 0})
    if not cat:
        return None, []
    kids = await db.categories.find({"parent_id": cat["id"]}, {"_id": 0, "id": 1}).to_list(200)
    return cat, [cat["id"]] + [k["id"] for k in kids]


async def hidden_category_ids():
    return [c["id"] async for c in db.categories.find({"hide_from_home": True}, {"id": 1})]


async def query_articles(category=None, tag=None, author=None, q=None, date_from=None, date_to=None, sort="latest",
                         video=False, gallery=False, page=1, limit=12, exclude=None, hide=False):
    await publish_due()
    f = public_filter()
    if hide and not category:
        hidden = await hidden_category_ids()
        if hidden:
            f["category_id"] = {"$nin": hidden}
    if category:
        cat, ids = await category_ids_with_children(category)
        if not cat:
            raise HTTPException(404, "Kategorija ne postoji")
        f["$or"] = [{"category_id": {"$in": ids}}, {"category_ids": {"$in": ids}}]
    if tag:
        f["tags_folded"] = fold(tag)
    if author:
        u = await db.users.find_one({"slug": author}, {"id": 1})
        f["author_ids"] = u["id"] if u else "-"
    if q:
        terms = [re.escape(t) for t in fold(q).split() if t][:8]
        f["$and"] = [{"search_text": {"$regex": t}} for t in terms]
    if date_from or date_to:
        f["published_at"] = {k: v for k, v in (("$gte", date_from), ("$lte", date_to and date_to + "T23:59:59")) if v}
    if video:
        f["has_video"] = True
    if gallery:
        f["gallery.0"] = {"$exists": True}
    if exclude:
        f["id"] = {"$nin": exclude}
    if sort == "popular":
        f["published_at"] = {"$gte": iso(now() - timedelta(days=14))}
        order = [("views", -1)]
    else:
        order = [("is_pinned", -1), ("published_at", -1)] if sort == "pinned" else [("published_at", -1)]
    total = await db.articles.count_documents(f)
    items = await db.articles.find(f, CARD).sort(order).skip((page - 1) * limit).limit(limit).to_list(limit)
    if sort == "popular" and len(items) < limit:
        f.pop("published_at", None)
        f["id"] = {"$nin": [i["id"] for i in items] + (exclude or [])}
        items += await db.articles.find(f, CARD).sort([("views", -1)]).limit(limit - len(items)).to_list(limit)
    return {"items": await enrich(items), "total": total, "page": page}
