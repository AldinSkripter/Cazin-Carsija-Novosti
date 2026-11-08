# Category delete/rename -> menu + homepage block cleanup (iteration 11)
import os
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
EMAIL, PW = "test_fb@ccn.ba", "TestFb12345A"
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json={"email": EMAIL, "password": PW})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text}")
    return ses


def add_links(s, slug, label):
    st = s.get(f"{BASE_URL}/api/admin/settings").json()
    mm = st.get("main_menu") or []
    fm = st.get("footer_menu") or []
    url = f"/kategorija/{slug}"
    r = s.put(f"{BASE_URL}/api/admin/settings", json={"main_menu": mm + [{"label": label, "url": url}],
                                                     "footer_menu": fm + [{"label": label, "url": url}]})
    assert r.status_code == 200
    bid = "TEST_" + uuid.uuid4().hex[:8]
    blk = {"id": bid, "type": "category", "title": label, "category_slug": slug, "limit": 4, "visible": True, "order": 99, "dedupe": True}
    mdb.settings.update_one({"key": "homepage"}, {"$push": {"value.draft": blk, "value.published": blk}})
    return bid


def menu_urls(key="main_menu"):
    return [m.get("url") for m in requests.get(f"{BASE_URL}/api/public/settings").json().get(key) or []]


def block_slugs():
    v = mdb.settings.find_one({"key": "homepage"})["value"]
    return [b.get("category_slug") for k in ("draft", "published") for b in v.get(k) or []]


def cleanup(slugs, cid=None):
    urls = [f"/kategorija/{x}" for x in slugs]
    mdb.settings.update_one({"key": "site"}, {"$pull": {"value.main_menu": {"url": {"$in": urls}}, "value.footer_menu": {"url": {"$in": urls}}}})
    mdb.settings.update_one({"key": "homepage"}, {"$pull": {"value.draft": {"category_slug": {"$in": slugs}}, "value.published": {"category_slug": {"$in": slugs}}}})
    if cid:
        mdb.categories.delete_one({"id": cid})


class TestDelete:
    def test_delete_removes_menu_and_block(self, s):
        r = s.post(f"{BASE_URL}/api/admin/categories", json={"name": "TEST Rubrika", "show_in_menu": True, "visible": True})
        assert r.status_code == 200, r.text
        cat = r.json()
        try:
            assert cat["slug"] == "test-rubrika"
            add_links(s, "test-rubrika", "TEST Rubrika")
            assert "/kategorija/test-rubrika" in menu_urls()
            assert "test-rubrika" in block_slugs()
            assert requests.get(f"{BASE_URL}/api/public/home").status_code == 200
            d = s.delete(f"{BASE_URL}/api/admin/categories/{cat['id']}")
            assert d.status_code == 200
            assert "/kategorija/test-rubrika" not in menu_urls()
            assert "/kategorija/test-rubrika" not in menu_urls("footer_menu")
            assert "test-rubrika" not in block_slugs()
            h = requests.get(f"{BASE_URL}/api/public/home")
            assert h.status_code == 200
            assert requests.get(f"{BASE_URL}/api/public/articles?category=test-rubrika").status_code == 404
            assert s.delete(f"{BASE_URL}/api/admin/categories/{cat['id']}").status_code == 404
        finally:
            cleanup(["test-rubrika"], cat["id"])

    def test_home_ok_with_dangling_block(self, s):
        # block referencing missing category must not break home
        blk = {"id": "TEST_dangle", "type": "category", "title": "x", "category_slug": "test-nepostoji", "limit": 4, "visible": True, "order": 99}
        mdb.settings.update_one({"key": "homepage"}, {"$push": {"value.published": blk}})
        try:
            r = requests.get(f"{BASE_URL}/api/public/home")
            assert r.status_code == 200
        finally:
            cleanup(["test-nepostoji"])


class TestRename:
    def test_rename_updates_links_and_old_slug(self, s):
        r = s.post(f"{BASE_URL}/api/admin/categories", json={"name": "TEST Stara", "show_in_menu": True, "visible": True})
        assert r.status_code == 200, r.text
        cat = r.json()
        try:
            add_links(s, "test-stara", "TEST Stara")
            u = s.put(f"{BASE_URL}/api/admin/categories/{cat['id']}", json={"name": "TEST Nova", "slug": "test-nova"})
            assert u.status_code == 200, u.text
            assert u.json()["slug"] == "test-nova"
            assert "test-stara" in u.json()["old_slugs"]
            st = requests.get(f"{BASE_URL}/api/public/settings").json()
            item = [m for m in st["main_menu"] if m["url"] == "/kategorija/test-nova"]
            assert item and item[0]["label"] == "TEST Nova"
            assert "/kategorija/test-stara" not in menu_urls()
            assert "test-nova" in block_slugs() and "test-stara" not in block_slugs()
            assert requests.get(f"{BASE_URL}/api/public/articles?category=test-stara").status_code == 200
            assert requests.get(f"{BASE_URL}/api/public/articles?category=test-nova").status_code == 200
            assert requests.get(f"{BASE_URL}/api/public/home").status_code == 200
            cats = requests.get(f"{BASE_URL}/api/public/categories").json()
            assert any(c["slug"] == "test-nova" and "test-stara" in (c.get("old_slugs") or []) for c in cats)
            # rename back to original slug -> old slug should not include current
            u2 = s.put(f"{BASE_URL}/api/admin/categories/{cat['id']}", json={"name": "TEST Stara", "slug": "test-stara"})
            assert u2.status_code == 200
            assert "test-stara" not in u2.json()["old_slugs"] and "test-nova" in u2.json()["old_slugs"]
            assert "/kategorija/test-stara" in menu_urls()
            # delete -> all slugs removed
            assert s.delete(f"{BASE_URL}/api/admin/categories/{cat['id']}").status_code == 200
            assert not any(x in menu_urls() for x in ("/kategorija/test-stara", "/kategorija/test-nova"))
            assert not any(x in block_slugs() for x in ("test-stara", "test-nova"))
        finally:
            cleanup(["test-stara", "test-nova"], cat["id"])

    def test_bih_state(self):
        cats = requests.get(f"{BASE_URL}/api/public/categories").json()
        bih = [c for c in cats if c["slug"] == "bih"]
        assert bih and "bosna-i-hercegovina" in bih[0].get("old_slugs", [])
        assert requests.get(f"{BASE_URL}/api/public/articles?category=bosna-i-hercegovina").status_code == 200
        assert "/kategorija/bih" in menu_urls()
        assert "/kategorija/bosna-i-hercegovina" not in menu_urls()

    def test_duplicate_slug_rejected(self, s):
        r = s.post(f"{BASE_URL}/api/admin/categories", json={"name": "BiH"})
        if r.status_code == 200:
            mdb.categories.delete_one({"id": r.json()["id"]})
        assert r.status_code == 400
