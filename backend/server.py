from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import os
import logging
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from pymongo import ASCENDING, DESCENDING, IndexModel

from core import db, client
import routes_auth
import routes_public
import routes_articles
import routes_admin
import fb_import
from seed import seed_all
from services import init_storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Cazin Čaršija Novosti API", version="1.0", docs_url="/api/docs", openapi_url="/api/openapi.json")

INDEXES = {
    "users": [IndexModel([("email", ASCENDING)], unique=True), IndexModel([("id", ASCENDING)], unique=True), IndexModel([("slug", ASCENDING)])],
    "articles": [IndexModel([("id", ASCENDING)], unique=True), IndexModel([("slug", ASCENDING)]), IndexModel([("status", ASCENDING), ("published_at", DESCENDING)]),
                 IndexModel([("category_id", ASCENDING)]), IndexModel([("tags_folded", ASCENDING)]), IndexModel([("views", DESCENDING)]),
                 IndexModel([("updated_at", DESCENDING)]),
                 IndexModel([("fb_post_key", ASCENDING)], unique=True, partialFilterExpression={"fb_post_key": {"$type": "string"}}),
                 IndexModel([("fb_post_hash", ASCENDING)], unique=True, partialFilterExpression={"fb_post_hash": {"$type": "string"}})],
    "article_versions": [IndexModel([("article_id", ASCENDING), ("version", DESCENDING)])],
    "categories": [IndexModel([("slug", ASCENDING)], unique=True)],
    "sessions": [IndexModel([("id", ASCENDING)]), IndexModel([("user_id", ASCENDING)])],
    "login_attempts": [IndexModel([("identifier", ASCENDING)])],
    "password_reset_tokens": [IndexModel([("expires_at", ASCENDING)], expireAfterSeconds=0)],
    "events": [IndexModel([("day", ASCENDING), ("type", ASCENDING)]), IndexModel([("article_id", ASCENDING)])],
    "ad_events": [IndexModel([("day", ASCENDING), ("campaign_id", ASCENDING)])],
    "audit_logs": [IndexModel([("created_at", DESCENDING)]), IndexModel([("entity", ASCENDING), ("entity_id", ASCENDING)])],
    "comments": [IndexModel([("article_id", ASCENDING), ("status", ASCENDING)])],
    "media": [IndexModel([("id", ASCENDING)]), IndexModel([("created_at", DESCENDING)])],
    "newsletter_subscribers": [IndexModel([("email", ASCENDING)], unique=True), IndexModel([("token", ASCENDING)])],
    "redirects": [IndexModel([("from_path", ASCENDING)])],
    "settings": [IndexModel([("key", ASCENDING)], unique=True)],
    "fb_ignored": [IndexModel([("key", ASCENDING)], unique=True)],
    "roles": [IndexModel([("key", ASCENDING)], unique=True)],
}


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith(("/api/admin", "/api/auth")):
        origin = request.headers.get("origin")
        host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
        if origin and urlparse(origin).netloc not in (host, "localhost:3000", "localhost:8001"):
            return JSONResponse({"detail": "Neispravan izvor zahtjeva"}, status_code=403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "SAMEORIGIN"
    resp.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith(("/api/admin", "/api/auth")):
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.get("/api/health")
async def health():
    return {"ok": True}


for r in (routes_auth.router, routes_articles.router, routes_admin.router, routes_public.router, fb_import.router, fb_import.cron_router):
    app.include_router(r)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    for coll, models in INDEXES.items():
        for m in models:
            try:
                await db[coll].create_indexes([m])
            except Exception as e:
                logger.error("index %s: %s", coll, e)
    try:
        init_storage()
    except Exception as e:
        logger.error("Storage init failed: %s", e)
    await seed_all()


@app.on_event("shutdown")
async def shutdown():
    client.close()
