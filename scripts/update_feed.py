#!/usr/bin/env python3
"""Public RSS discovery only. No application or login automation."""
import datetime as dt, hashlib, html, json, re, urllib.request
from xml.etree import ElementTree as ET
from pathlib import Path
from email.utils import parsedate_to_datetime

OUT=Path(__file__).resolve().parents[1]/"data/campaigns.json"
RSS="https://prtimes.jp/index.rdf"
SIGNAL=re.compile(r"抽選で.{0,50}(当たる|プレゼント)|プレゼントキャンペーン|フォロー.{0,8}リポスト|プレゼント企画|ギフト券.{0,30}(当たる|プレゼント)")
SKIP=re.compile(r"当選者発表|当選結果|抽選販売|抽選予約")
JST=dt.timezone(dt.timedelta(hours=9))
def child(e,tag):
    for c in e:
        if c.tag.split("}")[-1]==tag:return "".join(c.itertext()).strip()
    return ""
def main():
    req=urllib.request.Request(RSS,headers={"User-Agent":"KenshoNote-RSS/1.0","Accept":"application/rdf+xml,application/rss+xml,application/xml"})
    with urllib.request.urlopen(req,timeout=20) as response:
        data=response.read(3_000_001)
        if len(data)>3_000_000:raise RuntimeError("oversized feed")
    today=dt.datetime.now(JST)
    previous=json.loads(OUT.read_text(encoding="utf-8")).get("items",[]) if OUT.exists() else []
    result={}
    for e in ET.fromstring(data).iter():
        if e.tag.split("}")[-1] not in ("item","entry"):continue
        title=re.sub(r"<[^>]+>"," ",html.unescape(child(e,"title"))).strip()[:150]
        if not SIGNAL.search(title) or SKIP.search(title):continue
        link=child(e,"link")
        if not re.fullmatch(r"https://prtimes\.jp/[^?#\s]+(?:[?#][^\s]*)?",link):continue
        link=link.split("?")[0].split("#")[0]
        published=child(e,"date") or child(e,"pubDate")
        try:
            date=dt.datetime.fromisoformat(published.replace("Z","+00:00")) if "T" in published else parsedate_to_datetime(published)
            date=date.astimezone(JST).date()
        except (ValueError,TypeError):continue
        if not today.date()-dt.timedelta(days=90)<=date<=today.date()+dt.timedelta(days=1):continue
        cid="rss-"+hashlib.sha256(link.encode()).hexdigest()[:18]
        result[cid]={"id":cid,"title":title,"url":link,"organizer":"PR TIMES掲載記事（主催者は要確認）","category":"その他","deadline":None,"createdAt":date.isoformat(),"source":"PR TIMES"}
    for item in previous:
        if not isinstance(item,dict) or not str(item.get("id","")).startswith("rss-"):continue
        try: age=dt.date.fromisoformat(item["createdAt"])
        except (ValueError,KeyError,TypeError):continue
        if age<today.date()-dt.timedelta(days=90):continue
        if re.fullmatch(r"https://prtimes\.jp/[^\s]+",str(item.get("url",""))):result.setdefault(item["id"],item)
    items=sorted(result.values(),key=lambda x:x.get("createdAt",""),reverse=True)[:150]
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps({"generated_at":today.isoformat(timespec="seconds"),"source":"PR TIMES RSS (candidate titles only)","items":items},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("candidates",len(items))
if __name__=="__main__":main()
