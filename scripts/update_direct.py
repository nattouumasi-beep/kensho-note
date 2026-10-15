#!/usr/bin/env python3
"""Discover direct entry forms linked from an explicit allowlist of publisher-owned pages.

These are *officially linked* forms, not proof of eligibility or open registration.
No personal data, form submissions, logins, or bulk page crawling are performed.
"""
import datetime as dt
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUTPUT = BASE / "data/direct.json"
JST = dt.timezone(dt.timedelta(hours=9))
SOURCES = [
    {
        "id": "shinyusha-kaden-2026-11",
        "page": "https://360life.shinyusha.co.jp/articles/-/52975",
        "title": "家電批評 11月号 読者プレゼント（アンケート）",
        "month_label": "11月号",
        "deadline": "2026-11-02",
        "category": "家電・デジタル",
        "description": "読者アンケートへの回答が必要。公式記事に掲載された応募フォームへ直行",
    },
    {
        "id": "shinyusha-ldk-2026-11",
        "page": "https://360life.shinyusha.co.jp/articles/-/53042",
        "title": "LDK 11月号 読者プレゼント（アンケート）",
        "month_label": "11月号",
        "deadline": "2026-10-27",
        "category": "日用品",
        "description": "読者アンケートへの回答が必要。公式記事に掲載された応募フォームへ直行",
    },
    {
        "id": "shinyusha-beauty-2026-11",
        "page": "https://360life.shinyusha.co.jp/articles/-/53074",
        "title": "LDK the Beauty 11月号 読者プレゼント（アンケート）",
        "month_label": "11月号",
        "deadline": "2026-10-21",
        "category": "日用品",
        "description": "読者アンケートへの回答が必要。公式記事に掲載された応募フォームへ直行",
    },
]

class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.parts = []
        self.link = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip_depth += 1
        if tag == "a":
            self.link = {"href": dict(attrs).get("href", ""), "parts": []}

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.parts.append(data)
        if self.link is not None:
            self.link["parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.link is not None:
            self.links.append((self.link["href"], " ".join(self.link["parts"]).strip()))
            self.link = None
        if tag in ("script", "style", "noscript") and self.skip_depth:
            self.skip_depth -= 1

def valid_form_link(link):
    try:
        url = urllib.parse.urlsplit(link)
        if url.scheme != "https" or url.username or url.password:
            return ""
        if url.hostname == "docs.google.com" and url.path.startswith("/forms/d/"):
            return urllib.parse.urlunsplit((url.scheme, url.netloc, url.path, url.query, ""))
        if url.hostname == "forms.gle" and re.fullmatch(r"/[A-Za-z0-9_-]{6,}", url.path):
            return urllib.parse.urlunsplit((url.scheme, url.netloc, url.path, "", ""))
    except ValueError:
        pass
    return ""

def find_direct_link(page, month_label):
    parser = Links()
    parser.feed(page)
    text = " ".join(parser.parts)
    # If the current issue is no longer on the official page, do not use old forms.
    if month_label not in text or "読者プレゼント" not in text:
        return ""
    possibilities = [(valid_form_link(href), label) for href, label in parser.links]
    possibilities = [(url, label) for url, label in possibilities if url]
    if not possibilities:
        return ""
    # For newer issues the official pages display current issue first.
    matching = [url for url, label in possibilities if month_label in label]
    if matching:
        return matching[0]
    # Only accept the first form if the page states this issue prominently.
    # Multiple distinct forms with unlabeled links are ambiguous; skip safely.
    if len({url for url, _ in possibilities}) == 1:
        return possibilities[0][0]
    return ""

def main():
    today = dt.datetime.now(JST)
    data = []
    failures = 0
    for source in SOURCES:
        if today.date() > dt.date.fromisoformat(source["deadline"]):
            continue
        req = urllib.request.Request(source["page"], headers={
            "User-Agent": "KenshoNote-Official-Form-Discovery/1.0",
            "Accept": "text/html"})
        try:
            with urllib.request.urlopen(req, timeout=14) as response:
                final = urllib.parse.urlsplit(response.geturl())
                if final.hostname != "360life.shinyusha.co.jp":
                    raise ValueError("unexpected publisher redirect")
                page = response.read(900001)
                if len(page) > 900000:
                    raise ValueError("publisher page exceeds budget")
            link = find_direct_link(page.decode("utf-8", errors="replace"), source["month_label"])
            if not link:
                parser=Links()
                parser.feed(page.decode("utf-8", errors="replace"))
                links=[(href,label) for href,label in parser.links if "応募" in label or "こちら" in label or "フォーム" in label or "docs.google" in href or "forms.gle" in href]
                print(source["id"], "NO_VERIFIABLE_DIRECT_FORM",
                      "page_len",len(page),"month_label",source["month_label"] in " ".join(parser.parts),
                      "anchor_count",len(parser.links),"cta_count",len(links))
                for href,label in links[:8]:
                    # Publisher page links are public, but print only host and short CTA text.
                    print("CTA",repr(label[:70]),urllib.parse.urlsplit(urllib.parse.urljoin(source["page"],href)).hostname,href[:130])
                failures += 1
                continue
            data.append({
                "id": "direct-" + source["id"],
                "title": source["title"],
                "url": link,
                "officialArticle": source["page"],
                "organizer": "晋遊舎（360LiFE公式）",
                "category": source["category"],
                "priority": 125,
                "method": "form",
                "direct": True,
                "verification": "Publisher website links to this form; not submitted or checked for acceptance",
                "description": source["description"],
                "deadline": source["deadline"],
                "registration": "会員登録不要かはフォームで要確認",
                "source": "晋遊舎の公式ページ",
                "createdAt": today.date().isoformat(),
            })
            print(source["id"], "direct form found")
        except (OSError, ValueError, UnicodeError) as exc:
            failures += 1
            print(source["id"], "unavailable", type(exc).__name__)
    if not data and failures:
        # Never replace previously verified form URLs with an empty set due to a transient outage.
        # Do not silently carry expired data into a new run.
        previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {}
        for x in previous.get("items", []):
            try:
                if (x["id"].startswith("direct-") and
                    dt.date.fromisoformat(x["deadline"]) >= today.date() and
                    valid_form_link(x.get("url",""))):
                    data.append(x)
            except (TypeError, ValueError, KeyError, AttributeError):
                pass
    OUTPUT.write_text(json.dumps({
        "generated_at": today.isoformat(timespec="seconds"),
        "source": "Explicit publisher-owned pages; direct form URLs only",
        "items": data,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("official forms:", len(data), "failures:", failures)

if __name__ == "__main__":
    main()
