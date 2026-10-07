#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Epic 每周免费游戏 · 拉官方免费游戏接口，输出 data/epic-free.json。"""
import json
import os
import urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": "xiaojj-price-watch/1.0 (+https://xiaojj.pro)"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "epic-free.json")
URL = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=CN"


def main():
    req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    games = []
    for e in d["data"]["Catalog"]["searchStore"]["elements"]:
        promos = (e.get("promotions") or {}).get("promotionalOffers") or []
        if not promos or not promos[0].get("promotionalOffers"):
            continue
        off = promos[0]["promotionalOffers"][0]
        imgs = [x["url"] for x in e.get("keyImages", []) if x.get("type") == "Thumbnail"]
        slug = ((e.get("catalogNs") or {}).get("mappings") or [{}])[0].get("pageSlug") or e.get("urlSlug") or ""
        # 原价
        price = (e.get("price") or {}).get("totalPrice") or {}
        orig = (price.get("fmtPrice") or {}).get("originalPrice", "")
        games.append({
            "name": e.get("title", ""),
            "icon": imgs[0] if imgs else "",
            "url": "https://store.epicgames.com/zh-CN/p/" + slug if slug else "https://store.epicgames.com/zh-CN/free-games",
            "start": off["startDate"][:10],
            "end": off["endDate"][:10],
            "original_price": orig,
        })
    today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
    json.dump({"date": today, "games": games}, open(OUT, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("epic free games:", len(games), [g["name"] for g in games])


if __name__ == "__main__":
    main()
