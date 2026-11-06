# Regression tests for Cazin Čaršija Novosti: auth, RBAC workflow, scheduling, versions, media, ads, cameras, comments,
# submissions, newsletter, settings/backup/audit, SEO endpoints, 2FA setup, AI summary.
import io
import os
import time
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = {"email": "jonuzovicaldin7@gmail.com", "password": "Ccnn3qTUHCNwK7!"}
PW = "TestPass123!"
RUN = uuid.uuid4().hex[:6]
STATE = {"users": [], "articles": [], "campaigns": [], "cameras": [], "breaking": [], "media": []}


def login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return s


def png_bytes(color=(200, 30, 30)):
    b = io.BytesIO()
    Image.new("RGB", (900, 600), color).save(b, "PNG")
    return b.getvalue()


@pytest.fixture(scope="module")
def admin():
    return login(**ADMIN)


@pytest.fixture(scope="module")
def category_id():
    cats = requests.get(f"{BASE_URL}/api/public/categories").json()
    return next(c["id"] for c in cats if c["slug"] == "cazin")


@pytest.fixture(scope="module")
def users(admin):
    out = {}
    for role, extra in (("journalist", []), ("editor", []), ("author", ["articles.publish"]), ("marketing", [])):
        email = f"test_{role}_{RUN}@example.com"
        r = admin.post(f"{BASE_URL}/api/admin/users", json={"name": f"TEST_{role}", "email": email, "password": PW,
                                                             "role": role, "extra_permissions": extra})
        assert r.status_code == 200, r.text
        STATE["users"].append(r.json()["id"])
        out[role] = login(email, PW)
    return out


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    s = login(**ADMIN)
    for aid in STATE["articles"]:
        s.delete(f"{BASE_URL}/api/admin/articles/{aid}")
    for cid in STATE["campaigns"]:
        s.delete(f"{BASE_URL}/api/admin/campaigns/{cid}")
    for cid in STATE["cameras"]:
        s.delete(f"{BASE_URL}/api/admin/cameras/{cid}")
    for bid in STATE["breaking"]:
        s.delete(f"{BASE_URL}/api/admin/breaking/{bid}")
    for mid in STATE["media"]:
        s.delete(f"{BASE_URL}/api/admin/media/{mid}?force=true")
    for uid in STATE["users"]:
        s.delete(f"{BASE_URL}/api/admin/users/{uid}")


def new_article(sess, cat, title=None, **kw):
    body = {"title": title or f"TEST_ Članak {RUN} {uuid.uuid4().hex[:4]}", "category_id": cat,
            "body": "<p>Tekst o Bihaću i čaršiji u Cazinu. Dovoljno dug tekst za test.</p>", **kw}
    r = sess.post(f"{BASE_URL}/api/admin/articles", json=body)
    assert r.status_code == 200, r.text
    STATE["articles"].append(r.json()["id"])
    return r.json()


def tr(sess, aid, action, **kw):
    return sess.post(f"{BASE_URL}/api/admin/articles/{aid}/transition", json={"action": action, **kw})


# --- Auth ---
class TestAuth:
    def test_unauth_admin_401(self):
        assert requests.get(f"{BASE_URL}/api/admin/dashboard").status_code == 401
        assert requests.get(f"{BASE_URL}/api/admin/articles").status_code == 401

    def test_login_cookies_and_me(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login", json=ADMIN)
        assert r.status_code == 200
        sc = r.headers.get("set-cookie", "").lower()
        assert "access_token" in sc and "httponly" in sc and "secure" in sc
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert me["role"] == "super_admin" and "password_hash" not in me
        d = s.get(f"{BASE_URL}/api/admin/dashboard")
        assert d.status_code == 200

    def test_cors_credentials(self):
        r = requests.options(f"{BASE_URL}/api/auth/me", headers={"Origin": BASE_URL, "Access-Control-Request-Method": "GET"})
        assert r.headers.get("access-control-allow-origin") in (BASE_URL, None) or r.headers.get("access-control-allow-origin") != "*"
        print("CORS:", r.headers.get("access-control-allow-origin"), r.headers.get("access-control-allow-credentials"))

    def test_bruteforce_lockout(self):
        email = f"nobody_{RUN}@example.com"
        codes = [requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "Wrong12345X"}).status_code for _ in range(6)]
        assert codes[:5] == [401] * 5 and codes[5] == 429, codes

    def test_2fa_setup_qr(self, users):
        r = users["journalist"].post(f"{BASE_URL}/api/auth/2fa/setup")
        assert r.status_code == 200 and r.json()["qr"].startswith("data:image/png;base64,")


