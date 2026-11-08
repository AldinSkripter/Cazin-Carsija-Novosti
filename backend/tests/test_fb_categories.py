# FB import auto-categorization (keyword+AI), Obavještenja hidden-from-home category, per-post manual override
import os
import sys
import asyncio
import pytest
import requests
from dotenv import load_dotenv

sys.path.insert(0, "/app/backend")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
NOTICE_KEY, CULT_KEY = "fb-1794127197", "fb-1794118158"
STATE = {}


def mongo(fn):
    from motor.motor_asyncio import AsyncIOMotorClient
    async def run():
        db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
        return await fn(db)
    return asyncio.run(run())


def cat_ids():
    return mongo(lambda db: db.categories.find({}, {"_id": 0, "slug": 1, "id": 1}).to_list(100))


def slug_of(cid):
    return {c["id"]: c["slug"] for c in STATE["cats"]}.get(cid)


async def _cleanup_fb(db):
    arts = [a async for a in db.articles.find({"fb_post_key": {"$exists": True}}, {"id": 1, "featured_image": 1})]
    ids = [a["id"] for a in arts]
    mids = [a["featured_image"]["id"] for a in arts if a.get("featured_image")]
    await db.articles.delete_many({"id": {"$in": ids}})
    await db.article_versions.delete_many({"article_id": {"$in": ids}})
    await db.media.delete_many({"id": {"$in": mids}, "category": "facebook"})
    await db.fb_ignored.delete_many({})
    return len(ids), len(mids)


