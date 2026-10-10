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
STATUS_PATH = os.path.join(BASE, "data", "deals-status.json")

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


def page_title(html):
    m = re.search(r"<title>([^<]*)</title>", html or "")
    return (m.group(1) if m else "").strip()


def resolve_store(appid, expect_name=""):
    """返回 (store_url, header_image)。bundle ID 会落在错的 app 页上，用标题校验。"""
    app_url = f"https://store.steampowered.com/app/{appid}/"
    bundle_url = f"https://store.steampowered.com/bundle/{appid}/"
    try:
        r = requests.get(app_url, headers=UA, timeout=15, allow_redirects=True)
        title = page_title(r.text)
        # 标题里没有期望的游戏名 → 很可能是 bundle ID 撞了 app ID，切到 bundle 页
        key = (expect_name or "").split(":")[0].split("：")[0].strip().lower()
        if key and key not in title.lower():
            rb = requests.get(bundle_url, headers=UA, timeout=15)
            if rb.status_code == 200 and "ultimate edition" in rb.text.lower() or key in page_title(rb.text).lower():
                m = re.search(r'<meta property="og:image" content="([^"]+)"', rb.text)
                img = m.group(1).split("?")[0] if m else ""
                return bundle_url, img
    except Exception:
        pass
    # 普通 app：固定地址优先
    base = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}"
    for name in ("header.jpg", "capsule_616x353.jpg"):
        url = f"{base}/{name}"
        try:
            if requests.head(url, headers=UA, timeout=10).status_code == 200:
                return app_url, url
        except Exception:
            pass
    try:
        r = requests.get(app_url, headers=UA, timeout=15)
        m = re.search(r'<meta property="og:image" content="([^"]+)"', r.text)
        if m:
            return app_url, m.group(1).split("?")[0]
    except Exception:
        pass
    return app_url, ""


def resolve_image(appid, expect_name=""):
    """返回可用的封面图 URL；都不可用返回空字符串（前端用占位样式）"""
    return resolve_store(appid, expect_name)[1]


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
        store_url, header_image = resolve_store(appid, it.get("name") or "")
        deals.append({
            "appid": appid,
            "name": it.get("name") or str(appid),
            "discount_percent": disc,
            "original_price": round(orig, 2),
            "final_price": round(final, 2),
            "currency": it.get("currency") or "CNY",
            "positive_rate": round(rate * 100, 1),
            "total_reviews": total,
            "header_image": header_image,
            "url": store_url,
            "score": round(score, 3),
        })

    deals.sort(key=lambda d: d["score"], reverse=True)
    deals = deals[:TOP_N]
    print(f"达标 {len(deals)} 款", flush=True)

    # 状态文件每天都写：让推送任务一眼看到今日 deals 是否新鲜，
    # 不再靠人眼发现"防空榜保护"拦截导致的静默过期
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    status = {
        "date": today,
        "candidates": len(seen),
        "qualified": len(deals),
        "min_items": MIN_ITEMS,
        "deals_updated": len(deals) >= MIN_ITEMS,
    }
    os.makedirs(os.path.dirname(STATUS_PATH), exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)
    print(f"状态已写入 {STATUS_PATH}: {status}", flush=True)

    if len(deals) < MIN_ITEMS:
        print(f"有效条目不足 {MIN_ITEMS}，不覆盖旧文件", flush=True)
        return 0

    doc = {
        "date": today,
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