# --- Article workflow / RBAC ---
class TestWorkflow:
    def test_journalist_cannot_publish_can_submit(self, users, category_id, admin):
        a = new_article(users["journalist"], category_id)
        assert a["status"] == "draft"
        assert tr(users["journalist"], a["id"], "publish").status_code == 403
        r = tr(users["journalist"], a["id"], "submit")
        assert r.status_code == 200 and r.json()["status"] == "review"
        # editor reject requires reason
        assert tr(users["editor"], a["id"], "reject").status_code == 400
        r = tr(users["editor"], a["id"], "reject", reason="TEST razlog")
        assert r.status_code == 200 and r.json()["status"] == "rejected"
        assert tr(users["journalist"], a["id"], "submit").json()["status"] == "review"
        assert tr(users["editor"], a["id"], "approve").json()["status"] == "approved"
        r = tr(users["editor"], a["id"], "publish")
        assert r.status_code == 200 and r.json()["status"] == "published", r.text
        pub = requests.get(f"{BASE_URL}/api/public/articles/{a['slug']}")
        assert pub.status_code == 200 and pub.json()["article"]["title"] == a["title"] if "article" in pub.json() else pub.json()["title"] == a["title"]
        STATE["published"] = a

    def test_folded_search(self):
        a = STATE["published"]
        for q in ("Bihać", "bihac", "čaršiji", "carsiji"):
            items = requests.get(f"{BASE_URL}/api/public/articles", params={"q": q, "limit": 50}).json()["items"]
            assert any(i["id"] == a["id"] for i in items), q

    def test_author_with_extra_publish(self, users, category_id):
        a = new_article(users["author"], category_id)
        r = tr(users["author"], a["id"], "publish")
        assert r.status_code == 200 and r.json()["status"] == "published", r.text

    def test_scheduled_publish(self, users, category_id):
        a = new_article(users["editor"], category_id)
        when = (datetime.now(timezone.utc) + timedelta(seconds=20)).isoformat()
        r = tr(users["editor"], a["id"], "publish", publish_at=when)
        assert r.status_code == 200 and r.json()["status"] == "scheduled"
        time.sleep(37)
        requests.get(f"{BASE_URL}/api/public/articles?limit=1")
        time.sleep(1)
        st = users["editor"].get(f"{BASE_URL}/api/admin/articles/{a['id']}").json()["status"]
        if st != "published":
            time.sleep(16)
            requests.get(f"{BASE_URL}/api/public/articles?limit=1")
            st = users["editor"].get(f"{BASE_URL}/api/admin/articles/{a['id']}").json()["status"]
        assert st == "published"

    def test_versions_restore_duplicate(self, users, category_id):
        s = users["editor"]
        a = new_article(s, category_id)
        upd = {**{k: a.get(k) for k in ("title", "category_id", "body")}, "subtitle": "TEST_ izmjena"}
        assert s.put(f"{BASE_URL}/api/admin/articles/{a['id']}", json=upd).status_code == 200
        vs = s.get(f"{BASE_URL}/api/admin/articles/{a['id']}/versions").json()
        assert len(vs) >= 2
        first = vs[-1]
        assert s.post(f"{BASE_URL}/api/admin/articles/{a['id']}/versions/{first['id']}/restore").status_code == 200
        assert s.get(f"{BASE_URL}/api/admin/articles/{a['id']}").json()["subtitle"] == ""
        d = s.post(f"{BASE_URL}/api/admin/articles/{a['id']}/duplicate")
        assert d.status_code == 200
        STATE["articles"].append(d.json()["id"])
        assert "(kopija)" in s.get(f"{BASE_URL}/api/admin/articles/{d.json()['id']}").json()["title"]