@pytest.fixture(scope="module")
def s():
    ss = requests.Session()
    r = ss.post(f"{BASE_URL}/api/auth/login", json={"email": "test_fb@ccn.ba", "password": "TestFb12345A"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    STATE["cats"] = cat_ids()
    yield ss
    print("cleanup fb", mongo(_cleanup_fb))
    for aid in STATE.get("test_articles", []):
        mongo(lambda db: db.articles.delete_one({"id": aid}))
        mongo(lambda db: db.article_versions.delete_many({"article_id": aid}))


# --- unit: keyword classification
def test_detect_categories_unit():
    from fb_import import detect_categories
    assert detect_categories("NK Krajišnik pobijedio u utakmici u Bihaću") == ("sport", ["bihac"])
    assert detect_categories("Policija uhapsila osobu u Velikoj Kladuši") == ("hronika", ["velika-kladusa"])
    assert detect_categories("Obavještavamo vas o smrti našeg sugrađanina. Dženaza će biti klanjana u petak.") == ("obavjestenja", [])
    assert detect_categories("Nova cesta u Cazinu") == ("cazin", [])


def test_detect_false_positive_condolence_news():
    # news where politician expresses condolences should not be a death notice
    from fb_import import detect_categories
    r = detect_categories("Načelnik Cazina izrazio saučešće porodicama nakon saobraćajne nesreće")
    print("condolence news ->", r)
    assert r[0] != "obavjestenja", r


# --- category & menu
def test_notices_category_public():
    cats = requests.get(f"{BASE_URL}/api/public/categories").json()
    c = next((c for c in cats if c["slug"] == "obavjestenja"), None)
    assert c and c["name"] == "Obavještenja" and c["hide_from_home"] is True
    menu = requests.get(f"{BASE_URL}/api/public/settings").json()["main_menu"]
    urls = [m["url"] for m in menu]
    i = urls.index("/kategorija/obavjestenja")
    assert urls[i + 1] == "/kamere"
    assert requests.get(f"{BASE_URL}/api/public/articles?category=obavjestenja").status_code == 200


def test_posts_have_category(s):
    r = s.get(f"{BASE_URL}/api/admin/facebook/posts")
    assert r.status_code == 200
    ps = {p["key"]: p for p in r.json()}
    STATE["posts"] = ps
    assert all("category" in p for p in ps.values())
    if NOTICE_KEY in ps:
        assert ps[NOTICE_KEY]["category"] == "obavjestenja"
    if CULT_KEY in ps:
        assert ps[CULT_KEY]["category"] == "kultura"


# --- hidden category articles excluded from home / unfiltered list
def test_hidden_article_flow(s):
    notice = next(c for c in STATE["cats"] if c["slug"] == "obavjestenja")
    r = s.post(f"{BASE_URL}/api/admin/articles", json={"title": "TEST_ Obavijest o smrti test", "summary": "TEST", "body": "<p>TEST dženaza</p>",
                                                     "category_id": notice["id"], "status": "published"})
    assert r.status_code in (200, 201), r.text
    a = r.json()
    STATE.setdefault("test_articles", []).append(a["id"])
    if a.get("status") != "published":
        pr = s.post(f"{BASE_URL}/api/admin/articles/{a['id']}/transition", json={"action": "publish"})
        print("publish", pr.status_code, pr.text[:200])
    art = mongo(lambda db: db.articles.find_one({"id": a["id"]}, {"_id": 0, "status": 1, "category_id": 1, "slug": 1}))
    assert art["status"] == "published", art
    assert art["category_id"] == notice["id"]
    ids_cat = [x["id"] for x in requests.get(f"{BASE_URL}/api/public/articles?category=obavjestenja&limit=50").json()["items"]]
    assert a["id"] in ids_cat
    ids_all = [x["id"] for x in requests.get(f"{BASE_URL}/api/public/articles?limit=50").json()["items"]]
    assert a["id"] not in ids_all
    home = requests.get(f"{BASE_URL}/api/public/home").json()["blocks"]
    for b in home:
        assert a["id"] not in [x["id"] for x in b.get("articles", [])], f"in block {b.get('type')}"
    # popular (most_read-like) also excluded
    ids_pop = [x["id"] for x in requests.get(f"{BASE_URL}/api/public/articles?sort=popular&limit=50").json()["items"]]
    assert a["id"] not in ids_pop
    assert requests.get(f"{BASE_URL}/api/public/articles/{art['slug']}").status_code == 200


# --- FB import with auto classification (AI refinement may be slow)
def test_import_auto_classification(s):
    ps = STATE["posts"]
    keys = [k for k in (NOTICE_KEY, CULT_KEY) if k in ps and ps[k]["status"] == "new"]
    if len(keys) < 2:
        pytest.skip("expected FB posts not available")
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": keys}, timeout=240)
    assert r.status_code == 200, r.text
    assert len(r.json()["imported"]) == 2
    arts = {a["fb_post_key"]: a for a in mongo(lambda db: db.articles.find({"fb_post_key": {"$in": keys}}, {"_id": 0}).to_list(10))}
    n, c = arts[NOTICE_KEY], arts[CULT_KEY]
    print("notice", slug_of(n["category_id"]), [slug_of(x) for x in n.get("category_ids", [])])
    print("culture", slug_of(c["category_id"]), [slug_of(x) for x in c.get("category_ids", [])])
    assert slug_of(n["category_id"]) == "obavjestenja"
    assert slug_of(c["category_id"]) == "kultura"
    assert "cazin" in [slug_of(x) for x in c.get("category_ids", [])]
    # notice hidden from home, culture visible in latest list
    ids_all = [x["id"] for x in requests.get(f"{BASE_URL}/api/public/articles?limit=50").json()["items"]]
    assert n["id"] not in ids_all and c["id"] in ids_all
    ids_cazin = [x["id"] for x in requests.get(f"{BASE_URL}/api/public/articles?category=cazin&limit=50").json()["items"]]
    assert c["id"] in ids_cazin


# --- manual override with valid and invalid slug
def test_import_forced_category(s):
    mongo(_cleanup_fb)
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": [CULT_KEY, NOTICE_KEY],
                                                            "categories": {CULT_KEY: "sport", NOTICE_KEY: "nepostojeca-rubrika"}}, timeout=240)
    assert r.status_code == 200, r.text
    arts = {a["fb_post_key"]: a for a in mongo(lambda db: db.articles.find({"fb_post_key": {"$exists": True}}, {"_id": 0}).to_list(10))}
    assert slug_of(arts[CULT_KEY]["category_id"]) == "sport"
    print("forced sport extras", [slug_of(x) for x in arts[CULT_KEY].get("category_ids", [])])
    assert slug_of(arts[NOTICE_KEY]["category_id"]) == "obavjestenja"  # invalid slug ignored -> auto


def test_import_forced_bad_type(s):
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": [], "categories": "sport"})
    assert r.status_code == 200, r.text
    r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "keys": [], "categories": {CULT_KEY: 5}})
    assert r.status_code == 200, r.text
