# Newsletter preview / test-send / edit / send-all / cron tests
import os
import time
import uuid
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
EMAIL = "jonuzovicaldin7@gmail.com"
PASSWORD = "Ccnn3qTUHCNwK7!"
SECRET = os.environ["WEBHOOK_CRON_SECRET"]
mdb = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
CREATED = []


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{API}/auth/login", json={"email": EMAIL, "password": PASSWORD}, headers={"Origin": BASE_URL})
    if r.status_code != 200 or r.json().get("requires_2fa"):
        pytest.skip(f"login failed {r.status_code}")
    ses.headers.update({"Origin": BASE_URL, "Referer": BASE_URL + "/admin/newsletter"})
    yield ses
    for cid in CREATED:
        ses.delete(f"{API}/admin/newsletter/campaigns/{cid}")


@pytest.fixture(scope="module")
def camp(s):
    r = s.post(f"{API}/admin/newsletter/campaigns", json={"kind": "weekly"})
    assert r.status_code == 200, r.text
    d = r.json()
    CREATED.append(d["id"])
    assert d["status"] == "draft" and d["kind"] == "weekly" and "_id" not in d
    return d


# Auth required
def test_unauth_endpoints():
    cid = "x"
    for m, p in [("get", f"/admin/newsletter/campaigns/{cid}/preview"), ("put", f"/admin/newsletter/campaigns/{cid}"),
                 ("post", f"/admin/newsletter/campaigns/{cid}/test"), ("post", f"/admin/newsletter/campaigns/{cid}/send"),
                 ("get", "/admin/newsletter/campaigns")]:
        r = getattr(requests, m)(f"{API}{p}", json={})
        assert r.status_code == 401, (p, r.status_code)


# Preview HTML content
def test_preview_html(s, camp):
    r = s.get(f"{API}/admin/newsletter/campaigns/{camp['id']}/preview")
    assert r.status_code == 200
    html = r.json()["html"]
    assert "<!DOCTYPE html>" in html and "logo-email.png" in html and "Odjavi se" in html
    assert "Sedmični pregled" in html and camp["subject"] in html
    assert "Prijavite vijest" in html
    if len(camp["article_ids"]) > 1:
        assert "Još iz pregleda" in html
    assert BASE_URL in html, "base url not resolved to public origin"
    print("articles:", len(camp["article_ids"]))


def test_preview_404(s):
    assert s.get(f"{API}/admin/newsletter/campaigns/nonexistent/preview").status_code == 404


# Edit subject/intro
def test_edit_and_preview_updates(s, camp):
    r = s.put(f"{API}/admin/newsletter/campaigns/{camp['id']}", json={"subject": "TEST_Naslov <b>x</b>", "intro": "TEST_uvod <script>alert(1)</script>"})
    assert r.status_code == 200
    lst = s.get(f"{API}/admin/newsletter/campaigns").json()
    c = next(x for x in lst if x["id"] == camp["id"])
    assert c["subject"].startswith("TEST_Naslov")
    assert "<script>" not in c["intro"]
    html = s.get(f"{API}/admin/newsletter/campaigns/{camp['id']}/preview").json()["html"]
    assert "TEST_Naslov &lt;b&gt;x&lt;/b&gt;" in html
    assert "TEST_uvod" in html and "<script>" not in html


def test_edit_empty_subject(s, camp):
    assert s.put(f"{API}/admin/newsletter/campaigns/{camp['id']}", json={"subject": "  "}).status_code == 400


def test_edit_nonexistent(s):
    assert s.put(f"{API}/admin/newsletter/campaigns/nope", json={"subject": "a"}).status_code in (404, 409)


# Send-all with zero confirmed subscribers
def test_send_all_no_subs(s, camp):
    if mdb.newsletter_subscribers.count_documents({"status": "confirmed"}):
        pytest.skip("real subscribers present")
    if not camp["article_ids"]:
        pytest.skip("no articles")
    r = s.post(f"{API}/admin/newsletter/campaigns/{camp['id']}/send")
    assert r.status_code == 400 and "Nema potvrđenih pretplatnika" in r.text


# Send-all with TEST subscriber, then sent -> edit 409
def test_send_all_with_test_sub_then_edit_409(s):
    if mdb.newsletter_subscribers.count_documents({"status": "confirmed"}):
        pytest.skip("real subscribers present")
    c = s.post(f"{API}/admin/newsletter/campaigns", json={"kind": "weekly", "subject": "TEST_send_all"}).json()
    CREATED.append(c["id"])
    if not c["article_ids"]:
        pytest.skip("no articles")
    sid = "TEST_" + uuid.uuid4().hex
    mdb.newsletter_subscribers.insert_one({"id": sid, "email": f"TEST_{uuid.uuid4().hex[:6]}@example.com", "status": "confirmed",
                                           "frequency": "weekly", "token": uuid.uuid4().hex, "created_at": "2026-01-01T00:00:00"})
    try:
        r = s.post(f"{API}/admin/newsletter/campaigns/{c['id']}/send")
        assert r.status_code == 200, r.text
        r2 = s.post(f"{API}/admin/newsletter/campaigns/{c['id']}/send")
        assert r2.status_code == 409
        for _ in range(20):
            st = mdb.newsletter_campaigns.find_one({"id": c["id"]})["status"]
            if st in ("sent", "failed"):
                break
            time.sleep(1)
        print("final status", st)
        assert st == "sent"
        r3 = s.put(f"{API}/admin/newsletter/campaigns/{c['id']}", json={"subject": "x"})
        assert r3.status_code == 409
    finally:
        mdb.newsletter_subscribers.delete_one({"id": sid})


# Test email (real send) - called once
def test_test_email(s, camp):
    r = s.post(f"{API}/admin/newsletter/campaigns/{camp['id']}/test")
    assert r.status_code == 200, r.text
    assert r.json()["email"] == EMAIL


# Cron auth + idempotency
def test_cron(s):
    assert requests.post(f"{API}/cron/newsletter/weekly", json={}).status_code == 401
    assert requests.post(f"{API}/cron/newsletter/weekly", json={}, headers={"Authorization": "Bearer wrong"}).status_code == 401
    if mdb.newsletter_subscribers.count_documents({"status": "confirmed"}):
        pytest.skip("real subscribers present")
    before = {c["id"] for c in mdb.newsletter_campaigns.find({}, {"id": 1})}
    wid = "TEST_" + uuid.uuid4().hex
    h = {"Authorization": f"Bearer {SECRET}", "X-Webhook-Id": wid}
    r = requests.post(f"{API}/cron/newsletter/weekly", json={}, headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True}
    r = requests.post(f"{API}/cron/newsletter/weekly", json={}, headers=h)
    assert r.status_code == 200 and r.json().get("duplicate") is True
    assert requests.post(f"{API}/cron/newsletter/bogus", json={}, headers={"Authorization": f"Bearer {SECRET}"}).status_code == 400
    time.sleep(3)
    new = [c for c in mdb.newsletter_campaigns.find({}, {"_id": 0}) if c["id"] not in before]
    print("cron created:", [(c["subject"], c["status"], c["created_by"]) for c in new])
    for c in new:
        CREATED.append(c["id"])
    mdb.cron_runs.delete_one({"_id": f"nl:{wid}"})
