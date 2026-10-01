#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股异动服务端巡检脚本。
- 读取 data/stock.json（自选股 + 阈值）
- 先拉 Stooq 免费 CSV，失败则降级用 Yahoo Finance v8 chart（单 symbol）
- 对比 data/stock-latest.json 上次记录（边沿触发：条件由假变真才告警）
- 触发阈值时经 Bark 推送到手机（BARK_KEY 环境变量；未设置则只打日志）
- 写回 data/stock-latest.json（含更新时间）
任何单只 symbol 失败都不影响其他 symbol，脚本永不因行情失败而非零退出。
"""
import json
import os
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
STOCK_JSON = DATA / "stock.json"
LATEST_JSON = DATA / "stock-latest.json"

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
TIMEOUT = 12  # 单次请求超时秒数

STOOQ_URL = "https://stooq.com/q/l/?s={syms}&f=sd2t2ohlcv&h&e=csv"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=5d"


def log(*args):
    print("[stock_watch]", *args, flush=True)


def utc_day():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------- 行情源 ----------

def fetch_stooq(symbols):
    """Stooq 批量 CSV。返回 {SYM: {price, volume}}；无 prev_close（降级用）。"""
    syms = ",".join(s.lower() + ".us" for s in symbols)
    r = requests.get(STOOQ_URL.format(syms=syms), headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    text = r.text.strip()
    if not text or text.lstrip().startswith("<"):
        raise ValueError("Stooq 返回非 CSV（可能被风控拦截）")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    header = [h.strip().lower() for h in lines[0].split(",")]
    try:
        i_sym, i_close, i_vol = header.index("symbol"), header.index("close"), header.index("volume")
    except ValueError:
        raise ValueError(f"Stooq 表头异常: {lines[0][:80]}")
    out = {}
    for ln in lines[1:]:
        p = ln.split(",")
        if len(p) <= max(i_sym, i_close, i_vol):
            continue
        sym = p[i_sym].strip().upper().replace(".US", "")
        try:
            price, vol = float(p[i_close]), int(float(p[i_vol]))
        except ValueError:
            continue
        if price > 0:
            out[sym] = {"price": price, "volume": vol}
    if not out:
        raise ValueError("Stooq 解析出 0 条有效行情")
    return out


def fetch_yahoo(symbol):
    """Yahoo 单 symbol。返回完整字段 {price, prev_close, change_pct, volume, vol_base}。"""
    r = requests.get(YAHOO_URL.format(sym=symbol), headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    result = r.json()["chart"]["result"][0]
    meta = result["meta"]
    price = meta.get("regularMarketPrice")
    prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
    if not price or not prev_close:
        raise ValueError("Yahoo 缺少价格字段")
    volume = meta.get("regularMarketVolume") or 0
    vols = [v for v in result["indicators"]["quote"][0]["volume"] if v]
    full_days = vols[:-1] if len(vols) > 1 else []
    base_slice = full_days[-5:]
    vol_base = sum(base_slice) / len(base_slice) if base_slice else 0
    return {
        "price": round(float(price), 2),
        "prev_close": round(float(prev_close), 2),
        "change_pct": round((float(price) - float(prev_close)) / float(prev_close) * 100, 2),
        "volume": int(volume),
        "vol_base": int(vol_base),
    }


# ---------- Bark 推送 ----------

def bark_push(title, body):
    key = os.environ.get("BARK_KEY", "").strip()
    if not key:
        log("BARK_KEY 未设置，跳过推送 |", title, "|", body)
        return False
    url = (
        "https://api.day.app/"
        + key
        + "/"
        + urllib.parse.quote(title)
        + "/"
        + urllib.parse.quote(body)
        + "?group=stock"
    )
    try:
        r = requests.get(url, timeout=TIMEOUT)
        log("Bark 推送", r.status_code, title)
        return r.ok
    except Exception as e:  # noqa: BLE001
        log("Bark 推送失败:", e)
        return False


# ---------- 主流程 ----------

def main():
    cfg = json.loads(STOCK_JSON.read_text(encoding="utf-8"))
    symbols_cfg = {s["symbol"].upper(): s for s in cfg.get("symbols", [])}
    if not symbols_cfg:
        log("stock.json 无自选股，退出")
        return 0

    prev = {}
    if LATEST_JSON.exists():
        try:
            prev = json.loads(LATEST_JSON.read_text(encoding="utf-8")).get("quotes", {})
        except Exception as e:  # noqa: BLE001
            log("读取 stock-latest.json 失败:", e)

    # 1) 批量拉 Stooq
    stooq_quotes, yahoo_needed = {}, []
    try:
        stooq_quotes = fetch_stooq(list(symbols_cfg))
        log(f"Stooq 成功: {len(stooq_quotes)} 只")
    except Exception as e:  # noqa: BLE001
        log("Stooq 失败，全部降级走 Yahoo:", e)
        yahoo_needed = list(symbols_cfg)

    quotes = {}
    for sym, sc in symbols_cfg.items():
        q = None
        source = "stooq"
        if sym in stooq_quotes:
            sq = stooq_quotes[sym]
            p = prev.get(sym, {})
            base_price = p.get("prev_close") or p.get("price")
            q = {
                "price": round(sq["price"], 2),
                "prev_close": base_price,
                "change_pct": round((sq["price"] - base_price) / base_price * 100, 2) if base_price else 0.0,
                "volume": sq["volume"],
                "vol_base": p.get("vol_base", 0),
                "degraded": True,  # 无前收，用上次记录价对比
            }
        else:
            source = "yahoo"
            try:
                q = fetch_yahoo(sym)
            except Exception as e:  # noqa: BLE001
                log(f"{sym} Yahoo 也失败，沿用上次数据:", e)
                if sym in prev:
                    q = dict(prev[sym])
                    q["stale"] = True
                else:
                    continue
        q["source"] = source
        quotes[sym] = q

    # 2) 阈值判断（边沿触发）
    today = utc_day()
    for sym, sc in symbols_cfg.items():
        if sym not in quotes:
            continue
        q = quotes[sym]
        thr = float(sc.get("change_pct", 3.0))
        vol_mult = float(sc.get("vol_mult", 2.0))
        vol_ratio = (q["volume"] / q["vol_base"]) if q.get("vol_base") else 0.0
        q["vol_ratio"] = round(vol_ratio, 2)

        prev_alerts = prev.get(sym, {}).get("alerts", {})
        alerts = {}
        events = []
        conds = {
            "change": abs(q["change_pct"]) >= thr,
            "volume": vol_ratio >= vol_mult and q.get("vol_base", 0) > 0,
        }
        for kind, cond in conds.items():
            pa = prev_alerts.get(kind, {})
            was_active = pa.get("active") and pa.get("day") == today
            if cond and not was_active:
                alerts[kind] = {"active": True, "day": today}
                if kind == "change":
                    events.append(("美股异动", f"{sym} {'+' if q['change_pct'] >= 0 else ''}{q['change_pct']}%（阈值±{thr}%），现价 {q['price']}"))
                else:
                    events.append(("美股放量", f"{sym} 放量 {vol_ratio:.1f}x（阈值 {vol_mult}x），成交量 {q['volume']:,}"))
            elif cond:
                alerts[kind] = {"active": True, "day": today}
            else:
                alerts[kind] = {"active": False, "day": today}
        q["alerts"] = alerts
        for title, body in events:
            bark_push(title, body)
            log("触发:", title, body)

    # 3) 写回
    now = datetime.now(timezone.utc)
    payload = {
        "updated_at": now.astimezone().isoformat(timespec="seconds"),
        "updated_at_utc": now.isoformat(timespec="seconds"),
        "source": "stooq+yahoo" if stooq_quotes else "yahoo",
        "note": "由 stock-watch workflow 每 15 分钟更新；页面在行情接口不可用时降级读取本文件",
        "quotes": quotes,
    }
    LATEST_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"写回 {LATEST_JSON.name}，{len(quotes)} 只")
    return 0


if __name__ == "__main__":
    sys.exit(main())
