#!/usr/bin/env python3
"""Read public syndication feeds to find possible practical giveaways.

No form automation, login, scraping of page contents, social-media API use,
CAPTCHA processing, personal information collection, or automatic entry.
Every result is only an *unverified lead*; signup and eligibility are unknown.
"""
import datetime as dt
import hashlib
import html
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data/campaigns.json"
JST = dt.timezone(dt.timedelta(hours=9))
PR_TIMES = "https://prtimes.jp/index.rdf"
QUERIES = (
    "食品 プレゼントキャンペーン 当たる when:14d",
    "家電 ギフト券 抽選 プレゼント when:14d",
    "日用品 無料 懸賞 プレゼント when:14d",
    "ゲーム機 PC周辺機器 プレゼント 応募 when:14d",
)
FEEDS = [("PR TIMES", PR_TIMES),
         ("懸賞生活ブログ", "https://kenshou.syumimania.com/feed/"),
         ("激安らぼ", "https://gekiyasu-lab.net/feed/")] + [
    ("Google ニュース", "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q, "hl": "ja", "gl": "JP", "ceid": "JP:ja"}))
    for q in QUERIES
]
SIGNAL = re.compile(r"プレゼント|懸賞|抽選|当たる|当選|ギフト券|QUOカード")
EXCLUDE = re.compile(
    r"新規(会員)?登録|会員登録(が必要|必須)|有料会員|定期購入|対象商品.{0,12}購入|"
    r"レシート応募|購入者限定|購入者対象|抽選販売|先行販売|抽選予約|"
    r"参加費|応募費用|当選結果|当選者発表|受付終了|応募終了"
)
REGISTER = re.compile(r"会員登録(?!不要)|新規登録(?!不要)|アカウント作成|アプリ(を)?ダウンロード|LINE(友だち|お友だち)追加")
SIMPLE = re.compile(r"フォームから応募|応募フォーム|登録不要|会員登録不要")
RANK = [
    ("ギフト券", 105, r"Amazonギフト|ギフトカード|QUOカード|クオカード|PayPayポイント|えらべるPay|商品券|図書カード|現金"),
    ("家電・デジタル", 100, r"家電|テレビ|掃除機|イヤホン|ヘッドホン|スマホ|iPhone|iPad|タブレット|パソコン|PC周辺機器|モニター|キーボード|マウス|ドライヤー|炊飯器|コーヒーメーカー"),
    ("食品・飲料", 95, r"食品|飲料|お菓子|スイーツ|お米|お肉|お茶|コーヒー|グルメ|詰め合わせ|ビール|ジュース|食事券|冷凍食品"),
    ("ゲーム・ホビー", 90, r"ゲーム機|Nintendo|Switch|PlayStation|PS5|ゲーミング|Steam|ゲームソフト"),
    ("日用品", 85, r"日用品|洗剤|柔軟剤|シャンプー|化粧品|スキンケア|衛生用品|タオル|入浴剤|歯磨き|キッチン用品|文具|カレンダー|食器|収納用品"),
]
def text_of(item, name):
    for child in item:
        if child.tag.split("}")[-1] == name:
            return "".join(child.itertext()).strip()
    return ""
def plain(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", html.unescape(s or ""))).strip()
def parse_date(s):
    try:
        date = (dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
                if "T" in s else parsedate_to_datetime(s))
        return date.replace(tzinfo=date.tzinfo or dt.timezone.utc).astimezone(JST).date()
    except (ValueError, TypeError, OverflowError):
        return None
def classify(title):
    for category, score, pattern in RANK:
        if re.search(pattern, title, re.I):
            return category, score
    return "その他", 20
def allowed_link(link, feed):
    try:
        u = urllib.parse.urlsplit(link)
        if u.scheme != "https" or u.username or u.password or len(link)>1600: return ""
        if feed == "PR TIMES" and u.hostname != "prtimes.jp": return ""
        if feed == "Google ニュース" and u.hostname != "news.google.com": return ""
        if feed == "懸賞生活ブログ" and u.hostname not in ("kenshou.syumimania.com","www.kenshou.syumimania.com"): return ""
        if feed == "激安らぼ" and u.hostname not in ("gekiyasu-lab.net","www.gekiyasu-lab.net"): return ""
        return urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,u.query,""))
    except ValueError:
        return ""
