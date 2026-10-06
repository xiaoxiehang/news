#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""苹果降价榜 · 每天查 iTunes 官方 API，对比 30 天最高价，输出降价 App。

输入: data/app-watchlist.json  [{id, name}]
输出: data/app-drops.json       {date, drops:[...], tracked:[...]}
历史: data/app-price-history.json {appid: [{date, price}]}
"""
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "xiaojj-price-watch/1.0 (+https://xiaojj.pro)"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(BASE, "data", "app-watchlist.json")
HISTORY = os.path.join(BASE, "data", "app-price-history.json")
OUT = os.path.join(BASE, "data", "app-drops.json")
HISTORY_KEEP_DAYS = 30


def lookup(appid):
    url = "https://itunes.apple.com/lookup?id=%d&country=CN" % appid
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    results = d.get("results") or []
    if not results:
        return None
    it = results[0]
    return {
        "id": appid,
        "name": it.get("trackName", ""),
        "price": float(it.get("price") or 0),
        "icon": (it.get("artworkUrl100") or "").replace("100x100", "256x256"),
        "url": it.get("trackViewUrl", ""),
    }


def main():
    watch = json.load(open(WATCHLIST, encoding="utf-8"))
    history = {}
    if os.path.exists(HISTORY):
        history = json.load(open(HISTORY, encoding="utf-8"))
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=HISTORY_KEEP_DAYS)).strftime("%Y-%m-%d")

    tracked, drops = [], []
    for w in watch:
        try:
            info = lookup(w["id"])
        except Exception as e:
            print("lookup fail", w["id"], e)
            continue
        if not info or info["price"] <= 0:
            continue
        h = history.setdefault(str(w["id"]), [])
        h = [x for x in h if x["date"] >= cutoff and x["date"] != today]
        h.append({"date": today, "price": info["price"]})
        history[str(w["id"])] = h
        hist_max = max(x["price"] for x in h)
        tracked.append({**info, "hist_max": hist_max})
        if info["price"] < hist_max:
            drops.append({
                **info,
                "original_price": hist_max,
                "discount": round((1 - info["price"] / hist_max) * 100),
            })

    drops.sort(key=lambda x: -x["discount"])
    json.dump(history, open(HISTORY, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"date": today, "drops": drops, "tracked": tracked,
               "tracked_count": len(tracked)},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tracked=%d drops=%d" % (len(tracked), len(drops)))


if __name__ == "__main__":
    main()
