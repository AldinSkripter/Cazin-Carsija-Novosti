from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from core import db, new_id, iso, now, fold, slugify, sanitize_html, strip_tags, require, audit, client_ip

router = APIRouter(prefix="/api/admin/articles")
EDITABLE = ["title", "subtitle", "summary", "body", "slug", "category_id", "category_ids", "tags", "author_ids", "source",
            "source_author", "featured_image", "gallery", "video_urls", "seo_title", "seo_description", "canonical_url",
            "social_image", "publish_at", "is_breaking", "is_pinned", "is_exclusive", "is_sponsored", "allow_comments", "show_views"]
LIST_FIELDS = {"_id": 0, "body": 0, "search_text": 0, "gallery": 0}


class ArticleIn(BaseModel):
    model_config = {"extra": "ignore"}
    title: str = ""
    subtitle: str = ""
    summary: str = ""
    body: str = ""
    slug: str = ""
    category_id: str | None = None
    category_ids: list[str] = []
    tags: list[str] = []
    author_ids: list[str] = []
    source: str = ""
    source_author: str = ""
    featured_image: dict | None = None
    gallery: list[dict] = []
    video_urls: list[str] = []
    seo_title: str = ""
    seo_description: str = ""
    canonical_url: str = ""
    social_image: str = ""
    publish_at: str | None = None
    is_breaking: bool = False
    is_pinned: bool = False
    is_exclusive: bool = False
    is_sponsored: bool = False
    allow_comments: bool = True
    show_views: bool = True


class TransitionIn(BaseModel):
    action: str
    reason: str = ""
    publish_at: str | None = None


def can_edit(user, a):
    p = user["permissions"]
    if "articles.edit_all" in p:
        assigned = user.get("assigned_categories") or []
        if not assigned or a.get("category_id") in assigned:
            return True
    own = a.get("created_by") == user["id"] or user["id"] in a.get("author_ids", [])
    return "articles.edit_own" in p and own and (a["status"] in ("draft", "rejected", "review") or "articles.publish" in p)


