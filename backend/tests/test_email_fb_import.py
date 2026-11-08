# Tests: own-profile email change, super_admin user email edit, Facebook import (permissions + skip), imported articles public
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
SA_EMAIL = "test_fb@ccn.ba"
SA_PW = "TestFb12345A"
PW = "TestUser12345A"


def login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    return s, r


@pytest.fixture(scope="module")
def sa():
    s, r = login(SA_EMAIL, SA_PW)
    if r.status_code != 200:
        pytest.skip(f"super admin login failed {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def users(sa):
    created = {}
    for role in ("journalist", "chief_editor"):
        em = f"test_{role}_{uuid.uuid4().hex[:6]}@ccn.ba"
        r = sa.post(f"{BASE_URL}/api/admin/users", json={"name": f"TEST_{role}", "email": em, "password": PW, "role": role,
                                                          "extra_permissions": ["users.manage"] if role == "chief_editor" else []})
        assert r.status_code == 200, r.text
        created[role] = r.json()
    yield created
    for u in created.values():
        sa.delete(f"{BASE_URL}/api/admin/users/{u['id']}")


class TestProfileEmail:
    def test_wrong_password(self, users):
        s, r = login(users["journalist"]["email"], PW)
        assert r.status_code == 200
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"email": "test_new_x@ccn.ba", "current_password": "wrong"})
        assert r.status_code == 400
        assert "ispravnu trenutnu lozinku" in r.json()["detail"]

    def test_missing_password(self, users):
        s, _ = login(users["journalist"]["email"], PW)
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"email": "test_new_y@ccn.ba"})
        assert r.status_code == 400

    def test_duplicate_email(self, users):
        s, _ = login(users["journalist"]["email"], PW)
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"email": SA_EMAIL, "current_password": PW})
        assert r.status_code == 400
        assert "već postoji" in r.json()["detail"]

    def test_invalid_email(self, users):
        s, _ = login(users["journalist"]["email"], PW)
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"email": "notanemail", "current_password": PW})
        assert r.status_code == 400

    def test_change_and_login_new_and_restore(self, users):
        old = users["journalist"]["email"]
        new = f"test_changed_{uuid.uuid4().hex[:6]}@ccn.ba"
        s, _ = login(old, PW)
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"email": new.upper(), "current_password": PW, "name": "TEST_journalist2"})
        assert r.status_code == 200, r.text
        me = s.get(f"{BASE_URL}/api/auth/me").json()
        assert me["email"] == new and me["name"] == "TEST_journalist2"
        _, r_old = login(old, PW)
        assert r_old.status_code == 401
        s2, r_new = login(new, PW)
        assert r_new.status_code == 200
        r = s2.put(f"{BASE_URL}/api/auth/profile", json={"email": old, "current_password": PW})
        assert r.status_code == 200
        assert s2.get(f"{BASE_URL}/api/auth/me").json()["email"] == old

    def test_name_only_no_password_needed(self, users):
        s, _ = login(users["journalist"]["email"], PW)
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"name": "TEST_journalist", "email": users["journalist"]["email"]})
        assert r.status_code == 200

    def test_empty_name_rejected(self, users):
        s, _ = login(users["journalist"]["email"], PW)
        r = s.put(f"{BASE_URL}/api/auth/profile", json={"name": "  "})
        assert r.status_code == 400


class TestAdminUserEmail:
    def test_super_admin_changes_email(self, sa, users):
        u = users["journalist"]
        new = f"test_sa_{uuid.uuid4().hex[:6]}@ccn.ba"
        r = sa.put(f"{BASE_URL}/api/admin/users/{u['id']}", json={"email": new})
        assert r.status_code == 200, r.text
        lst = sa.get(f"{BASE_URL}/api/admin/users").json()
        assert any(x["id"] == u["id"] and x["email"] == new for x in lst)
        assert login(new, PW)[1].status_code == 200
        r = sa.put(f"{BASE_URL}/api/admin/users/{u['id']}", json={"email": u["email"]})
        assert r.status_code == 200

    def test_super_admin_duplicate(self, sa, users):
        r = sa.put(f"{BASE_URL}/api/admin/users/{users['journalist']['id']}", json={"email": SA_EMAIL})
        assert r.status_code == 400

    def test_non_super_admin_403(self, users):
        s, r = login(users["chief_editor"]["email"], PW)
        assert r.status_code == 200
        r = s.put(f"{BASE_URL}/api/admin/users/{users['journalist']['id']}", json={"email": "test_hack@ccn.ba"})
        assert r.status_code == 403, r.text

    def test_non_super_admin_same_email_ok(self, users):
        s, _ = login(users["chief_editor"]["email"], PW)
        r = s.put(f"{BASE_URL}/api/admin/users/{users['journalist']['id']}", json={"email": users["journalist"]["email"], "name": "TEST_journalist"})
        assert r.status_code == 200, r.text


class TestFacebookImport:
    def test_journalist_403(self, users):
        s, _ = login(users["journalist"]["email"], PW)
        r = s.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "remove_samples": False})
        assert r.status_code == 403

    def test_unauth_401(self):
        r = requests.post(f"{BASE_URL}/api/admin/facebook/import", json={})
        assert r.status_code == 401

    def test_import_skips_existing(self, sa):
        r = sa.post(f"{BASE_URL}/api/admin/facebook/import", json={"limit": 8, "remove_samples": False}, timeout=90)
        assert r.status_code in (200, 502), r.text
        if r.status_code == 502:
            pytest.skip("Facebook did not return posts: " + r.text)
        d = r.json()
        print("IMPORT RESULT", d)
        assert d["removed_samples"] == 0
        assert d["skipped"] >= 5
        assert isinstance(d["imported"], list)

    def test_imported_article_public(self):
        r = requests.get(f"{BASE_URL}/api/public/articles/cazin-kroz-umjetnost-i-ljubav-prema-zavicaju")
        assert r.status_code == 200, r.text
        a = r.json()
        assert a["status"] == "published"
        assert a["body"].count("<p>") >= 2
        assert a.get("published_at")
