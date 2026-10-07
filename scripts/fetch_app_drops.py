#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""苹果降价/限免榜 · 每天查 iTunes 官方 API（国区+美区+港区），对比 30 天最高价，输出降价 App。

数据源：
  1. 三国付费榜 Top100（RSS）：自动发现热门付费 App
  2. data/app-watchlist.json：手动关注的 App（榜单可能漏掉的小众好 App）

输出: data/app-drops.json       {date, drops:[...], tracked:[...]}
历史: data/app-price-history.json {appid: {CN: [{date, price}], US: [...], HK: [...]}}
"""
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

UA = {"User-Agent": "xiaojj-price-watch/1.0 (+https://xiaojj.pro)"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(BASE, "data", "app-watchlist.json")
MAC_WATCHLIST = os.path.join(BASE, "data", "mac-watchlist.json")
HISTORY = os.path.join(BASE, "data", "app-price-history.json")
OUT = os.path.join(BASE, "data", "app-drops.json")
HISTORY_KEEP_DAYS = 30
CHART_LIMIT = 100
REGIONS = [("CN", "国区", "¥"), ("US", "美区", "$"), ("HK", "港区", "HK$")]
FX_USD_CNY = 7.2  # 美区价格换算参考


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def chart_ids(country, limit=CHART_LIMIT):
    """取某区付费榜 TopN 的 app id 集合。"""
    url = "https://itunes.apple.com/%s/rss/toppaidapplications/limit=%d/json" % (
        country.lower(), limit)
    try:
        d = get_json(url)
    except Exception as e:
        print("chart fail", country, e)
        return set()
    ids = set()
    for e in (d.get("feed", {}).get("entry") or []):
        try:
            ids.add(int(e["id"]["attributes"]["im:id"]))
        except Exception:
            continue
    return ids


def lookup_many(appids, country):
    """批量查价（lookup 支持逗号分隔多个 id）。返回 {id: info}。"""
    out = {}
    ids = sorted(set(appids))
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        url = "https://itunes.apple.com/lookup?id=%s&country=%s" % (
            ",".join(map(str, chunk)), country)
        try:
            d = get_json(url)
        except Exception as e:
            print("lookup fail", country, e)
            continue
        for it in d.get("results") or []:
            try:
                aid = int(it.get("trackId"))
            except Exception:
                continue
            out[aid] = {
                "price": float(it.get("price") or 0),
                "currency": it.get("currency") or "USD",
                "name": it.get("trackName", ""),
                "icon": (it.get("artworkUrl100") or "").replace("100x100", "256x256"),
                "url": it.get("trackViewUrl", ""),
            }
    return out


def main():
    watch = []
    if os.path.exists(WATCHLIST):
        watch = json.load(open(WATCHLIST, encoding="utf-8"))
    manual_ids = {int(w["id"]) for w in watch}
    manual_names = {int(w["id"]): w.get("name", "") for w in watch}

    mac_watch = []
    if os.path.exists(MAC_WATCHLIST):
        mac_watch = json.load(open(MAC_WATCHLIST, encoding="utf-8"))
    mac_ids = {int(w["id"]) for w in mac_watch}
    mac_names = {int(w["id"]): w.get("name", "") for w in mac_watch}

    history = {}
    if os.path.exists(HISTORY):
        history = json.load(open(HISTORY, encoding="utf-8"))
    # 兼容旧格式：{appid: [{date, price}]} → {appid: {"CN": [...]}}
    for k, v in list(history.items()):
        if isinstance(v, list):
            history[k] = {"CN": v}

    # 三区榜单 id 并集 + 手动 watchlist
    all_ids = set(manual_ids)
    for code, _, _ in REGIONS:
        all_ids |= chart_ids(code)
    print("ios apps to check:", len(all_ids))
    print("mac apps to check:", len(mac_ids))

    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=HISTORY_KEEP_DAYS)).strftime("%Y-%m-%d")

    # 分区批量查价
    region_data = {}
    for code, _, _ in REGIONS:
        region_data[code] = lookup_many(all_ids, code)

    tracked, drops = [], []

    def process(appid, rdata, platform, name_hint):
        key = ("mac:" if platform == "mac" else "") + str(appid)
        h = history.setdefault(key, {})
        info = {"id": appid, "name": name_hint, "prices": {}, "platform": platform}
        base_info = None
        for code, label, symbol in REGIONS:
            r = rdata[code].get(appid)
            if not r:
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
            return
        info["name"] = base_info["name"] or info["name"] or key
        info["icon"] = base_info["icon"]
        info["url"] = base_info["url"]
        tracked.append(info)
        # 任一区降价即上榜（取降幅最大的区）；价格为 0 且历史有价 = 限免，按 100% 计
        best = None
        for code, p in info["prices"].items():
            if p["price"] < p["hist_max"]:
                disc = 100 if p["price"] == 0 else round((1 - p["price"] / p["hist_max"]) * 100)
                if best is None or disc > best["discount"]:
                    best = {"region": code, "discount": disc,
                            "original_price": p["hist_max"],
                            "is_free": p["price"] == 0}
        if best:
            drops.append({**info, **best})

    for appid in sorted(all_ids):
        process(appid, region_data, "ios", manual_names.get(appid, ""))

    # Mac 应用：与 iOS 同一套 lookup，按区查价
    mac_region_data = {}
    for code, _, _ in REGIONS:
        mac_region_data[code] = lookup_many(mac_ids, code)
    for appid in sorted(mac_ids):
        process(appid, mac_region_data, "mac", mac_names.get(appid, ""))

    drops.sort(key=lambda x: -x["discount"])
    json.dump(history, open(HISTORY, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"date": today, "drops": drops, "tracked": tracked,
               "tracked_count": len(tracked), "fx_usd_cny": FX_USD_CNY},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tracked=%d drops=%d" % (len(tracked), len(drops)))


if __name__ == "__main__":
    main()
