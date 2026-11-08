# helper for iteration 11 UI test: setup / delete / cleanup TEST category + menu items
import os, sys, json, requests
from pymongo import MongoClient
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env"); load_dotenv("/app/backend/.env")
B = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
s = requests.Session()
assert s.post(f"{B}/api/auth/login", json={"email": "test_fb@ccn.ba", "password": "TestFb12345A"}).status_code == 200
act = sys.argv[1]
if act == "setup":
    c = s.post(f"{B}/api/admin/categories", json={"name": "TEST Rubrika", "show_in_menu": True, "visible": True}).json()
    st = s.get(f"{B}/api/admin/settings").json()
    mm = st["main_menu"] + [{"label": "TEST Rubrika", "url": "/kategorija/test-rubrika"}, {"label": "TEST Ghost", "url": "/kategorija/test-ghost-nepostoji"}]
    s.put(f"{B}/api/admin/settings", json={"main_menu": mm})
    blk = {"id": "TEST_uiblk", "type": "category", "title": "TEST Rubrika", "category_slug": "test-rubrika", "limit": 4, "visible": True, "order": 99}
    mdb.settings.update_one({"key": "homepage"}, {"$push": {"value.draft": blk, "value.published": blk}})
    open("/tmp/testcat.json", "w").write(json.dumps(c)); print("setup", c["id"], c["slug"])
elif act == "delete":
    c = json.load(open("/tmp/testcat.json"))
    print("delete", s.delete(f"{B}/api/admin/categories/{c['id']}").status_code)
elif act == "cleanup":
    urls = ["/kategorija/test-rubrika", "/kategorija/test-ghost-nepostoji"]
    mdb.settings.update_one({"key": "site"}, {"$pull": {"value.main_menu": {"url": {"$in": urls}}}})
    mdb.settings.update_one({"key": "homepage"}, {"$pull": {"value.draft": {"id": "TEST_uiblk"}, "value.published": {"id": "TEST_uiblk"}}})
    c = json.load(open("/tmp/testcat.json")); mdb.categories.delete_one({"id": c["id"]}); print("cleaned")
print([m["url"] for m in requests.get(f"{B}/api/public/settings").json()["main_menu"]])