async def get_editable(aid, user):
    a = await db.articles.find_one({"id": aid, "deleted": {"$ne": True}}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Članak nije pronađen")
    if not can_edit(user, a):
        raise HTTPException(403, "Nemate dozvolu za uređivanje ovog članka")
    return a


async def unique_slug(slug, aid):
    base, i = slug, 2
    while await db.articles.find_one({"slug": slug, "id": {"$ne": aid}}):
        slug, i = f"{base}-{i}", i + 1
    return slug


async def prepare(data: dict, aid: str, user):
    data["title"] = data["title"].strip()[:250]
    data["body"] = sanitize_html(data["body"])
    data["slug"] = await unique_slug(slugify(data.get("slug") or data["title"]), aid)
    data["tags"] = list(dict.fromkeys(t.strip() for t in data["tags"] if t.strip()))[:20]
    data["tags_folded"] = [fold(t) for t in data["tags"]]
    data["author_ids"] = data["author_ids"] or [user["id"]]
    data["video_urls"] = [v for v in data["video_urls"] if v.startswith("https://")]
    names = [u["name"] async for u in db.users.find({"id": {"$in": data["author_ids"]}}, {"name": 1})]
    data["search_text"] = fold(" ".join([data["title"], data["subtitle"], data["summary"], strip_tags(data["body"]), " ".join(data["tags"]), " ".join(names)]))
    data["has_video"] = bool(data["video_urls"]) or "youtube.com/embed" in data["body"]
    data["updated_at"] = iso()
    data["updated_by"] = user["id"]
    return data


async def save_version(a, user, note=""):
    n = await db.article_versions.count_documents({"article_id": a["id"]}) + 1
    await db.article_versions.insert_one({"id": new_id(), "article_id": a["id"], "version": n, "note": note, "user_id": user["id"],
                                          "user_name": user["name"], "status": a.get("status"), "created_at": iso(),
                                          "data": {k: a.get(k) for k in EDITABLE}})


async def sync_breaking(a, user):
    if a.get("is_breaking") and a["status"] == "published":
        await db.breaking_news.update_one({"article_id": a["id"]}, {"$set": {"title": a["title"], "active": True},
                                          "$setOnInsert": {"id": new_id(), "priority": 5, "created_by": user["name"], "created_at": iso()}}, upsert=True)


@router.get("")
async def list_articles(status: str = None, q: str = None, category_id: str = None, mine: bool = False, page: int = 1, limit: int = 25,
                        user=Depends(require("articles.create", "articles.edit_own", "articles.edit_all"))):
    f = {"deleted": {"$ne": True}}
    if status:
        f["status"] = status
    if category_id:
        f["category_id"] = category_id
    if q:
        f["search_text"] = {"$regex": fold(q).replace(".", r"\.")}
    if mine or "articles.edit_all" not in user["permissions"]:
        f["$or"] = [{"created_by": user["id"]}, {"author_ids": user["id"]}]
    total = await db.articles.count_documents(f)
    items = await db.articles.find(f, LIST_FIELDS).sort("updated_at", -1).skip((page - 1) * limit).limit(limit).to_list(limit)
    return {"items": items, "total": total}


@router.post("")
async def create(body: ArticleIn, request: Request, user=Depends(require("articles.create"))):
    aid = new_id()
    data = await prepare(body.model_dump(), aid, user)
    data.update(id=aid, status="draft", created_by=user["id"], created_at=iso(), views=0, deleted=False, was_published=False)
    await db.articles.insert_one(data)
    await save_version(data, user, "Kreirano")
    await audit(user, "article.create", "article", aid, data["title"], client_ip(request))
    data.pop("_id", None)
    return data


@router.get("/duplicates")
async def duplicates(title: str, exclude: str = "", user=Depends(require("articles.create"))):
    words = {w for w in fold(title).split() if len(w) > 3}
    if not words:
        return []
    out = []
    async for a in db.articles.find({"deleted": {"$ne": True}, "id": {"$ne": exclude}}, {"id": 1, "title": 1, "status": 1, "slug": 1, "_id": 0}).sort("created_at", -1).limit(800):
        w2 = {w for w in fold(a["title"]).split() if len(w) > 3}
        score = len(words & w2) / max(len(words | w2), 1)
        if score >= 0.4:
            out.append({**a, "score": round(score, 2)})
    return sorted(out, key=lambda x: -x["score"])[:5]


@router.get("/{aid}")
async def get_one(aid: str, user=Depends(require("articles.create", "articles.edit_own", "articles.edit_all"))):
    a = await db.articles.find_one({"id": aid, "deleted": {"$ne": True}}, {"_id": 0, "search_text": 0})
    if not a:
        raise HTTPException(404, "Članak nije pronađen")
    a["can_edit"] = can_edit(user, a)
    if not a["can_edit"] and "articles.edit_all" not in user["permissions"] and "articles.approve" not in user["permissions"] \
            and a.get("created_by") != user["id"]:
        raise HTTPException(403, "Nemate pristup")
    return a


@router.put("/{aid}")
async def update(aid: str, body: ArticleIn, request: Request, autosave: bool = False, user=Depends(require("articles.edit_own", "articles.edit_all"))):
    a = await get_editable(aid, user)
    data = await prepare(body.model_dump(), aid, user)
    if a.get("was_published") and data["slug"] != a["slug"]:
        await db.redirects.update_one({"from_path": f"/vijesti/{a['slug']}"}, {"$set": {"to_path": f"/vijesti/{data['slug']}", "code": 301},
                                      "$setOnInsert": {"id": new_id(), "created_at": iso()}}, upsert=True)
    if a["status"] == "scheduled" and data.get("publish_at"):
        data["publish_at"] = data["publish_at"]
    await db.articles.update_one({"id": aid}, {"$set": data})
    a.update(data)
    if not autosave:
        await save_version(a, user, "Ručno sačuvano")
        await audit(user, "article.update", "article", aid, a["title"], client_ip(request))
        await sync_breaking(a, user)
    a.pop("search_text", None)
    return a


@router.post("/{aid}/transition")
async def transition(aid: str, body: TransitionIn, request: Request, user=Depends(require("articles.create", "articles.approve", "articles.publish"))):
    a = await db.articles.find_one({"id": aid, "deleted": {"$ne": True}}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Članak nije pronađen")
    p, act, st = user["permissions"], body.action, a["status"]
    upd = {}
    if act == "submit":
        if not can_edit(user, a) or st not in ("draft", "rejected"):
            raise HTTPException(403, "Članak se ne može poslati na pregled")
        upd = {"status": "review", "submitted_at": iso(), "rejection_reason": ""}
    elif act in ("approve", "reject"):
        if "articles.approve" not in p:
            raise HTTPException(403, "Nemate dozvolu za odobravanje")
        if act == "reject" and not body.reason.strip():
            raise HTTPException(400, "Unesite obrazloženje odbijanja")
        if st not in ("review", "approved", "scheduled"):
            raise HTTPException(400, "Članak nije na pregledu")
        upd = {"status": "approved", "approved_by": user["id"]} if act == "approve" else {"status": "rejected", "rejection_reason": body.reason.strip()[:1000]}
    elif act in ("publish", "schedule"):
        if "articles.publish" not in p or not can_edit(user, a):
            raise HTTPException(403, "Nemate dozvolu za objavljivanje")
        if not a.get("title") or not a.get("category_id"):
            raise HTTPException(400, "Članak mora imati naslov i kategoriju")
        when = body.publish_at or a.get("publish_at")
        if act == "schedule" or (when and when > iso()):
            if not when or when <= iso():
                raise HTTPException(400, "Odaberite budući datum objave")
            upd = {"status": "scheduled", "publish_at": when}
        else:
            upd = {"status": "published", "published_at": a.get("published_at") or iso(), "was_published": True, "published_by": user["id"]}
    elif act in ("unpublish", "archive"):
        if "articles.publish" not in p or not can_edit(user, a):
            raise HTTPException(403, "Nemate dozvolu")
        upd = {"status": "draft" if act == "unpublish" else "archived"}
        await db.breaking_news.update_many({"article_id": aid}, {"$set": {"active": False}})
    else:
        raise HTTPException(400, "Nepoznata akcija")
    await db.articles.update_one({"id": aid}, {"$set": {**upd, "updated_at": iso()}})
    a.update(upd)
    await sync_breaking(a, user)
    await save_version(a, user, f"Status: {a['status']}")
    await audit(user, f"article.{act}", "article", aid, f"{a['title']} {body.reason}".strip(), client_ip(request))
    a.pop("search_text", None)
    return a


@router.post("/{aid}/duplicate")
async def duplicate(aid: str, user=Depends(require("articles.create"))):
    a = await db.articles.find_one({"id": aid}, {"_id": 0})
    if not a:
        raise HTTPException(404, "Članak nije pronađen")
    if not can_edit(user, a) and a.get("created_by") != user["id"] and "articles.edit_all" not in user["permissions"]:
        raise HTTPException(403, "Nemate pristup ovom članku")
    nid = new_id()
    data = {k: a.get(k) for k in EDITABLE}
    data.update(title=f"{a['title']} (kopija)", slug=await unique_slug(a["slug"] + "-kopija", nid), id=nid, status="draft",
                created_by=user["id"], author_ids=[user["id"]], created_at=iso(), updated_at=iso(), views=0, deleted=False,
                was_published=False, search_text=a.get("search_text", ""), tags_folded=a.get("tags_folded", []), has_video=a.get("has_video", False))
    await db.articles.insert_one(data)
    await audit(user, "article.duplicate", "article", nid, f"Kopija od {aid}")
    return {"id": nid}


@router.delete("/{aid}")
async def delete(aid: str, user=Depends(require("articles.delete"))):
    a = await db.articles.find_one({"id": aid}, {"title": 1, "was_published": 1})
    if not a:
        raise HTTPException(404, "Članak nije pronađen")
    await db.articles.update_one({"id": aid}, {"$set": {"deleted": True, "deleted_at": iso(), "status": "archived"}})
    await audit(user, "article.delete", "article", aid, a["title"])
    return {"ok": True}


@router.get("/{aid}/versions")
async def versions(aid: str, user=Depends(require("articles.edit_own", "articles.edit_all"))):
    a = await db.articles.find_one({"id": aid}, {"_id": 0, "created_by": 1, "author_ids": 1})
    if not a or ("articles.edit_all" not in user["permissions"] and user["id"] not in [a.get("created_by"), *a.get("author_ids", [])]):
        raise HTTPException(403, "Nemate pristup ovom članku")
    return await db.article_versions.find({"article_id": aid}, {"_id": 0, "data.body": 0}).sort("version", -1).to_list(200)


@router.post("/{aid}/versions/{vid}/restore")
async def restore(aid: str, vid: str, user=Depends(require("articles.edit_own", "articles.edit_all"))):
    a = await get_editable(aid, user)
    v = await db.article_versions.find_one({"id": vid, "article_id": aid}, {"_id": 0})
    if not v:
        raise HTTPException(404, "Verzija nije pronađena")
    data = await prepare(ArticleIn(**v["data"]).model_dump(), aid, user)
    data["slug"] = a["slug"]
    await db.articles.update_one({"id": aid}, {"$set": data})
    a.update(data)
    await save_version(a, user, f"Vraćena verzija {v['version']}")
    await audit(user, "article.restore_version", "article", aid, f"v{v['version']}")
    return {"ok": True}


@router.get("/{aid}/history")
async def history(aid: str, user=Depends(require("articles.edit_own", "articles.edit_all"))):
    return await db.audit_logs.find({"entity": "article", "entity_id": aid}, {"_id": 0}).sort("created_at", -1).to_list(200)
