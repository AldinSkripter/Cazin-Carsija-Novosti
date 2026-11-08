import io
import re
import base64
import secrets as pysecrets
from datetime import timedelta

import pyotp
import qrcode
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel
import jwt

from core import (db, new_id, iso, now, hash_pw, verify_pw, set_auth_cookies, get_current_user, clean, audit,
                  client_ip, rate_limit, secret, JWT_ALG, permissions_for)
from services import send_email, email_template

router = APIRouter(prefix="/api/auth")


class LoginIn(BaseModel):
    email: str
    password: str
    totp: str | None = None


class PwIn(BaseModel):
    current_password: str
    new_password: str


class ResetIn(BaseModel):
    token: str
    password: str


class CodeIn(BaseModel):
    code: str


class ProfileIn(BaseModel):
    name: str | None = None
    bio: str | None = None
    avatar: str | None = None
    email: str | None = None
    current_password: str | None = None


def check_pw_policy(p: str):
    if len(p) < 10 or p.lower() == p or not any(c.isdigit() for c in p):
        raise HTTPException(400, "Lozinka mora imati najmanje 10 znakova, veliko slovo i broj")


async def create_session(request: Request, response: Response, user: dict):
    sid = new_id()
    await db.sessions.insert_one({"id": sid, "user_id": user["id"], "ip": client_ip(request),
                                  "user_agent": request.headers.get("user-agent", "")[:200], "created_at": iso(),
                                  "last_seen": iso(), "revoked": False})
    set_auth_cookies(response, user["id"], sid)


async def user_out(user):
    u = clean(dict(user))
    u["permissions"] = await permissions_for(u)
    u.pop("totp_pending", None)
    return u


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    ip = client_ip(request)
    rate_limit(f"login:{ip}", 20, 300)
    email = body.email.strip().lower()
    ident = f"{ip}:{email}"
    att = await db.login_attempts.find_one({"identifier": ident})
    if att and att.get("locked_until", "") <= iso() and att.get("count", 0) >= 5:
        await db.login_attempts.delete_one({"identifier": ident})
        att = None
    if att and att.get("count", 0) >= 5:
        raise HTTPException(429, "Previše neuspjelih pokušaja. Pokušajte za 15 minuta.")
    user = await db.users.find_one({"email": email, "deleted": {"$ne": True}})
    if not user or not verify_pw(body.password, user.get("password_hash", "")):
        cnt = (att or {}).get("count", 0) + 1
        await db.login_attempts.update_one({"identifier": ident}, {"$set": {"count": cnt, "locked_until": iso(now() + timedelta(minutes=15))}}, upsert=True)
        await audit(None, "auth.login_failed", "user", "", email, ip)
        raise HTTPException(401, "Pogrešan e-mail ili lozinka")
    if not user.get("active", True):
        raise HTTPException(403, "Račun je deaktiviran")
    if user.get("totp_enabled"):
        if not body.totp:
            return {"requires_2fa": True}
        if not pyotp.TOTP(user["totp_secret"]).verify(body.totp.strip(), valid_window=1):
            raise HTTPException(401, "Pogrešan 2FA kod")
    await db.login_attempts.delete_one({"identifier": ident})
    await db.sessions.delete_many({"user_id": user["id"], "$or": [{"revoked": True}, {"created_at": {"$lt": iso(now() - timedelta(days=7))}}]})
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": iso()}})
    await create_session(request, response, user)
    await audit(user, "auth.login", "user", user["id"], "", ip)
    return await user_out(user)


@router.post("/logout")
async def logout(response: Response, user=Depends(get_current_user)):
    await db.sessions.update_one({"id": user["session_id"]}, {"$set": {"revoked": True}})
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.post("/logout-all")
async def logout_all(response: Response, user=Depends(get_current_user)):
    await db.sessions.update_many({"user_id": user["id"]}, {"$set": {"revoked": True}})
    await audit(user, "auth.logout_all", "user", user["id"])
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"ok": True}


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Nema sesije")
    try:
        p = jwt.decode(token, secret(), algorithms=[JWT_ALG])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Sesija istekla")
    if p.get("type") != "refresh" or not await db.sessions.find_one({"id": p["sid"], "revoked": False}):
        raise HTTPException(401, "Sesija nije aktivna")
    await db.sessions.update_one({"id": p["sid"]}, {"$set": {"last_seen": iso()}})
    set_auth_cookies(response, p["sub"], p["sid"])
    return {"ok": True}


@router.post("/forgot-password")
async def forgot(body: dict, request: Request):
    rate_limit(f"forgot:{client_ip(request)}", 5, 600)
    email = str(body.get("email", "")).strip().lower()
    user = await db.users.find_one({"email": email, "deleted": {"$ne": True}})
    origin = request.headers.get("origin", "")
    if user and origin.startswith("https://"):
        token = pysecrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({"token": token, "user_id": user["id"], "used": False, "expires_at": now() + timedelta(hours=1)})
        html = email_template("Resetovanje lozinke", "<p>Primili smo zahtjev za resetovanje lozinke. Link vrijedi 1 sat.</p>",
                              f"{origin}/admin/reset-lozinke?token={token}", "Postavi novu lozinku")
        await send_email(to=email, subject="Resetovanje lozinke", html=html)
    return {"ok": True, "message": "Ako račun postoji, poslali smo link za resetovanje."}


