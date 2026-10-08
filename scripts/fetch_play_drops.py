#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""谷歌 Play 降价/限免榜 · 每天抓 play.google.com 应用页（美区店面），对比 30 天最高价，输出降价 App。

Play 无官方查价接口：价格从页面内嵌 JSON 的 offers 块解析（纯 HTTP，无需渲染 JS）。
数据源：data/play-watchlist.json（包名列表，人工维护）
输出: data/play-drops.json         {date, drops:[...], tracked:[...]}
历史: data/play-price-history.json  {pkg: [{date, price}]}
"""
import json
import os
import re
import time
import urllib.request
import urllib.error

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCHLIST = os.path.join(BASE, "data", "play-watchlist.json")
HISTORY = os.path.join(BASE, "data", "play-price-history.json")
OUT = os.path.join(BASE, "data", "play-drops.json")
HISTORY_KEEP_DAYS = 30
STORE = ("US", "美区", "$")
SLEEP_BETWEEN = 1.0  # 对 Play 客气一点


def fetch_page(pkg):
    url = "https://play.google.com/store/apps/details?id=%s&hl=en&gl=US" % pkg
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def parse(html):
    """返回 (name, price, currency, icon)，缺失则为 None。"""
    m = re.search(r'"@type":"Offer","price":"([\d.]+)","priceCurrency":"([A-Z]+)"', html)
    if not m:
        return None
    price, currency = float(m.group(1)), m.group(2)
    t = re.search(r'<meta property="og:title" content="(.+?) - Apps on Google Play"', html)
    name = t.group(1) if t else None
    im = re.search(r'"image":"(https://[^"]+)"', html)
    icon = im.group(1) if im else None
    return name, price, currency, icon


def main():
    if not os.path.exists(WATCHLIST):
        print("no watchlist", WATCHLIST)
        return
    watch = json.load(open(WATCHLIST, encoding="utf-8"))
    history = {}
    if os.path.exists(HISTORY):
        history = json.load(open(HISTORY, encoding="utf-8"))

    from datetime import datetime, timedelta
    today = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() - timedelta(days=HISTORY_KEEP_DAYS)).strftime("%Y-%m-%d")

    tracked, drops, dead = [], [], []
    code, label, symbol = STORE
    for w in watch:
        pkg = w["pkg"]
        try:
            html = fetch_page(pkg)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                dead.append(pkg)
                print("delisted(404):", pkg)
            else:
                print("fetch fail:", pkg, e)
            continue
        except Exception as e:
            print("fetch fail:", pkg, type(e).__name__, e)
            continue
        time.sleep(SLEEP_BETWEEN)
        p = parse(html)
        if not p:
            print("parse fail:", pkg)
            continue
        name, price, currency, icon = p
        name = name or w.get("name") or pkg
        h = history.setdefault(pkg, [])
        hist = [x for x in h if x["date"] >= cutoff and x["date"] != today]
        hist.append({"date": today, "price": price})
        history[pkg] = hist
        hist_max = max(x["price"] for x in hist)
        info = {
            "id": pkg, "name": name, "icon": icon,
            "url": "https://play.google.com/store/apps/details?id=%s&hl=en&gl=US" % pkg,
            "platform": "play",
            "prices": {code: {
                "label": label, "symbol": symbol, "price": price,
                "hist_max": hist_max, "currency": currency,
            }},
        }
        tracked.append(info)
        # 降价判定：现价 < 30 天最高价；0 元且历史有价 = 限免，按 100% 计
        if price < hist_max:
            disc = 100 if price == 0 else round((1 - price / hist_max) * 100)
            drops.append({**info, "region": code, "discount": disc,
                          "original_price": hist_max, "is_free": price == 0})

    drops.sort(key=lambda x: -x["discount"])
    json.dump(history, open(HISTORY, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"date": today, "drops": drops, "tracked": tracked,
               "tracked_count": len(tracked), "store": code},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("tracked=%d drops=%d dead=%d" % (len(tracked), len(drops), len(dead)))
    if dead:
        print("prune from watchlist:", dead)


if __name__ == "__main__":
    main()
