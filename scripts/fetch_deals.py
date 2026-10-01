#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Steam 每日好价榜 · 每天抓一次 Steam 国区特惠 + 热销榜，
按「折扣力度 × 好评率 × 评价数」算性价比，输出 data/deals.json，
供 price.xiaojj.pro 首页「今日好价」直接展示。

抓不到或有效条目太少时不覆盖旧文件（宁可展示昨天的数据，也不展示空榜）。
"""
import json
import math
import os
import sys
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "xiaojj-price-watch/1.0 (+https://xiaojj.pro)"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(BASE, "data", "deals.json")

MIN_DISCOUNT = 30      # 折扣至少 3 折以下（即 discount_percent >= 30）
MIN_POSITIVE = 0.85    # 好评率至少 85%
MIN_REVIEWS = 500      # 评价数至少 500（过滤冷门刷榜）
TOP_N = 12
MIN_ITEMS = 5          # 少于这个数就不覆盖旧文件


def fetch_categories():
    r = requests.get(
        "https://store.steampowered.com/api/featuredcategories/",
        params={"cc": "CN"}, headers=UA, timeout=30,
    )
    r.raise_for_status()
    return r.json() or {}


def fetch_review(appid):
    """返回 (好评率, 评价总数)，失败返回 (None, None)"""
    try:
        r = requests.get(
            f"https://store.steampowered.com/appreviews/{appid}",
            params={"json": 1, "language": "all", "num_per_page": 0},
            headers=UA, timeout=20,
        )
        r.raise_for_status()
        q = (r.json() or {}).get("query_summary") or {}
        total = q.get("total_reviews") or 0
        pos = q.get("total_positive") or 0
        if total <= 0:
            return None, None
        return pos / total, total
    except Exception as e:
        print(f"  评价接口失败 {appid}: {e}", flush=True)
        return None, None


def main():
    print("抓取 Steam 特惠/热销榜...", flush=True)
    cats = fetch_categories()
    seen = {}
    for tab in ("specials", "top_sellers"):
        for it in (cats.get(tab) or {}).get("items", []):
            appid = it.get("id")
            if not appid or appid in seen:
                continue
            seen[appid] = it
    print(f"去重后候选 {len(seen)} 款", flush=True)

    deals = []
    for appid, it in seen.items():
        disc = it.get("discount_percent") or 0
        if disc < MIN_DISCOUNT:
            continue
        rate, total = fetch_review(appid)
        if rate is None or rate < MIN_POSITIVE or total < MIN_REVIEWS:
            continue
        final = (it.get("final_price") or 0) / 100.0
        orig = (it.get("original_price") or 0) / 100.0
        score = (disc / 100.0) * rate * math.log10(total)
        deals.append({
            "appid": appid,
            "name": it.get("name") or str(appid),
            "discount_percent": disc,
            "original_price": round(orig, 2),
            "final_price": round(final, 2),
            "currency": it.get("currency") or "CNY",
            "positive_rate": round(rate * 100, 1),
            "total_reviews": total,
            "header_image": f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg",
            "url": f"https://store.steampowered.com/app/{appid}/",
            "score": round(score, 3),
        })

    deals.sort(key=lambda d: d["score"], reverse=True)
    deals = deals[:TOP_N]
    print(f"达标 {len(deals)} 款", flush=True)

    if len(deals) < MIN_ITEMS:
        print(f"有效条目不足 {MIN_ITEMS}，不覆盖旧文件", flush=True)
        return 0

    doc = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "Steam 国区特惠/热销",
        "items": deals,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"已写入 {OUT_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
