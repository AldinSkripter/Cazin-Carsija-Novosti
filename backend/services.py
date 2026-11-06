import io
import os
import logging
from html import escape

import httpx
import requests
from PIL import Image, ImageOps

from core import new_id

logger = logging.getLogger("services")
APP_NAME = "ccn-portal"
STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_storage_key = None


def init_storage(force=False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    r = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
    r.raise_for_status()
    _storage_key = r.json()["storage_key"]
    return _storage_key


def put_object(path, data, content_type):
    for attempt in (0, 1):
        r = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(attempt == 1), "Content-Type": content_type},
                         data=data, timeout=120)
        if r.status_code == 404 and attempt == 0:
            continue
        r.raise_for_status()
        return r.json()


def get_object(path):
    for attempt in (0, 1):
        r = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(attempt == 1)}, timeout=60)
        if r.status_code == 404 and attempt == 0:
            continue
        r.raise_for_status()
        return r.content, r.headers.get("Content-Type", "application/octet-stream")


SIZES = {"large": 1600, "medium": 900, "thumb": 420}
MAX_UPLOAD = 15 * 1024 * 1024


def process_image(raw: bytes, crop=None):
    """Validate, strip EXIF, create WebP variants. Returns (media_id, variants, w, h)."""
    if len(raw) > MAX_UPLOAD:
        raise ValueError("Datoteka je prevelika (max 15 MB)")
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()
        img = Image.open(io.BytesIO(raw))
        if img.format not in ("JPEG", "PNG", "WEBP", "AVIF", "GIF"):
            raise ValueError
    except Exception:
        raise ValueError("Neispravna ili nepodržana slika (JPG, PNG, WebP, AVIF)")
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA") if img.mode in ("P", "LA") else img
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    if crop:
        x, y, w, h = [int(crop[k]) for k in ("x", "y", "w", "h")]
        img = img.crop((x, y, x + w, y + h))
    mid = new_id()
    variants = {}
    for name, width in SIZES.items():
        im = img.copy()
        if im.width > width:
            im = im.resize((width, int(im.height * width / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=80, method=4)
        res = put_object(f"{APP_NAME}/media/{mid}/{name}.webp", buf.getvalue(), "image/webp")
        variants[name] = f"/api/media/file/{res['path']}"
    return mid, variants, img.width, img.height


# ---------- Email (Emergent managed) ----------
EMAIL_BASE_URL = "https://integrations.emergentagent.com"


def _assert_safe_email(subject: str, html: str) -> None:
    low = f"{subject}\n{html}".lower()
    if "<form" in low or "<input" in low:
        raise ValueError("No forms in email")
    for part in low.split('href="')[1:]:
        if not part.startswith(("https://", "mailto:")):
            raise ValueError("Links must be https")


async def send_email(*, to: str, subject: str, html: str):
    _assert_safe_email(subject, html)
    payload = {"to": [to], "subject": subject, "html": html, "from_name": os.environ["EMAIL_FROM_NAME"]}
    if os.environ.get("EMAIL_REPLY_TO"):
        payload["contact_email"] = os.environ["EMAIL_REPLY_TO"]
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.post(f"{EMAIL_BASE_URL}/api/v1/email/send", headers={"X-Email-Key": os.environ["EMERGENT_EMAIL_KEY"]}, json=payload)
    if r.status_code >= 400:
        logger.warning("Email failed %s %s", r.status_code, r.text[:300])
        return False
    return True


def email_template(title: str, body_html: str, link: str = "", link_label: str = "") -> str:
    name = escape(os.environ["EMAIL_FROM_NAME"])
    btn = (f'<p><a href="{escape(link)}" style="background:#00C2B8;color:#0B1F3B;padding:12px 20px;'
           f'text-decoration:none;font-weight:bold;border-radius:4px">{escape(link_label)}</a></p>') if link else ""
    return (f'<table role="presentation" width="100%"><tr><td style="background:#0B1F3B;padding:18px 24px;color:#D4A52C;'
            f'font-family:Georgia,serif;font-size:20px;font-weight:bold">{name}</td></tr>'
            f'<tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0B1F3B"><h2>{escape(title)}</h2>{body_html}{btn}'
            f'<p style="font-size:12px;color:#888">Poslano od {name}. Nikada ne tražimo vašu lozinku putem e-maila.</p></td></tr></table>')


# ---------- AI (Claude Sonnet 5.5) ----------
AI_SYSTEM = ("Ti si urednički asistent bosanskog informativnog portala Cazin Čaršija Novosti. Pišeš na bosanskom jeziku (ijekavica). "
             "STROGO: nikada ne izmišljaj činjenice, izjave, imena, brojke, izvore ili fotografije. Koristi isključivo informacije iz "
             "dostavljenog teksta. Ako informacija nedostaje, to naglasi. Odgovaraj sažeto, bez uvoda.")


async def ai_generate(prompt: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=new_id(), system_message=AI_SYSTEM)
    chat.with_model("anthropic", "claude-sonnet-5-5")
    return await chat.send_message(UserMessage(text=prompt))
