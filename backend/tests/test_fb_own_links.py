"""Offline regression tests for shared portal links."""
import sys
import unittest
import ast
import asyncio
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fb_links import own_site_link


class OwnLinkTests(unittest.TestCase):
    def test_own_links(self):
        for post in [
            {"message": "Procitajte https://cazin-carsija.ba/vijest/test?fbclid=123"},
            {"message": "WWW.CAZIN-CARSIJA.BA/vijest/test"},
            {"attachments": [{"target": {"url": "https://www.cazin-carsija.ba/vijest/test"}}]},
            {"url": "https://l.facebook.com/l.php?u=https%3A%2F%2Fcazin-carsija.ba%2Fvijest%2Ftest&h=123"},
            {"link_metadata": {"attachment": {"url": "https://cazin-carsija.ba/test"}}},
        ]:
            with self.subTest(post=post):
                self.assertTrue(own_site_link(post, ["https://cazin-carsija.ba"]))

    def test_original_and_external_posts(self):
        for message in ["Nova vijest iz Cazina", "https://example.com/vijest", "https://cazin-carsija.ba.evil.com/test", "https://fake-cazin-carsija.ba/test"]:
            with self.subTest(message=message):
                self.assertFalse(own_site_link({"message": message}, ["https://cazin-carsija.ba"]))
        self.assertFalse(own_site_link({"photoURL": "https://cazin-carsija.ba/image.jpg"}, ["https://cazin-carsija.ba"]))

    def test_configured_domain(self):
        self.assertTrue(own_site_link({"message": "https://portal.example/news"}, [None, "https://www.portal.example/"]))

    def test_import_blocks_even_manual_selection(self):
        # Execute the actual import function with offline dependencies.
        tree = ast.parse((Path(__file__).resolve().parents[1] / "fb_import.py").read_text(encoding="utf-8"))
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "run_import")
        for keys in (None, {"fb-123"}):
            articles = SimpleNamespace(insert_one=AsyncMock())
            scope = dict(
                IMPORT_LOCK=asyncio.Lock(), get_settings=AsyncMock(return_value={}),
                fetch_posts=AsyncMock(return_value=[{"message": "https://cazin-carsija.ba/vijest/test", "createdTime": 123}]),
                own_site_link=own_site_link, os=os, datetime=datetime, timezone=timezone,
                db=SimpleNamespace(articles=articles, settings=SimpleNamespace(update_one=AsyncMock())),
                iso=lambda: "now", audit=AsyncMock(),
            )
            exec(compile(ast.Module(body=[function], type_ignores=[]), "fb_import.py", "exec"), scope)
            result = asyncio.run(scope["run_import"]({"id": "tester"}, keys=keys))
            self.assertEqual(result["skipped"], 1)
            self.assertEqual(result["imported"], [])
            articles.insert_one.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
