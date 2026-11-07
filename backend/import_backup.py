"""Import a CČN backup JSON into MongoDB and download its media files into MEDIA_DIR.
Usage: python import_backup.py /data/backup.json https://stari-sajt.example
"""
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import httpx
from motor.motor_asyncio import AsyncIOMotorClient

COLLS = ["articles", "article_versions", "categories", "tags", "media", "pages", "breaking_news", "advertisers", "ad_campaigns",
         "comments", "blocked_users", "submissions", "newsletter_subscribers", "newsletter_campaigns", "settings", "roles", "users",
         "redirects", "cameras", "privacy_requests"]
MEDIA_RE = re.compile(r"/api/media/file/(ccn-portal/media/[A-Za-z0-9_\-./]+?\.(?:webp|jpe?g|png|gif|avif|pdf|mp4))")


async def main(path, old_url):
    raw = Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    for c in COLLS:
        docs = data.get(c)
        if isinstance(docs, list) and docs:
            await db[c].delete_many({})
            await db[c].insert_many(docs)
            print(f"  {c}: {len(docs)}")
    site = os.environ.get("SITE_URL")
    if site:
        await db.settings.update_one({"key": "site"}, {"$set": {"value.site_url": site}})
    root = Path(os.environ["MEDIA_DIR"])
    files = sorted(set(MEDIA_RE.findall(raw)))
    ok = fail = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as cl:
        sem = asyncio.Semaphore(6)

        async def fetch(p):
            nonlocal ok, fail
            dest = root / p
            if dest.exists() and dest.stat().st_size:
                ok += 1
                return
            async with sem:
                try:
                    r = await cl.get(f"{old_url.rstrip('/')}/api/media/file/{p}")
                    r.raise_for_status()
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(r.content)
                    ok += 1
                except Exception:
                    fail += 1
        await asyncio.gather(*(fetch(p) for p in files))
    print(f"  slike: {ok} preuzeto, {fail} neuspjelo")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2]))
