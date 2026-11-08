"""Offline checks for the article deletion route and linked breaking news."""
import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


class NotFound(Exception):
    def __init__(self, status, message):
        self.status_code = status


class ArticleDeleteTests(unittest.TestCase):
    def route(self, article):
        source = Path(__file__).resolve().parents[1] / "routes_articles.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "delete")
        self.assertIn('require(\'articles.delete\')', ast.unparse(function.args.defaults[0]))
        function.decorator_list = []
        function.args.defaults = [ast.Constant(value=None)]
        articles = SimpleNamespace(find_one=AsyncMock(return_value=article), update_one=AsyncMock())
        breaking = SimpleNamespace(update_many=AsyncMock())
        audit = AsyncMock()
        scope = dict(db=SimpleNamespace(articles=articles, breaking_news=breaking), iso=lambda: "now", audit=audit, HTTPException=NotFound)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(source), "exec"), scope)
        return scope["delete"], articles, breaking, audit

    def test_published_article_removed_and_breaking_disabled(self):
        delete, articles, breaking, audit = self.route({"title": "Vijest", "was_published": True})
        user = {"id": "admin"}
        self.assertEqual(asyncio.run(delete("article-1", user)), {"ok": True})
        articles.find_one.assert_awaited_once_with({"id": "article-1", "deleted": {"$ne": True}}, {"title": 1, "was_published": 1})
        articles.update_one.assert_awaited_once_with({"id": "article-1"}, {"$set": {"deleted": True, "deleted_at": "now", "status": "archived"}})
        breaking.update_many.assert_awaited_once_with({"article_id": "article-1"}, {"$set": {"active": False}})
        audit.assert_awaited_once_with(user, "article.delete", "article", "article-1", "Vijest")

    def test_missing_or_already_deleted_article(self):
        delete, articles, breaking, audit = self.route(None)
        with self.assertRaises(NotFound) as error:
            asyncio.run(delete("missing", {"id": "admin"}))
        self.assertEqual(error.exception.status_code, 404)
        articles.update_one.assert_not_awaited()
        breaking.update_many.assert_not_awaited()
        audit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
