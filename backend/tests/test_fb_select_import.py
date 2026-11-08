# FB selective import (checkbox keys), junk filtering, ignored list, cron never imports junk/ignored
import os
import sys
import time
import asyncio
import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
CRON = os.environ["WEBHOOK_CRON_SECRET"]
ORIG_KEYS = {"fb-1794118158", "fb-1794127197"}
STATE = {}


def mongo(coro_fn):
    from motor.motor_asyncio import AsyncIOMotorClient
    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        return await coro_fn(db)
    return asyncio.run(run())


def fb_count():
    return mongo(lambda db: db.articles.count_documents({"fb_post_key": {"$exists": True}}))


@pytest.fixture(scope="module")
def s():
    ss = requests.Session()
    r = ss.post(f"{BASE_URL}/api/auth/login", json={"email": "test_fb@ccn.ba", "password": "TestFb12345A"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    yield ss
    # cleanup: hard-delete FB articles beyond original 2, clear fb_ignored
    async def clean(db):
        extra = [a["id"] async for a in db.articles.find({"fb_post_key": {"$exists": True, "$nin": list(ORIG_KEYS)}}, {"id": 1})]
        if extra:
            await db.articles.delete_many({"id": {"$in": extra}})
            await db.article_versions.delete_many({"article_id": {"$in": extra}})
        await db.fb_ignored.delete_many({})
        return extra
    print("cleanup removed", mongo(clean))


def posts(s):
    r = s.get(f"{BASE_URL}/api/admin/facebook/posts")
    assert r.status_code == 200, r.text
    return r.json()


# --- unit: junk detection
def test_is_junk_unit():
    from fb_import import is_junk
    assert is_junk({"message": "Na prodaju mini cooper", "photoURL": "x"})
    assert is_junk({"message": "Lijepa vijest", "photoURL": None})
    assert is_junk({"message": "Hitno potreban stan, tražim stan", "photoURL": "x"})
    assert not is_junk({"message": "Otvoren novi park u Cazinu", "photoURL": "x"})


def test_is_junk_false_positive_oglasio():
    # 'oglas' substring matches common news words like 'oglasio se', 'proglasio'
    from fb_import import is_junk
    assert not is_junk({"message": "Načelnik se oglasio povodom poplava", "photoURL": "x"}), "false positive: 'oglasio'"


# --- list posts
def test_list_posts_structure(s):
    ps = posts(s)
    STATE["posts"] = ps
    assert 1 <= len(ps) <= 10
    for p in ps:
        assert set(["key", "title", "summary", "image", "created_at", "status", "suggested"]) <= set(p)
        assert p["status"] in ("new", "imported", "ignored")
    st = {p["key"]: p["status"] for p in ps}
    for k in ORIG_KEYS:
        if k in st:
            assert st[k] == "imported"
    print([(p["key"], p["title"][:30], p["status"], p["suggested"]) for p in ps])


def test_legacy_import_skips_junk(s):
    before = fb_count()
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8})
    assert r.status_code == 200, r.text
    junk_new = [p for p in STATE["posts"] if p["status"] == "new" and not p["suggested"]]
    sugg_new = [p for p in STATE["posts"] if p["status"] == "new" and p["suggested"]]
    assert len(r.json()["imported"]) == len(sugg_new)
    assert fb_count() == before + len(sugg_new)
    assert all(p["title"] not in r.json()["imported"] for p in junk_new)


def test_cron_never_imports_junk(s):
    before = fb_count()
    r = requests.post(f"{BASE_URL}/api/cron/facebook-import", headers={"Authorization": f"Bearer {CRON}"})
    assert r.status_code == 200 and r.json()["ok"]
    time.sleep(12)
    assert fb_count() == before


def test_cron_unauthorized():
    r = requests.post(f"{BASE_URL}/api/cron/facebook-import", headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


def test_import_empty_selection_marks_ignored(s):
    before = fb_count()
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": []})
    assert r.status_code == 200 and r.json()["imported"] == []
    assert fb_count() == before
    ps = posts(s)
    assert all(p["status"] in ("imported", "ignored") for p in ps)
    assert any(p["status"] == "ignored" for p in ps)
    STATE["posts"] = ps


def test_cron_never_imports_ignored(s):
    before = fb_count()
    requests.post(f"{BASE_URL}/api/cron/facebook-import", headers={"Authorization": f"Bearer {CRON}"})
    time.sleep(12)
    assert fb_count() == before


def test_select_ignored_imports_it_only(s):
    ign = [p for p in STATE["posts"] if p["status"] == "ignored"]
    target = ign[0]
    before = fb_count()
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": [target["key"]]})
    assert r.status_code == 200, r.text
    assert r.json()["imported"] == [target["title"]]
    assert fb_count() == before + 1
    st = {p["key"]: p["status"] for p in posts(s)}
    assert st[target["key"]] == "imported"
    for p in ign[1:]:
        assert st[p["key"]] == "ignored"
    assert mongo(lambda db: db.fb_ignored.count_documents({"key": target["key"]})) == 0
    STATE["target"] = target


def test_reselect_imported_no_duplicate(s):
    t = STATE["target"]
    before = fb_count()
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": [t["key"], *ORIG_KEYS]})
    assert r.status_code == 200
    assert r.json()["imported"] == []
    assert r.json()["skipped"] >= 1
    assert fb_count() == before


def test_invalid_keys_type(s):
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"keys": "abc"})
    assert r.status_code == 400


def test_unauthenticated():
    assert requests.get(f"{BASE_URL}/api/admin/facebook/posts").status_code in (401, 403)
    assert requests.post(f"{BASE_URL}/api/admin/facebook/import", json={"keys": []}).status_code in (401, 403)