def fetch(feed):
    req = urllib.request.Request(feed, headers={
        "User-Agent":"KenshoNote-Discovery/1.1 (public RSS only)",
        "Accept":"application/rss+xml,application/rdf+xml,application/xml"})
    with urllib.request.urlopen(req, timeout=18) as response:
        data = response.read(2_000_001)
        if len(data) > 2_000_000: raise ValueError("Feed too large")
    return ET.fromstring(data)
def main():
    now = dt.datetime.now(JST)
    previous = json.loads(OUT.read_text(encoding="utf-8")).get("items",[]) if OUT.exists() else []
    result = {}
    ok = 0
    for source, feed in FEEDS:
        try:
            root = fetch(feed)
            ok += 1
        except (OSError, ValueError, ET.ParseError) as exc:
            print(source, "unavailable:", type(exc).__name__)
            continue
        for item in root.iter():
            if item.tag.split("}")[-1] not in ("item","entry"): continue
            title = plain(text_of(item,"title"))[:160]
            snippet = plain(text_of(item,"description"))[:240]
            if not title or not SIGNAL.search(title): continue
            if EXCLUDE.search(title): continue
            link = allowed_link(text_of(item,"link"), source)
            if not link: continue
            date = parse_date(text_of(item,"date") or text_of(item,"pubDate") or text_of(item,"published"))
            if not date or not now.date()-dt.timedelta(days=30) <= date <= now.date()+dt.timedelta(days=1): continue
            cat, score = classify(title)
            # Explicitly described signups are excluded; all remaining registrations are still UNVERIFIED.
            if REGISTER.search(title): continue
            if "フォロー" in title or "リポスト" in title: score -= 18
            score += 5 if SIMPLE.search(title) else 0
            cid = "rss-" + hashlib.sha256(link.encode()).hexdigest()[:18]
            result[cid] = {
                "id":cid,"title":title,"url":link,
                "organizer":"案内記事（主催者は要確認）",
                "category":cat,"priority":max(0,score),
                "registration":"未確認（応募先で確認）",
                "deadline":None,"createdAt":date.isoformat(),
                "source":source,
            }
    if ok == 0:
        raise RuntimeError("All public RSS feeds failed; retaining existing data")
    for item in previous:
        if not isinstance(item,dict) or not str(item.get("id","")).startswith("rss-"): continue
        age = parse_date(str(item.get("createdAt","")))
        if age is None:
            try: age=dt.date.fromisoformat(item["createdAt"])
            except (ValueError,TypeError,KeyError): continue
        if age < now.date()-dt.timedelta(days=30): continue
        link = str(item.get("url",""))
        source = item.get("source","PR TIMES")
        if allowed_link(link,source) and not EXCLUDE.search(str(item.get("title",""))):
            cat,score=classify(str(item.get("title","")))
            if not REGISTER.search(str(item.get("title",""))):
                item.update(category=cat,priority=score,registration="未確認（応募先で確認）")
                result.setdefault(item["id"],item)
    items=sorted(result.values(),key=lambda x:(x["priority"],x["createdAt"]),reverse=True)[:200]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({
        "generated_at":now.isoformat(timespec="seconds"),
        "source":"Public PR TIMES, Google News, and giveaway blog RSS; candidates unverified",
        "items":items
    },ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("feeds:",ok,"/",len(FEEDS),"candidates:",len(items),"practical:",sum(x["priority"]>=80 for x in items))
if __name__=="__main__":main()
