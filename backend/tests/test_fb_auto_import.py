# Tests: FB hourly auto-import cron (auth, enable/disable), dedup (repeat/concurrent/soft-deleted), author selection
import os
import time
import uuid
import asyncio
import concurrent.futures as cf
import pytest
import requests
from dotenv import dotenv_values
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ENV = dotenv_values("/app/backend/.env")
SECRET = ENV["WEBHOOK_CRON_SECRET"]
SA_EMAIL, SA_PW, PW = "test_fb@ccn.ba", "TestFb12345A", "TestUser12345A"
CRON = f"{BASE_URL}/api/cron/facebook-import"


def mongo(coro_fn):
    async def run():
        c = AsyncIOMotorClient(ENV["MONGO_URL"])
        try:
            return await coro_fn(c[ENV["DB_NAME"]])
        finally:
            c.close()
    return asyncio.run(run())


def fb_count(include_deleted=True):
    q = {"fb_post_key": {"$type": "string"}}
    return mongo(lambda db: db.articles.count_documents(q))


def cron():
    return requests.post(CRON, headers={"Authorization": f"Bearer {SECRET}"}, json={})


@pytest.fixture(scope="module")
def sa():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": SA_EMAIL, "password": SA_PW})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.text}")
    yield s
    s.put(f"{BASE_URL}/api/admin/facebook/auto", json={"enabled": True, "author_id": None})


@pytest.fixture(scope="module")
def journalist(sa):
    em = f"test_j_{uuid.uuid4().hex[:6]}@ccn.ba"
    r = sa.post(f"{BASE_URL}/api/admin/users", json={"name": "TEST_journalist", "email": em, "password": PW, "role": "journalist"})
    assert r.status_code == 200, r.text
    u = r.json()
    s = requests.Session()
    assert s.post(f"{BASE_URL}/api/auth/login", json={"email": em, "password": PW}).status_code == 200
    yield u, s
    sa.delete(f"{BASE_URL}/api/admin/users/{u['id']}")
    mongo(lambda db: db.users.delete_one({"id": u["id"]}))


