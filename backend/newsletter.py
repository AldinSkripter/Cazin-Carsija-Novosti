import asyncio
import logging
from urllib.parse import urlparse
from datetime import timedelta
from html import escape

from core import db, new_id, iso, now, strip_tags, get_settings
from services import send_email

logger = logging.getLogger(__name__)


async def resolve_base(request):
    s = await get_settings()
    if s.get("site_url"):
        return s["site_url"].rstrip("/")
    origin = request.headers.get("origin", "").rstrip("/")
    if not origin.startswith("https://"):
        ref = urlparse(request.headers.get("referer", ""))
        origin = f"https://{ref.netloc}" if ref.scheme == "https" and ref.netloc else ""
    if origin.startswith("https://"):
        await db.meta.update_one({"_id": "public_origin"}, {"$set": {"value": origin}}, upsert=True)
        return origin
    saved = await db.meta.find_one({"_id": "public_origin"})
    return saved["value"] if saved else f"https://{request.headers.get('host', '')}"


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


DAYS = ["Ponedjeljak", "Utorak", "Srijeda", "Četvrtak", "Petak", "Subota", "Nedjelja"]
MONTHS = ["januar", "februar", "mart", "april", "maj", "juni", "juli", "august", "septembar", "oktobar", "novembar", "decembar"]
SERIF = "Georgia,'Times New Roman',serif"
SANS = "'Helvetica Neue',Helvetica,Arial,sans-serif"
LABEL = {"daily": "Dnevni pregled", "weekly": "Sedmični pregled", "manual": "Izdvojeno za vas"}


def _img_url(a, base, size="medium"):
    fi = a.get("featured_image") or {}
    u = fi.get(size) or fi.get("medium") or ""
    if u.startswith("/api/"):
        u = base + u
    return u if u.startswith("https://") else ""


async def _articles(camp):
    arts = await db.articles.find({"id": {"$in": camp["article_ids"]}}, {"_id": 0, "id": 1, "title": 1, "slug": 1, "summary": 1, "featured_image": 1, "category_id": 1}).to_list(50)
    cats = {c["id"]: c["name"] for c in await db.categories.find({}, {"_id": 0, "id": 1, "name": 1}).to_list(500)}
    order = {i: n for n, i in enumerate(camp["article_ids"])}
    arts.sort(key=lambda a: order.get(a["id"], 99))
    for a in arts:
        a["cat"] = cats.get(a.get("category_id"), "Vijesti")
    return arts


def _hero(a, base):
    url, img = f"{base}/vijesti/{a['slug']}", _img_url(a, base, "large")
    pic = (f'<tr><td><a href="{escape(url)}"><img src="{escape(img)}" alt="{escape(a["title"])}" width="600" height="320" style="display:block;width:100%;max-width:600px;height:320px;object-fit:cover;border:0"></a></td></tr>') if img else ""
    return (f'{pic}<tr><td class="px" style="padding:28px 40px 32px;background:#ffffff">'
            f'<p style="margin:0 0 12px;font:700 11px/1 {SANS};letter-spacing:2px;text-transform:uppercase;color:#D4A52C">{escape(a["cat"])} &nbsp;<span style="color:#E1142B">&#9679;</span>&nbsp; Glavna vijest</p>'
            f'<a href="{escape(url)}" style="text-decoration:none"><h1 style="margin:0 0 14px;font:700 28px/1.25 {SERIF};color:#0B1F3B">{escape(a["title"])}</h1></a>'
            f'<p style="margin:0 0 22px;font:400 16px/1.6 {SANS};color:#4A5568">{escape((a.get("summary") or "")[:300])}</p>'
            f'<a href="{escape(url)}" style="display:inline-block;background:#00C2B8;color:#0B1F3B;font:700 14px/1 {SANS};padding:14px 26px;border-radius:999px;text-decoration:none">Pročitaj vijest &rarr;</a>'
            f'</td></tr>')


def _row(a, base, n):
    url, img = f"{base}/vijesti/{a['slug']}", _img_url(a, base, "thumb")
    thumb = (f'<td class="stack" width="170" valign="top" style="padding:0 20px 0 0"><a href="{escape(url)}"><img src="{escape(img)}" alt="" width="170" height="120" class="thumb" '
             f'style="display:block;width:170px;max-width:100%;height:120px;object-fit:cover;border:0;border-radius:6px"></a></td>') if img else ""
    return (f'<tr><td class="px" style="padding:0 40px;background:#ffffff"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #E6E9EF"><tr><td style="padding:22px 0">'
            f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>{thumb}<td class="stack" valign="top">'
            f'<p style="margin:0 0 8px;font:700 10px/1 {SANS};letter-spacing:2px;text-transform:uppercase;color:#00A39B">{n:02d} &nbsp;&middot;&nbsp; {escape(a["cat"])}</p>'
            f'<a href="{escape(url)}" style="text-decoration:none"><h3 style="margin:0 0 8px;font:700 19px/1.3 {SERIF};color:#0B1F3B">{escape(a["title"])}</h3></a>'
            f'<p style="margin:0;font:400 14px/1.55 {SANS};color:#5A6578">{escape((a.get("summary") or "")[:160])}</p>'
            f'</td></tr></table></td></tr></table></td></tr>')


