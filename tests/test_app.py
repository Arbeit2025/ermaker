import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as app_module  # noqa: E402

SAMPLE = "users(id PK, name, email)\nposts(id PK, user_id FK->users.id, title, body)"


class ParserTest(unittest.TestCase):
    def test_parse_tables(self):
        tables, errors = app_module.parse_definitions(SAMPLE)
        self.assertEqual(errors, [])
        self.assertEqual([t["name"] for t in tables], ["users", "posts"])
        users = tables[0]
        self.assertEqual([c["name"] for c in users["columns"]], ["id", "name", "email"])
        self.assertTrue(users["columns"][0]["pk"])
        self.assertFalse(users["columns"][1]["pk"])

    def test_parse_fk(self):
        tables, errors = app_module.parse_definitions(SAMPLE)
        self.assertEqual(errors, [])
        posts = tables[1]
        fk_col = posts["columns"][1]
        self.assertEqual(fk_col["name"], "user_id")
        self.assertEqual(fk_col["fk"], ("users", "id"))

    def test_parse_bad_input(self):
        tables, errors = app_module.parse_definitions("これは定義ではない\nusers(id PK)")
        self.assertEqual(len(errors), 1)
        self.assertEqual([t["name"] for t in tables], ["users"])

    def test_parse_bad_column_token(self):
        tables, errors = app_module.parse_definitions("users(id XX)")
        self.assertEqual(len(errors), 1)
        self.assertEqual(tables, [])

    def test_parse_empty(self):
        tables, errors = app_module.parse_definitions("")
        self.assertEqual(tables, [])
        self.assertEqual(errors, [])


class PageTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "ok")

    def test_index_has_sample_diagram(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("かんたんER図メーカー", body)
        self.assertIn("<svg", body)
        self.assertIn("users", body)
        self.assertIn("posts", body)

    def test_post_renders_svg(self):
        res = self.client.post("/", data={"definitions": SAMPLE})
        body = res.get_data(as_text=True)
        self.assertIn("<svg", body)
        self.assertIn("<line", body)
        self.assertIn("読み取ったテーブル", body)

    def test_post_bad_input_friendly_error(self):
        res = self.client.post("/", data={"definitions": "でたらめな入力"})
        self.assertEqual(res.status_code, 200)
        body = res.get_data(as_text=True)
        self.assertIn("解釈できない行がありました", body)


if __name__ == "__main__":
    unittest.main()
