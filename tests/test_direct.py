"""Unit tests for conservative direct-entry links (no requests or form submissions)."""
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "update_direct.py"
spec = importlib.util.spec_from_file_location("update_direct", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class DirectEntryTests(unittest.TestCase):
    def test_publisher_owned_form_is_accepted(self):
        self.assertEqual(
            mod.valid_form_link("https://from.shinyusha.co.jp/n/form/zrpb/YBDnzsL63vy2m4xasaHBR"),
            "https://from.shinyusha.co.jp/n/form/zrpb/YBDnzsL63vy2m4xasaHBR"
        )

    def test_other_hosts_cannot_masquerade_as_official_forms(self):
        for url in (
            "https://from.shinyusha.co.jp.evil.test/n/form/zrpb/YBDnzsL63vy2m4xasaHBR",
            "http://from.shinyusha.co.jp/n/form/zrpb/YBDnzsL63vy2m4xasaHBR",
            "https://from.shinyusha.co.jp/admin/",
            "https://docs.google.com.evil.test/forms/d/e/12345",
            "https://phishing.example.com/login",
        ):
            self.assertFalse(mod.valid_form_link(url), url)

    def test_latest_issue_is_selected(self):
        new = "https://from.shinyusha.co.jp/n/form/zrpb/YBDnzsL63vy2m4xasaHBR"
        old = "https://from.shinyusha.co.jp/n/form/zrpb/FYtcEAnCcpcAsPHdEZbBh"
        html = """<html><body><h1>読者プレゼント</h1><h2>11月号 応募</h2>
        <a href="{}">2026年11月号の応募はこちら</a>
        <h2>10月号</h2><a href="{}">2026年10月号の応募はこちら</a>
        </body></html>""".format(new,old)
        self.assertEqual(mod.find_direct_link(html, "11月号"), new)

    def test_current_issue_with_generic_labels(self):
        new = "https://from.shinyusha.co.jp/n/form/zrpb/tJnDbzQdnQumHR4ucRT9s"
        old = "https://from.shinyusha.co.jp/n/form/zrpb/vyA9pGVAhB6nDaDWPcv83"
        html = """<html><body><h1>読者プレゼント</h1><h2>11月号</h2>
        <a href="{}">応募ページはこちら</a><h2>10月号</h2>
        <a href="{}">応募ページはこちら</a></body></html>""".format(new,old)
        self.assertEqual(mod.find_direct_link(html, "11月号"),new)

    def test_missing_issue_is_not_assumed(self):
        html = """<h1>読者プレゼント</h1><a href="https://from.shinyusha.co.jp/n/form/zrpb/YBDnzsL63vy2m4xasaHBR">応募はこちら</a>"""
        self.assertFalse(mod.find_direct_link(html, "11月号"))

if __name__ == "__main__":
    unittest.main()