async def render_email(camp, base, token):
    arts = await _articles(camp)
    d = now()
    date = f"{DAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} {d.year}."
    b, label = escape(base), LABEL.get(camp.get("kind"), LABEL["manual"])
    pre = escape(camp.get("intro") or (arts[0]["title"] if arts else camp["subject"]))[:150]
    intro = (f'<tr><td class="px" style="padding:36px 40px 8px;background:#ffffff">'
             f'<p style="margin:0 0 6px;font:700 11px/1 {SANS};letter-spacing:3px;text-transform:uppercase;color:#00A39B">{escape(label)}</p>'
             f'<h2 style="margin:0 0 12px;font:700 24px/1.3 {SERIF};color:#0B1F3B">{escape(camp["subject"])}</h2>'
             + (f'<p style="margin:0 0 8px;font:400 16px/1.65 {SANS};color:#4A5568">{escape(camp["intro"])}</p>' if camp.get("intro") else
                f'<p style="margin:0 0 8px;font:400 16px/1.65 {SANS};color:#4A5568">Izdvojili smo najzanimljivije priče iz Cazina, Krajine i svijeta. Ugodno čitanje.</p>')
             + '<div style="width:56px;height:3px;background:#D4A52C;margin-top:18px"></div></td></tr>')
    hero = _hero(arts[0], base) if arts else ""
    more = ""
    if len(arts) > 1:
        more = (f'<tr><td class="px" style="padding:8px 40px 4px;background:#ffffff"><p style="margin:0;font:700 13px/1 {SANS};letter-spacing:2px;text-transform:uppercase;color:#0B1F3B">'
                f'<span style="display:inline-block;width:10px;height:10px;background:#E1142B;border-radius:50%;margin-right:8px"></span>Još iz pregleda</p></td></tr>'
                + "".join(_row(a, base, i + 2) for i, a in enumerate(arts[1:])))
    return f'''<!DOCTYPE html><html lang="bs"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light">
<title>{escape(camp["subject"])}</title><style>@media (max-width:620px){{.px{{padding-left:22px!important;padding-right:22px!important}}.stack{{display:block!important;width:100%!important;padding:0 0 14px 0!important}}h1{{font-size:24px!important}}.thumb{{width:100%!important;height:180px!important}}}}</style></head>
<body style="margin:0;padding:0;background:#E6E9EF"><div style="display:none;max-height:0;overflow:hidden;opacity:0">{pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#E6E9EF"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px">
<tr><td style="padding:0 4px 12px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
<td style="font:400 12px/1 {SANS};color:#5A6578">{date}</td><td align="right"><a href="{b}/" style="font:600 12px/1 {SANS};color:#0B1F3B;text-decoration:none">Otvori u pregledniku &rarr;</a></td></tr></table></td></tr>
<tr><td align="center" style="background:#0B1F3B;padding:30px 24px 22px;border-radius:12px 12px 0 0"><a href="{b}/"><img src="{b}/logo-email.png" alt="Cazin Čaršija Novosti" width="240" style="display:block;width:240px;height:auto;border:0"></a>
<p style="margin:14px 0 0;font:600 11px/1 {SANS};letter-spacing:3px;text-transform:uppercase;color:#D4A52C">Cazin &middot; Krajina &middot; BiH &middot; Svijet</p></td></tr>
<tr><td style="height:4px;line-height:4px;font-size:0;background:#00C2B8">&nbsp;</td></tr>
{intro}{hero}{more}
<tr><td class="px" align="center" style="background:#ffffff;padding:28px 40px 40px;border-radius:0 0 12px 12px"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F6F9;border-radius:10px"><tr><td align="center" style="padding:26px 20px">
<p style="margin:0 0 6px;font:700 18px/1.3 {SERIF};color:#0B1F3B">Imate vijest iz vašeg mjesta?</p><p style="margin:0 0 16px;font:400 14px/1.5 {SANS};color:#5A6578">Pošaljite nam informaciju, fotografiju ili video.</p>
<a href="{b}/prijavite-vijest" style="display:inline-block;background:#0B1F3B;color:#ffffff;font:700 13px/1 {SANS};padding:13px 24px;border-radius:999px;text-decoration:none">Prijavite vijest</a>&nbsp;
<a href="{b}/kamere" style="display:inline-block;border:2px solid #0B1F3B;color:#0B1F3B;font:700 13px/1 {SANS};padding:11px 22px;border-radius:999px;text-decoration:none">Kamere na granici</a></td></tr></table></td></tr>
<tr><td align="center" style="padding:26px 24px 8px;font:400 12px/1.7 {SANS};color:#5A6578"><p style="margin:0 0 6px;font:700 14px/1 {SERIF};color:#0B1F3B">Cazin Čaršija Novosti</p>
<p style="margin:0 0 10px">Ovaj e-mail primate jer ste se prijavili na newsletter portala.<br><a href="{b}/" style="color:#0B1F3B">Portal</a> &nbsp;&middot;&nbsp; <a href="{b}/stranica/politika-privatnosti" style="color:#0B1F3B">Privatnost</a> &nbsp;&middot;&nbsp; <a href="{b}/newsletter?odjava={escape(token)}" style="color:#E1142B">Odjavi se</a></p>
<p style="margin:0;color:#8A94A6">&copy; {d.year} Cazin Čaršija Novosti</p></td></tr>
</table></td></tr></table></body></html>'''


async def send_campaign(cid, base, frequency=None):
    camp = await db.newsletter_campaigns.find_one({"id": cid}, {"_id": 0})
    q = {"status": "confirmed"}
    if frequency:
        q["frequency"] = frequency
    subs = await db.newsletter_subscribers.find(q, {"_id": 0, "email": 1, "token": 1}).to_list(100000)
    sent = failed = 0
    for s in subs:
        html = await render_email(camp, base, s["token"])
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
    if not camp["article_ids"] or not await db.newsletter_subscribers.count_documents({"status": "confirmed", "frequency": kind}):
        return
    await db.newsletter_campaigns.insert_one(dict(camp))
    await start_send(camp["id"], base, frequency=kind)
