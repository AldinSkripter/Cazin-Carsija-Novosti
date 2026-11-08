# Share / OpenGraph endpoints tests (share page, og-image, static og image)
import io
import os
import re
import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def articles():
    r = requests.get(f"{BASE_URL}/api/public/articles?limit=50", timeout=20)
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    return items


def _has_img(a):
    return bool(a.get("social_image") or (a.get("featured_image") or {}).get("large"))


def meta(html, prop):
    m = re.search(rf'<meta (?:property|name)="{re.escape(prop)}" content="([^"]*)"', html)
    return m.group(1) if m else None


# share page meta tags
def test_share_page_meta(articles):
    a = next((x for x in articles if _has_img(x)), articles[0])
    r = requests.get(f"{BASE_URL}/api/share/{a['slug']}", timeout=20, allow_redirects=False)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    h = r.text
    assert meta(h, "og:title")
    assert meta(h, "og:url").endswith(f"/vijesti/{a['slug']}")
    assert "/api/share/" not in meta(h, "og:url")
    assert meta(h, "og:image:width") == "1200"
    assert meta(h, "og:image:height") == "630"
    assert meta(h, "twitter:card") == "summary_large_image"
    assert meta(h, "article:published_time")
    if _has_img(a):
        assert meta(h, "og:image").endswith(f"/api/og-image/{a['slug']}.jpg")
    else:
        assert meta(h, "og:image").endswith("/og-image.jpg")


def test_share_unknown_404():
    r = requests.get(f"{BASE_URL}/api/share/TEST_nonexistent-slug-xyz", timeout=20)
    assert r.status_code == 404


# og-image renderer
def test_og_image_article(articles):
    withimg = [x for x in articles if _has_img(x)]
    if not withimg:
        pytest.skip("no article with image")
    for a in withimg[:3]:
        r = requests.get(f"{BASE_URL}/api/og-image/{a['slug']}.jpg", timeout=40)
        assert r.status_code == 200, (a["slug"], r.status_code, r.text[:200])
        assert r.headers["content-type"] == "image/jpeg"
        im = Image.open(io.BytesIO(r.content))
        assert im.format == "JPEG" and im.size == (1200, 630)


def test_og_image_no_image_article_404(articles):
    noimg = [x for x in articles if not _has_img(x)]
    if not noimg:
        pytest.skip("all articles have images")
    r = requests.get(f"{BASE_URL}/api/og-image/{noimg[0]['slug']}.jpg", timeout=20)
    assert r.status_code == 404


def test_og_image_unknown_404():
    r = requests.get(f"{BASE_URL}/api/og-image/TEST_nonexistent-slug-xyz.jpg", timeout=20)
    assert r.status_code == 404


# static site og image + index.html meta
def test_static_og_image():
    r = requests.get(f"{BASE_URL}/og-image.jpg", timeout=20)
    assert r.status_code == 200
    im = Image.open(io.BytesIO(r.content))
    assert im.format == "JPEG" and im.size == (1200, 630)


def test_index_og_meta():
    r = requests.get(f"{BASE_URL}/", timeout=20)
    assert r.status_code == 200
    assert f'property="og:image" content="{BASE_URL}/og-image.jpg"' in r.text
    assert 'name="twitter:card" content="summary_large_image"' in r.text
