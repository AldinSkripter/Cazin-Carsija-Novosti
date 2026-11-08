import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict

import bcrypt
import jwt
import nh3
from fastapi import Request, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
JWT_ALG = "HS256"
ACCESS_MIN = 30
REFRESH_DAYS = 7

PERMISSIONS = {
    "articles.create": "Kreiranje članaka",
    "articles.edit_own": "Uređivanje vlastitih članaka",
    "articles.edit_all": "Uređivanje svih članaka",
    "articles.publish": "Objavljivanje članaka",
    "articles.approve": "Odobravanje / odbijanje članaka",
    "articles.delete": "Brisanje članaka",
    "categories.manage": "Kategorije i oznake",
    "media.manage": "Medijska biblioteka",
    "homepage.manage": "Uređivanje početne stranice",
    "breaking.manage": "Breaking News",
    "comments.moderate": "Moderacija komentara",
    "submissions.manage": "Prijavljene vijesti",
    "ads.manage": "Reklame",
    "newsletter.manage": "Newsletter",
    "pages.manage": "Stranice i meniji",
    "cameras.manage": "Live kamere",
    "analytics.view": "Statistika",
    "audit.view": "Audit log",
    "ai.use": "AI asistent",
    "users.manage": "Korisnici i uloge",
    "settings.manage": "Sistemske postavke",
}

ALL = list(PERMISSIONS.keys())
ROLE_DEFAULTS = {
    "super_admin": ("Vlasnik / Super Admin", ALL),
    "chief_editor": ("Glavni urednik", [p for p in ALL if p not in ("users.manage", "settings.manage")]),
    "editor": ("Urednik", ["articles.create", "articles.edit_own", "articles.edit_all", "articles.publish", "articles.approve",
                           "media.manage", "breaking.manage", "homepage.manage", "ai.use", "submissions.manage", "analytics.view"]),
    "journalist": ("Novinar", ["articles.create", "articles.edit_own", "media.manage", "ai.use"]),
    "author": ("Ovlašteni autor", ["articles.create", "articles.edit_own", "media.manage", "ai.use"]),
    "moderator": ("Moderator", ["comments.moderate", "submissions.manage"]),
    "marketing": ("Marketing", ["ads.manage", "analytics.view"]),
}

STATUSES = ["draft", "review", "approved", "scheduled", "published", "archived", "rejected"]


def now():
    return datetime.now(timezone.utc)


def iso(dt=None):
    return (dt or now()).isoformat()


def new_id():
    return str(uuid.uuid4())


TRANSLIT = str.maketrans({"č": "c", "ć": "c", "š": "s", "đ": "dj", "ž": "z", "Č": "c", "Ć": "c", "Š": "s", "Đ": "dj", "Ž": "z"})


def fold(s: str) -> str:
    return (s or "").translate(TRANSLIT).lower()


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", fold(s)).strip("-")
    return s[:90] or new_id()[:8]


def hash_pw(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_pw(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except Exception:
        return False


def secret():
    return os.environ["JWT_SECRET"]


def make_token(user_id: str, sid: str, kind: str):
    exp = now() + (timedelta(minutes=ACCESS_MIN) if kind == "access" else timedelta(days=REFRESH_DAYS))
    return jwt.encode({"sub": user_id, "sid": sid, "type": kind, "exp": exp}, secret(), algorithm=JWT_ALG)


def set_auth_cookies(response, user_id, sid):
    for kind, age in (("access", ACCESS_MIN * 60), ("refresh", REFRESH_DAYS * 86400)):
        response.set_cookie(f"{kind}_token", make_token(user_id, sid, kind), httponly=True, secure=True,
                            samesite="lax", max_age=age, path="/")


def clean(doc):
    if doc:
        doc.pop("_id", None)
        doc.pop("password_hash", None)
        doc.pop("totp_secret", None)
    return doc


async def permissions_for(user) -> list:
    role = await db.roles.find_one({"key": user.get("role")}, {"_id": 0})
    perms = set(role["permissions"] if role else [])
    perms |= set(user.get("extra_permissions") or [])
    return sorted(p for p in perms if p in PERMISSIONS)


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401, "Niste prijavljeni")
    try:
        payload = jwt.decode(token, secret(), algorithms=[JWT_ALG])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Sesija je istekla")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Neispravan token")
    if payload.get("type") != "access":
        raise HTTPException(401, "Neispravan token")
    sess = await db.sessions.find_one({"id": payload.get("sid"), "user_id": payload["sub"], "revoked": False})
    if not sess:
        raise HTTPException(401, "Sesija nije aktivna")
    user = await db.users.find_one({"id": payload["sub"], "deleted": {"$ne": True}})
    if not user or not user.get("active", True):
        raise HTTPException(401, "Korisnik nije aktivan")
    user = clean(user)
    user["permissions"] = await permissions_for(user)
    user["session_id"] = payload["sid"]
    return user


def require(*perms):
    async def dep(user=Depends(get_current_user)):
        if not any(p in user["permissions"] for p in perms):
            raise HTTPException(403, "Nemate dozvolu za ovu akciju")
        return user
    return dep


async def audit(user, action: str, entity: str = "", entity_id: str = "", details: str = "", ip: str = ""):
    await db.audit_logs.insert_one({
        "id": new_id(), "user_id": user.get("id") if user else None, "user_name": user.get("name") if user else "Sistem",
        "action": action, "entity": entity, "entity_id": entity_id, "details": details[:500], "ip": ip, "created_at": iso(),
    })


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "")


_hits = defaultdict(list)


def rate_limit(key: str, limit: int, window: int):
    t = time.time()
    _hits[key] = [x for x in _hits[key] if x > t - window]
    if len(_hits[key]) >= limit:
        raise HTTPException(429, "Previše zahtjeva, pokušajte kasnije")
    _hits[key].append(t)


ALLOWED_TAGS = {"p", "br", "strong", "b", "em", "i", "u", "s", "h2", "h3", "h4", "blockquote", "ul", "ol", "li", "a",
                "img", "figure", "figcaption", "table", "thead", "tbody", "tr", "th", "td", "hr", "div", "iframe", "span", "code", "pre"}
ALLOWED_ATTRS = {"a": {"href", "title", "target"}, "img": {"src", "alt", "title", "width", "height"},
                 "iframe": {"src", "width", "height", "allowfullscreen", "frameborder", "allow"},
                 "div": {"data-youtube-video"}, "td": {"colspan", "rowspan"}, "th": {"colspan", "rowspan"}}


def _attr_filter(tag, attr, value):
    if tag == "iframe" and attr == "src":
        ok = value.startswith(("https://www.youtube.com/embed/", "https://www.youtube-nocookie.com/embed/", "https://player.vimeo.com/"))
        return value if ok else None
    return value


def sanitize_html(html: str) -> str:
    return nh3.clean(html or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, attribute_filter=_attr_filter,
                     url_schemes={"http", "https", "mailto", "tel"})


def strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


async def get_settings() -> dict:
    s = await db.settings.find_one({"key": "site"}, {"_id": 0})
    return (s or {}).get("value", {})