# --- Media ---
class TestMedia:
    def test_upload_webp_alt_delete_blocked(self, users, category_id):
        s = users["editor"]
        r = s.post(f"{BASE_URL}/api/admin/media", files=[("files", ("test_img.png", png_bytes(), "image/png"))])
        assert r.status_code == 200, r.text
        m = r.json()[0] if isinstance(r.json(), list) else r.json()["items"][0]
        STATE["media"].append(m["id"])
        print("MEDIA:", {k: v for k, v in m.items() if k != "search"})
        assert ".webp" in str(m)
        assert s.put(f"{BASE_URL}/api/admin/media/{m['id']}", json={"alt": "TEST_ alt"}).status_code == 200
        new_article(s, category_id, featured_image=m)
        assert s.delete(f"{BASE_URL}/api/admin/media/{m['id']}").status_code == 409


# --- Ads / breaking / cameras ---
class TestAdsEtc:
    def test_ad_campaign_click(self, admin, users):
        r = admin.post(f"{BASE_URL}/api/admin/campaigns", json={"name": "TEST_ kampanja", "position": "sidebar", "type": "image",
                       "image_url": "https://picsum.photos/300/250", "target_url": "https://example.com", "active": True, "weight": 100})
        assert r.status_code == 200
        cid = r.json()["id"]
        STATE["campaigns"].append(cid)
        ads = requests.get(f"{BASE_URL}/api/public/ads", params={"positions": "sidebar"}).json()
        assert "sidebar" in ads
        c = requests.get(f"{BASE_URL}/api/public/ads/{cid}/click", allow_redirects=False)
        assert c.status_code == 302 and c.headers["location"] == "https://example.com"
        lst = admin.get(f"{BASE_URL}/api/admin/campaigns").json()
        assert next(x for x in lst if x["id"] == cid)["clicks"] == 1
        h = users["marketing"].post(f"{BASE_URL}/api/admin/campaigns", json={"name": "TEST_ html", "type": "html", "html_code": "<b>x</b>"})
        assert h.status_code == 403

    def test_breaking_ticker(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/breaking", json={"title": f"TEST_ breaking {RUN}", "active": True, "priority": 9})
        assert r.status_code == 200
        STATE["breaking"].append(r.json()["id"])
        b = requests.get(f"{BASE_URL}/api/public/breaking").json()
        assert any(f"TEST_ breaking {RUN}" == x.get("title") for x in b)

    def test_cameras_crud(self, admin):
        r = admin.post(f"{BASE_URL}/api/admin/cameras", json={"name": "TEST_ kamera", "image_url": "https://picsum.photos/640/360",
                                                              "refresh_seconds": 60, "active": True, "order": 99})
        assert r.status_code == 200
        cid = r.json()["id"]
        STATE["cameras"].append(cid)
        assert admin.put(f"{BASE_URL}/api/admin/cameras/{cid}", json={"name": "TEST_ kamera 2"}).json()["name"] == "TEST_ kamera 2"
        assert admin.post(f"{BASE_URL}/api/admin/cameras", json={"name": "x", "image_url": "ftp://x"}).status_code == 400
        img = requests.get(f"{BASE_URL}/api/public/cameras/{cid}/image")
        assert img.status_code == 200 and img.headers["content-type"].startswith("image")

    def test_seeded_camera_images(self):
        cams = requests.get(f"{BASE_URL}/api/public/cameras").json()
        res = {c["name"]: requests.get(f"{BASE_URL}/api/public/cameras/{c['id']}/image").status_code for c in cams}
        print("CAMS:", res)
        assert any(v == 200 for v in res.values())


# --- Comments / submissions / newsletter ---
class TestPublicForms:
    def test_comment_moderation(self, admin):
        a = STATE["published"]
        r = requests.post(f"{BASE_URL}/api/public/articles/{a['id']}/comments", json={"name": "TEST_ Čitalac", "content": "TEST komentar odlično"})
        assert r.status_code == 200 and r.json()["status"] == "pending", r.text
        pend = admin.get(f"{BASE_URL}/api/admin/comments", params={"status": "pending"}).json()
        pend = pend.get("items", pend) if isinstance(pend, dict) else pend
        c = next(x for x in pend if x["article_id"] == a["id"])
        m = admin.post(f"{BASE_URL}/api/admin/comments/{c['id']}/moderate", json={"action": "approved"})
        assert m.status_code == 200, m.text
        vis = requests.get(f"{BASE_URL}/api/public/articles/{a['id']}/comments").json()
        assert any(x["id"] == c["id"] for x in vis)

    def test_submit_news_to_draft(self, admin):
        bad = requests.post(f"{BASE_URL}/api/public/submit-news", data={"name": "TEST_", "contact": "t@e.com", "title": "TEST_ prijava",
                            "description": "x" * 30})
        assert bad.status_code == 400
        r = requests.post(f"{BASE_URL}/api/public/submit-news", data={"name": "TEST_ Građanin", "contact": "t@example.com",
                          "title": f"TEST_ prijava {RUN}", "description": "Opis prijavljene vijesti dovoljno dug.", "consent_data": "true",
                          "consent_rights": "true"})
        assert r.status_code == 200, r.text
        subs = admin.get(f"{BASE_URL}/api/admin/submissions").json()
        s = next(x for x in subs if x["title"] == f"TEST_ prijava {RUN}")
        d = admin.post(f"{BASE_URL}/api/admin/submissions/{s['id']}/to-draft")
        assert d.status_code == 200, d.text
        if d.json().get("id"):
            STATE["articles"].append(d.json()["id"])
        print("TO DRAFT:", d.json())

    def test_newsletter(self, admin):
        assert requests.post(f"{BASE_URL}/api/public/newsletter/subscribe", json={"email": "delivered@resend.dev"}).status_code == 400
        r = requests.post(f"{BASE_URL}/api/public/newsletter/subscribe", json={"email": "delivered@resend.dev", "consent": True},
                          headers={"Origin": BASE_URL})
        assert r.status_code == 200
        print("NL:", r.json())
        subs = admin.get(f"{BASE_URL}/api/admin/newsletter/subscribers").json()
        assert any(x["email"] == "delivered@resend.dev" for x in subs)


# --- Settings / backup / audit / SEO / AI ---
class TestSystem:
    def test_settings_backup_audit(self, admin):
        s = admin.get(f"{BASE_URL}/api/admin/settings")
        assert s.status_code == 200
        assert admin.put(f"{BASE_URL}/api/admin/settings", json=s.json()).status_code == 200
        b = admin.get(f"{BASE_URL}/api/admin/backup")
        assert b.status_code == 200 and isinstance(b.json(), dict)
        # NOTE: backup intentionally contains users incl. password_hash (needed for restore) - reported as security note
        assert "_meta" in b.json()
        a = admin.get(f"{BASE_URL}/api/admin/audit").json()
        assert len(a.get("items", a)) > 0

    def test_editor_cannot_manage_users(self, users):
        assert users["editor"].get(f"{BASE_URL}/api/admin/users").status_code == 403
        assert users["journalist"].get(f"{BASE_URL}/api/admin/settings").status_code == 403

    def test_seo_endpoints(self):
        for p, needle in (("sitemap.xml", "<urlset"), ("news-sitemap.xml", "<urlset"), ("rss.xml", "<rss"), ("robots.txt", "Sitemap")):
            r = requests.get(f"{BASE_URL}/api/{p}")
            assert r.status_code == 200 and needle in r.text, p
        slug = STATE["published"]["slug"]
        r = requests.get(f"{BASE_URL}/api/share/{slug}")
        assert r.status_code == 200 and 'og:title' in r.text
        assert requests.get(f"{BASE_URL}/api/public/articles/unknown-xyz").status_code == 404

    def test_ai_summary(self, users):
        r = users["editor"].post(f"{BASE_URL}/api/admin/ai/summary", json={"text": "Gradsko vijeće Cazina usvojilo je budžet za 2026. godinu. " * 5}, timeout=90)
        print("AI:", r.status_code, r.text[:300])
        assert r.status_code == 200 and len(r.json()["result"]) > 10

    def test_logout_all(self, users):
        s = users["marketing"]
        assert s.post(f"{BASE_URL}/api/auth/logout-all").status_code == 200
        assert s.get(f"{BASE_URL}/api/auth/me").status_code == 401
