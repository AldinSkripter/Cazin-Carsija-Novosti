import asyncio
import logging
from datetime import timedelta
from html import escape

from core import db, new_id, iso, now, strip_tags, get_settings
from services import send_email, email_template

logger = logging.getLogger(__name__)


def base_url(settings, request):
    return (settings.get("site_url") or f"https://{request.headers.get('host', '')}").rstrip("/")


async def build_campaign(kind="manual", ids=None, count=8, subject="", intro="", created_by="Sistem"):
    days = 1 if kind == "daily" else 7
    ids = ids or []
    if kind != "manual" or not ids:
        top = await db.articles.find({"status": "published", "deleted": {"$ne": True}, "published_at": {"$gte": iso(now() - timedelta(days=days))}},
                                     {"id": 1}).sort("views", -1).limit(int(count or 8)).to_list(20)
        ids = [a["id"] for a in top]
    return {"id": new_id(), "subject": str(subject or ("Dnevni pregled vijesti" if kind == "daily" else "Sedmični pregled vijesti"))[:200],
            "intro": strip_tags(str(intro or ""))[:2000], "kind": kind, "article_ids": ids, "status": "draft",
            "recipients": await db.newsletter_subscribers.count_documents({"status": "confirmed"}), "created_by": created_by, "created_at": iso()}


def _img(a, base):
    u = (a.get("featured_image") or {}).get("medium") or ""
    if u.startswith("/api/"):
        u = base + u
    return f'<img src="{escape(u)}" alt="" width="560" style="width:100%;max-width:560px;border-radius:4px;display:block;margin-bottom:8px">' if u.startswith("https://") else ""


async def campaign_html(camp, base):
    arts = await db.articles.find({"id": {"$in": camp["article_ids"]}}, {"_id": 0, "id": 1, "title": 1, "slug": 1, "summary": 1, "featured_image": 1}).to_list(50)
    order = {i: n for n, i in enumerate(camp["article_ids"])}
    arts.sort(key=lambda a: order.get(a["id"], 99))
    items = "".join(
        f'<div style="padding:14px 0;border-bottom:1px solid #E6E9EF">{_img(a, base)}'
        f'<a href="{escape(base)}/vijesti/{escape(a["slug"])}" style="color:#0B1F3B;font-size:18px;font-weight:bold;text-decoration:none">{escape(a["title"])}</a>'
        f'<p style="margin:6px 0 0;color:#444;font-size:14px">{escape((a.get("summary") or "")[:220])}</p></div>' for a in arts)
    intro = f'<p>{escape(camp["intro"])}</p>' if camp.get("intro") else ""
    return intro + items, len(arts)


def _footer(base, token):
    return (f'<p style="font-size:12px;color:#888;margin-top:18px">Ovaj e-mail primate jer ste se prijavili na newsletter. '
            f'<a href="{escape(base)}/newsletter?odjava={escape(token)}" style="color:#888">Odjavi se</a></p>')


async def send_campaign(cid, base, frequency=None):
    camp = await db.newsletter_campaigns.find_one({"id": cid}, {"_id": 0})
    body, n = await campaign_html(camp, base)
    q = {"status": "confirmed"}
    if frequency:
        q["frequency"] = frequency
    subs = await db.newsletter_subscribers.find(q, {"_id": 0, "email": 1, "token": 1}).to_list(100000)
    sent = failed = 0
    for s in subs:
        html = email_template(camp["subject"], body + _footer(base, s["token"]), f"{base}/", "Otvori portal")
        try:
            ok = await send_email(to=s["email"], subject=camp["subject"], html=html)
        except Exception as e:
            logger.warning("Newsletter send error %s", e)
            ok = False
        sent, failed = sent + ok, failed + (not ok)
        await db.newsletter_campaigns.update_one({"id": cid}, {"$set": {"sent_count": sent, "failed_count": failed}})
        await asyncio.sleep(0.3)
    await db.newsletter_campaigns.update_one({"id": cid}, {"$set": {"status": "sent", "sent_at": iso(), "recipients": len(subs), "sent_count": sent, "failed_count": failed}})


async def start_send(cid, base, frequency=None):
    r = await db.newsletter_campaigns.update_one({"id": cid, "status": {"$in": ["draft", "failed"]}}, {"$set": {"status": "sending", "sent_count": 0, "failed_count": 0}})
    if not r.modified_count:
        return False

    async def run():
        try:
            await send_campaign(cid, base, frequency)
        except Exception as e:
            logger.exception("Campaign failed: %s", e)
            await db.newsletter_campaigns.update_one({"id": cid}, {"$set": {"status": "failed"}})
    asyncio.create_task(run())
    return True


async def auto_digest(kind, base):
    s = await get_settings()
    if not s.get("newsletter_enabled", True):
        return
    camp = await build_campaign(kind=kind, created_by="Automatski")
    if not camp["article_ids"]:
        return
    await db.newsletter_campaigns.insert_one(dict(camp))
    await start_send(camp["id"], base, frequency=kind)
