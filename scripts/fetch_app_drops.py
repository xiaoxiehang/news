#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""苹果降价榜 · 每天查 iTunes 官方 API（国区+美区），对比 30 天最高价，输出降价 App。

输入: data/app-watchlist.json  [{id, name}]
输出: data/app-drops.json       {date, drops:[...], tracked:[...]}
历史: data/app-price-history.json {appid: {CN: [{date, price}], US: [{date, price}]}}
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
REGIONS = [("CN", "国区", "¥"), ("US", "美区", "$")]
FX_USD_CNY = 7.2  # 美区价格换算参考


def lookup(appid, country):
    url = "https://itunes.apple.com/lookup?id=%d&country=%s" % (appid, country)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        d = json.load(r)
    results = d.get("results") or []
    if not results:
        return None
    it = results[0]
    price = float(it.get("price") or 0)
    return {
        "price": price,
        "currency": it.get("currency") or ("CNY" if country == "CN" else "USD"),
        "name": it.get("trackName", ""),
        "icon": (it.get("artworkUrl100") or "").replace("100x100", "256x256"),
        "url": it.get("trackViewUrl", ""),
    }


def main():
    watch = json.load(open(WATCHLIST, encoding="utf-8"))
    history = {}
    if os.path.exists(HISTORY):
        history = json.load(open(HISTORY, encoding="utf-8"))
    # 兼容旧格式：{appid: [{date, price}]} → {appid: {"CN": [...]}}
    for k, v in list(history.items()):
        if isinstance(v, list):
            history[k] = {"CN": v}
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=HISTORY_KEEP_DAYS)).strftime("%Y-%m-%d")

    tracked, drops = [], []
    for w in watch:
        appid = str(w["id"])
        h = history.setdefault(appid, {})
        info = {"id": w["id"], "name": w["name"], "prices": {}}
        base_info = None
        for code, label, symbol in REGIONS:
            try:
                r = lookup(w["id"], code)
            except Exception as e:
                print("lookup fail", w["id"], code, e)
                continue
            if not r or r["price"] <= 0:
                continue
            if base_info is None:
                base_info = r
            hist = [x for x in h.get(code, []) if x["date"] >= cutoff and x["date"] != today]
            hist.append({"date": today, "price": r["price"]})
            h[code] = hist
            hist_max = max(x["price"] for x in hist)
            info["prices"][code] = {
                "label": label, "symbol": symbol,
                "price": r["price"], "hist_max": hist_max,
                "currency": r["currency"],
            }
        if not info["prices"] or base_info is None:
            continue
        info["name"] = base_info["name"] or w["name"]
        info["icon"] = base_info["icon"]
        info["url"] = base_info["url"]
        tracked.append(info)
        # 任一区降价即上榜（取降幅最大的区）
        best = None
        for code, p in info["prices"].items():
            if p["price"] < p["hist_max"]:
                disc = round((1 - p["price"] / p["hist_max"]) * 100)
                if best is None or disc > best["discount"]:
                    best = {"region": code, "discount": disc,
                            "original_price": p["hist_max"]}
        if best:
            drops.append({**info, **best})

    drops.sort(key=lambda x: -x["discount"])
    json.dump(history, open(HISTORY, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"date": today, "drops": drops, "tracked": tracked,
               "tracked_count": len(tracked), "fx_usd_cny": FX_USD_CNY},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tracked=%d drops=%d" % (len(tracked), len(drops)))


if __name__ == "__main__":
    main()