def wait_run(sa, prev, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        st = sa.get(f"{BASE_URL}/api/admin/facebook/auto").json()
        if st.get("last_run") != prev:
            return st
        time.sleep(2)
    return None


class TestCronAuth:
    def test_no_auth(self):
        assert requests.post(CRON, json={}).status_code == 401

    def test_wrong_bearer(self):
        assert requests.post(CRON, headers={"Authorization": "Bearer nope"}, json={}).status_code == 401

    def test_basic_scheme(self):
        assert requests.post(CRON, headers={"Authorization": SECRET}, json={}).status_code == 401


class TestAutoSettings:
    def test_get_shape(self, sa):
        d = sa.get(f"{BASE_URL}/api/admin/facebook/auto").json()
        for k in ("enabled", "last_run", "last_imported", "author_id"):
            assert k in d

    def test_journalist_forbidden(self, journalist):
        _, s = journalist
        assert s.get(f"{BASE_URL}/api/admin/facebook/auto").status_code == 403
        assert s.put(f"{BASE_URL}/api/admin/facebook/auto", json={"enabled": False}).status_code == 403

    def test_unknown_author(self, sa):
        r = sa.put(f"{BASE_URL}/api/admin/facebook/auto", json={"author_id": "nonexistent-id"})
        assert r.status_code == 400

    def test_disabled_cron_noop(self, sa):
        r = sa.put(f"{BASE_URL}/api/admin/facebook/auto", json={"enabled": False})
        assert r.status_code == 200 and r.json()["enabled"] is False
        prev = r.json()["last_run"]
        t = time.time()
        r = cron()
        assert r.status_code == 200 and r.json()["ok"] is True
        assert time.time() - t < 5
        time.sleep(15)
        assert sa.get(f"{BASE_URL}/api/admin/facebook/auto").json()["last_run"] == prev
        r = sa.put(f"{BASE_URL}/api/admin/facebook/auto", json={"enabled": True})
        assert r.json()["enabled"] is True


class TestDedup:
    def test_cron_runs_no_dup(self, sa):
        before = fb_count()
        prev = sa.get(f"{BASE_URL}/api/admin/facebook/auto").json()["last_run"]
        t = time.time()
        r = cron()
        assert r.status_code == 200 and r.json()["ok"] is True, r.text
        assert time.time() - t < 5, "cron must ack immediately"
        st = wait_run(sa, prev)
        assert st is not None, "cron did not run (last_run not updated)"
        assert st["last_imported"] == 0
        assert fb_count() == before

    def test_manual_import_no_dup(self, sa):
        before = fb_count()
        r = sa.post(f"{BASE_URL}/api/admin/facebook/import", json={"remove_samples": False}, timeout=120)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["imported"] == [] and d["skipped"] >= 1 and d["removed_samples"] == 0
        assert fb_count() == before

    def test_concurrent_no_dup(self, sa):
        before = fb_count()
        cookies = sa.cookies
        def manual():
            return requests.post(f"{BASE_URL}/api/admin/facebook/import", json={}, cookies=cookies, timeout=150)
        with cf.ThreadPoolExecutor(6) as ex:
            futs = [ex.submit(cron) for _ in range(3)] + [ex.submit(manual) for _ in range(2)]
            res = [f.result() for f in futs]
        assert all(r.status_code == 200 for r in res), [r.text for r in res]
        time.sleep(20)
        assert fb_count() == before

    def test_soft_deleted_not_reimported(self, sa):
        a = mongo(lambda db: db.articles.find_one({"fb_post_key": {"$type": "string"}, "deleted": False}, {"_id": 0, "id": 1}))
        mongo(lambda db: db.articles.update_one({"id": a["id"]}, {"$set": {"deleted": True}}))
        try:
            before = fb_count()
            r = sa.post(f"{BASE_URL}/api/admin/facebook/import", json={}, timeout=120)
            assert r.status_code == 200, r.text
            assert r.json()["imported"] == []
            assert fb_count() == before
        finally:
            mongo(lambda db: db.articles.update_one({"id": a["id"]}, {"$set": {"deleted": False}}))


class TestAuthor:
    def test_author_applied_on_reimport(self, sa, journalist):
        u, _ = journalist
        r = sa.put(f"{BASE_URL}/api/admin/facebook/auto", json={"author_id": u["id"]})
        assert r.status_code == 200 and r.json()["author_id"] == u["id"]
        before = fb_count()
        # hard-delete the newest fb article (backup) and re-import
        doc = mongo(lambda db: db.articles.find_one({"fb_post_key": {"$type": "string"}}, {"_id": 0}, sort=[("fb_post_key", -1)]))
        mongo(lambda db: db.articles.delete_one({"id": doc["id"]}))
        try:
            r = sa.post(f"{BASE_URL}/api/admin/facebook/import", json={}, timeout=120)
            assert r.status_code == 200, r.text
            assert len(r.json()["imported"]) == 1, r.json()
            new = mongo(lambda db: db.articles.find_one({"fb_post_key": doc["fb_post_key"]}, {"_id": 0}))
            assert new and new["author_ids"] == [u["id"]], new and new.get("author_ids")
            assert fb_count() == before
        finally:
            cur = mongo(lambda db: db.articles.find_one({"fb_post_key": doc["fb_post_key"]}, {"_id": 1}))
            if not cur:
                mongo(lambda db: db.articles.insert_one(doc))
            else:
                # restore original author so journalist deletion doesn't orphan
                mongo(lambda db: db.articles.update_one({"fb_post_key": doc["fb_post_key"]},
                                                        {"$set": {"author_ids": doc["author_ids"], "author_names": doc.get("author_names")}}))
            sa.put(f"{BASE_URL}/api/admin/facebook/auto", json={"author_id": None})
