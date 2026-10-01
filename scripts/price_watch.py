#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""降价提醒助手 · 服务端每日巡检

读取 data/prices.json 追踪列表，对 steam / apple 类型调用官方 API 查现价；
现价 <= 目标价 且之前未提醒过（notified 标记去重），则经 Bark 推送到手机；
价格回升到目标价以上后重置 notified，下次再降价会重新提醒。
手动（manual）类型跳过，由用户在网页端更新。

环境变量：
    BARK_KEY  Bark 推送 key（未设置则只打印、不推送）
"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone

import requests

UA = {"User-Agent": "xiaojj-price-watch/1.0 (+https://xiaojj.pro)"}
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE, "data", "prices.json")
HISTORY_KEEP = 30


def fetch_steam(appid):
    """返回 (现价, 币种)；免费游戏返回 (0.0, 'CNY')；查不到返回 None"""
    r = requests.get(
        "https://store.steampowered.com/api/appdetails",
        params={"appids": appid, "filters": "price_overview", "cc": "cn"},
        headers=UA, timeout=20,
    )
    r.raise_for_status()
    entry = (r.json() or {}).get(str(appid)) or {}
    if not entry.get("success"):
        return None
    po = (entry.get("data") or {}).get("price_overview")
    if not po:  # 免费游戏无 price_overview
        return (0.0, "CNY")
    return (po["final"] / 100.0, po.get("currency") or "CNY")


def fetch_apple(appid):
    """返回 (现价, 币种)；查不到返回 None"""
    r = requests.get(
        "https://itunes.apple.com/lookup",
        params={"id": appid, "country": "CN"},
        headers=UA, timeout=20,
    )
    r.raise_for_status()
    d = r.json() or {}
    if not d.get("resultCount"):
        return None
    a = d["results"][0]
    return (float(a.get("price") or 0), a.get("currency") or "CNY")


def bark_push(key, title, body, url=""):
    path = "/".join(["", key, urllib.parse.quote(title), urllib.parse.quote(body)])
    link = f"https://api.day.app{path}"
    if url:
        link += "?url=" + urllib.parse.quote(url)
    r = requests.get(link, headers=UA, timeout=15)
    r.raise_for_status()


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        doc = json.load(f)
    items = doc.get("items", [])
    bark_key = (os.environ.get("BARK_KEY") or "").strip()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    updated = 0
    for it in items:
        itype = it.get("type")
        appid = str(it.get("appid") or "").strip()
        name = it.get("name") or appid or "未知商品"
        if itype == "manual" or not appid:
            continue  # 手动商品由网页端更新，服务端跳过
        try:
            if itype == "steam":
                res = fetch_steam(appid)
            elif itype == "apple":
                res = fetch_apple(appid)
            else:
                print(f"[SKIP] {name} 未知类型 {itype}")
                continue
        except Exception as e:  # 网络/API 抖动不中断整轮巡检
            print(f"[ERR] {name} 查价失败: {e}")
            continue
        if res is None:
            print(f"[ERR] {name} 未找到（appid 可能失效）")
            continue

        price, currency = round(res[0], 2), res[1]
        it["current"] = price
        it["currency"] = currency
        hist = it.get("history") or []
        if not hist or hist[-1].get("price") != price:
            hist.append({"t": today, "price": price})
            it["history"] = hist[-HISTORY_KEEP:]

        target = float(it.get("target") or 0)
        if price <= target and not it.get("notified"):
            title = f"降到 ¥{price:.2f} 了"
            body = f"{name} 已降到目标价 ¥{target:.2f}，现价 ¥{price:.2f}"
            if bark_key:
                try:
                    bark_push(bark_key, title, body, it.get("url") or "")
                    print(f"[PUSH] {body}")
                except Exception as e:
                    print(f"[ERR] {name} 推送失败: {e}")
            else:
                print(f"[DRY] {body}（未配置 BARK_KEY，仅打印）")
            it["notified"] = True
        elif price > target and it.get("notified"):
            it["notified"] = False  # 价格回升，重置标记
            print(f"[RESET] {name} 回升到 ¥{price:.2f}，提醒标记已重置")
        updated += 1

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"巡检完成：{len(items)} 件，更新 {updated} 件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
