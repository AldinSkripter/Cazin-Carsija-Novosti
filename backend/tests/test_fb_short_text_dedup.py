# Tests: FB dedup for short identical texts (death notices) - post_hash None for short text, key-based dedup
import os, time, sys
import pytest, requests
sys.path.insert(0, "/app/backend/tests")
from test_fb_auto_import import mongo, SECRET, SA_EMAIL, SA_PW, CRON

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
DEATH = "obavještavamo vas o smrti"


def _last_run():
    d = mongo(lambda db: db.settings.find_one({"key": "fb_auto"}, {"_id": 0})) or {}
    return (d.get("value") or {}).get("last_run")


def cron(wait=150):
    """Trigger cron (background job) and poll fb_auto.last_run until the job finishes."""
    before = _last_run()
    r = requests.post(CRON, headers={"Authorization": f"Bearer {SECRET}"}, json={}, timeout=60)
    t = time.time()
    while time.time() - t < wait and _last_run() == before:
        time.sleep(3)
    print("cron done in", round(time.time() - t), "s", r.text)
    return r


@pytest.fixture(scope="module")
def sa():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": SA_EMAIL, "password": SA_PW})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.text}")
    return s


def fb_articles():
    return mongo(lambda db: db.articles.find({"fb_post_key": {"$type": "string"}},
                                             {"_id": 0, "id": 1, "title": 1, "fb_post_key": 1, "fb_post_hash": 1, "category_id": 1, "slug": 1, "deleted": 1}).to_list(100))


def posts(sa):
    r = sa.get(f"{BASE_URL}/api/admin/facebook/posts", timeout=120)
    assert r.status_code == 200, r.text
    return r.json()


def death_posts(ps):
    return [p for p in ps if DEATH in ((p.get("title") or "") + " " + (p.get("summary") or "")).lower()]


class TestShortTextDedup:
    def test_01_unit_post_hash(self):
        sys.path.insert(0, "/app/backend")
        from dotenv import load_dotenv
        load_dotenv("/app/backend/.env")
        from fb_import import post_hash
        assert post_hash("„Obavještavamo vas o smrti") is None
        assert isinstance(post_hash("a" * 100), str)

    def test_02_feed_has_two_death_notices_new(self, sa):
        ps = posts(sa)
        print([(p["key"], p["title"][:40], p["status"], p["suggested"], p["category"]) for p in ps])
        d = death_posts(ps)
        assert len(d) == 2, d
        assert d[0]["key"] != d[1]["key"]
        assert all(p["status"] == "new" for p in d), d

    def test_03_cron_imports_both(self, sa):
        r = cron()
        print(r.status_code, r.text[:500])
        assert r.status_code == 200
        arts = fb_articles()
        print(arts)
        ob = mongo(lambda db: db.categories.find_one({"slug": "obavjestenja"}, {"_id": 0, "id": 1}))
        deaths = [a for a in arts if a["category_id"] == ob["id"]]
        assert len(deaths) == 2
        assert deaths[0]["id"] != deaths[1]["id"] and deaths[0]["fb_post_key"] != deaths[1]["fb_post_key"]
        assert all(a.get("fb_post_hash") is None for a in deaths)
        assert any("velike vijesti" in a["title"].lower() for a in arts)

    def test_04_public_listing(self):
        r = requests.get(f"{BASE_URL}/api/public/articles", params={"category": "obavjestenja"})
        assert r.status_code == 200
        data = r.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        print(len(items), [i.get("title") for i in items])
        assert len(items) == 2
        home = requests.get(f"{BASE_URL}/api/public/home").text.lower()
        keys = {a["slug"] for a in fb_articles() if DEATH in a["title"].lower()}
        for s in keys:
            assert s not in home, f"death notice {s} on home"

    def test_05_status_imported(self, sa):
        d = death_posts(posts(sa))
        assert all(p["status"] == "imported" for p in d), d

    def test_06_cron_again_no_dupes(self):
        before = len(fb_articles())
        r = cron()
        assert r.status_code == 200, r.text
        print(r.text[:300])
        assert len(fb_articles()) == before

    def test_07_hard_delete_one_shows_new(self, sa):
        d = death_posts(posts(sa))
        k = d[0]["key"]
        mongo(lambda db: db.articles.delete_one({"fb_post_key": k}))
        st = {p["key"]: p["status"] for p in death_posts(posts(sa))}
        print(st)
        assert st[k] == "new"
        assert st[d[1]["key"]] == "imported"
        # re-import via cron restores it
        assert cron().status_code == 200
        st = {p["key"]: p["status"] for p in death_posts(posts(sa))}
        assert st[k] == "imported"
