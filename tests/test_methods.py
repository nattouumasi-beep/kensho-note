"""Regression tests for low-effort giveaway filters; no web access needed."""
import importlib.util
import pathlib
import unittest

MODULE = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "update_feed.py"
spec = importlib.util.spec_from_file_location("update_feed", MODULE)
feed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feed)


class MethodClassificationTests(unittest.TestCase):
    def test_explicit_follow_repost_is_sns(self):
        self.assertEqual(feed.detect_method("公式Xフォロー＆リポストでギフト券"), "sns")
        self.assertEqual(feed.detect_method("Instagramでフォロー&コメントすると当たる"), "sns")
        self.assertEqual(feed.detect_method("LINE友だち追加で応募"), "sns")

    def test_web_form_language_is_positive(self):
        self.assertEqual(feed.detect_method("Web応募フォームから応募して家電を当てよう"), "form")
        self.assertEqual(feed.detect_method("アンケートに答えて洗剤が当たる"), "form")

    def test_extra_steps_are_not_easy(self):
        self.assertEqual(feed.detect_method("レシートを送って応募"), "other")
        self.assertEqual(feed.detect_method("店頭で購入した人にプレゼント"), "other")

    def test_unknown_is_not_labeled_form(self):
        self.assertEqual(feed.detect_method("Amazonギフトカードを抽選でプレゼント"), "unknown")
        self.assertEqual(feed.detect_method("XPRICEの家電プレゼント"), "unknown")

    def test_date_parsing_supports_rfc2822_and_iso(self):
        self.assertEqual(feed.parse_date("Thu, 15 Oct 2026 10:00:00 GMT").isoformat(), "2026-10-15")
        self.assertEqual(feed.parse_date("2026-10-15T10:00:00Z").isoformat(), "2026-10-15")


if __name__ == "__main__":
    unittest.main()