@router.post("/reset-password")
async def reset(body: ResetIn):
    check_pw_policy(body.password)
    t = await db.password_reset_tokens.find_one({"token": body.token, "used": False})
    exp = t and t["expires_at"]
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=now().tzinfo)
    if not t or exp < now():
        raise HTTPException(400, "Link je neispravan ili je istekao")
    await db.users.update_one({"id": t["user_id"]}, {"$set": {"password_hash": hash_pw(body.password)}})
    await db.password_reset_tokens.update_one({"token": body.token}, {"$set": {"used": True}})
    await db.sessions.update_many({"user_id": t["user_id"]}, {"$set": {"revoked": True}})
    await audit({"id": t["user_id"], "name": ""}, "auth.password_reset", "user", t["user_id"])
    return {"ok": True}


@router.post("/change-password")
async def change_pw(body: PwIn, user=Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]})
    if not verify_pw(body.current_password, full["password_hash"]):
        raise HTTPException(400, "Trenutna lozinka nije ispravna")
    check_pw_policy(body.new_password)
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_pw(body.new_password)}})
    await db.sessions.update_many({"user_id": user["id"], "id": {"$ne": user["session_id"]}}, {"$set": {"revoked": True}})
    await audit(user, "auth.password_changed", "user", user["id"])
    return {"ok": True}


@router.put("/profile")
async def profile(body: ProfileIn, user=Depends(get_current_user)):
    upd = {k: v for k, v in body.model_dump(exclude={"email", "current_password"}).items() if v is not None}
    email = (body.email or "").strip().lower()
    if email and email != user["email"]:
        full = await db.users.find_one({"id": user["id"]})
        if not verify_pw(body.current_password or "", full["password_hash"]):
            raise HTTPException(400, "Za promjenu e-maila unesite ispravnu trenutnu lozinku")
        await ensure_email_free(email, user["id"])
        upd["email"] = email
    if upd.get("name") is not None and not upd["name"].strip():
        raise HTTPException(400, "Ime ne može biti prazno")
    await db.users.update_one({"id": user["id"]}, {"$set": upd})
    if "email" in upd:
        await audit(user, "auth.email_changed", "user", user["id"], f"{user['email']} → {email}")
    return {"ok": True}


async def ensure_email_free(email: str, uid: str):
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(400, "Unesite ispravnu e-mail adresu")
    if await db.users.find_one({"email": email, "id": {"$ne": uid}, "deleted": {"$ne": True}}):
        raise HTTPException(400, "Korisnik s tim e-mailom već postoji")


@router.post("/2fa/setup")
async def tfa_setup(user=Depends(get_current_user)):
    sec = pyotp.random_base32()
    await db.users.update_one({"id": user["id"]}, {"$set": {"totp_pending": sec}})
    uri = pyotp.TOTP(sec).provisioning_uri(name=user["email"], issuer_name="Cazin Čaršija Novosti")
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, "PNG")
    return {"secret": sec, "uri": uri, "qr": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()}


@router.post("/2fa/enable")
async def tfa_enable(body: CodeIn, user=Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]})
    sec = full.get("totp_pending")
    if not sec or not pyotp.TOTP(sec).verify(body.code.strip(), valid_window=1):
        raise HTTPException(400, "Pogrešan kod")
    await db.users.update_one({"id": user["id"]}, {"$set": {"totp_secret": sec, "totp_enabled": True}, "$unset": {"totp_pending": ""}})
    await audit(user, "auth.2fa_enabled", "user", user["id"])
    return {"ok": True}


@router.post("/2fa/disable")
async def tfa_disable(body: CodeIn, user=Depends(get_current_user)):
    full = await db.users.find_one({"id": user["id"]})
    if not full.get("totp_enabled") or not pyotp.TOTP(full["totp_secret"]).verify(body.code.strip(), valid_window=1):
        raise HTTPException(400, "Pogrešan kod")
    await db.users.update_one({"id": user["id"]}, {"$set": {"totp_enabled": False}, "$unset": {"totp_secret": ""}})
    await audit(user, "auth.2fa_disabled", "user", user["id"])
    return {"ok": True}


@router.get("/sessions")
async def sessions(user=Depends(get_current_user)):
    items = await db.sessions.find({"user_id": user["id"], "revoked": False}, {"_id": 0}).sort("created_at", -1).to_list(50)
    for s in items:
        s["current"] = s["id"] == user["session_id"]
    return items


@router.delete("/sessions/{sid}")
async def revoke_session(sid: str, user=Depends(get_current_user)):
    await db.sessions.update_one({"id": sid, "user_id": user["id"]}, {"$set": {"revoked": True}})
    return {"ok": True}
