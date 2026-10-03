#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美股实时异动监听（Finnhub websocket + Bark 推送）。

- 连 Finnhub websocket 订阅自选股实时成交（data/stock.json 的 symbols）
- 滚动窗口检测：
    价格：5 分钟涨跌幅 >= 1.5%，或 15 分钟涨跌幅 >= 2.5%
    放量：近 5 分钟成交笔数 >= 过去 60 分钟平均 5 分钟笔数 x 3，且 5 分钟涨跌幅绝对值 >= 0.8%
- 触发后经 Bark 推送到手机；每只 symbol 每种告警 30 分钟内只推一次
- 仅在美东交易时段（9:30-16:00，周一到周五）推送；盘外只记录行情
- 每 60 秒更新 data/stock-latest.json（与旧版同 schema，source=finnhub-rt）
- 交易时段每 10 分钟 git 提交推送一次数据
- key 从 ~/.config/stock/keys.json 读取（{"finnhub": "...", "bark": "..."}，600 权限）

systemd user service 常驻运行，断线自动重连。
"""
import json
import os
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import websocket  # pip install websocket-client
except ImportError:
    print("[rt] 缺少依赖 websocket-client，请先 pip install websocket-client", flush=True)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CFG = DATA / "stock.json"
LATEST = DATA / "stock-latest.json"
KEYFILE = Path.home() / ".config" / "stock" / "keys.json"

ET = ZoneInfo("America/New_York")

# ---- 检测参数 ----
PRICE_5M_PCT = 1.5    # 5 分钟涨跌幅阈值 %
PRICE_15M_PCT = 2.5   # 15 分钟涨跌幅阈值 %
VOL_MULT = 3.0        # 放量倍数（5min 笔数 vs 过去60min 平均5min笔数）
VOL_PRICE_MIN = 0.8   # 放量告警要求的最小 5 分钟涨跌幅绝对值 %
COOLDOWN_SEC = 30 * 60
WIN_SEC = 60 * 60     # 滚动窗口：保留 60 分钟成交
EVAL_SEC = 20         # 每 20 秒评估一次
JSON_SEC = 60         # 每 60 秒写 stock-latest.json
SYNC_SEC = 10 * 60    # 每 10 分钟 git 同步

FINNHUB_WS = "wss://ws.finnhub.io?token={key}"
FINNHUB_QUOTE = "https://finnhub.io/api/v1/quote?symbol={sym}&token={key}"
BARK_PUSH = "https://api.day.app/push"


def log(*args):
    print("[rt]", *args, flush=True)


def load_keys():
    try:
        d = json.loads(KEYFILE.read_text(encoding="utf-8"))
        fh, bk = (d.get("finnhub") or "").strip(), (d.get("bark") or "").strip()
        return fh, bk
    except Exception as e:
        log("读取 key 文件失败:", e)
        return "", ""


def load_symbols():
    try:
        d = json.loads(CFG.read_text(encoding="utf-8"))
        return [s["symbol"] for s in d.get("symbols", []) if s.get("symbol")]
    except Exception as e:
        log("读取 stock.json 失败:", e)
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]


def market_open_now():
    now = datetime.now(ET)
    if now.weekday() >= 5:
        return False
    mins = now.hour * 60 + now.minute
    return 9 * 60 + 30 <= mins < 16 * 60


class Tracker:
    """单只 symbol 的滚动成交记录与告警状态。"""

    def __init__(self, symbol):
        self.symbol = symbol
        self.trades = deque()  # (ts, price, vol)
        self.lock = threading.Lock()
        self.last_alert = {}   # kind -> ts
        self.prev_close = None
        self.day_volume = 0.0

    def add(self, ts, price, vol):
        with self.lock:
            self.trades.append((ts, price, vol))
            self.day_volume += vol
            cutoff = ts - WIN_SEC
            while self.trades and self.trades[0][0] < cutoff:
                self.trades.popleft()

    def snapshot(self):
        with self.lock:
            return list(self.trades)

    def price_at(self, trades, ts):
        """ts 时刻之前最后一笔成交价。"""
        p = None
        for t, price, _ in trades:
            if t <= ts:
                p = price
            else:
                break
        return p

    def evaluate(self, now):
        """返回 [(kind, title, body)] 告警列表。"""
        trades = self.snapshot()
        if len(trades) < 10:
            return []
        last_ts, last_price, _ = trades[-1]
        p5 = self.price_at(trades, now - 300)
        p15 = self.price_at(trades, now - 900)
        if p5 is None or last_price is None:
            return []
        r5 = (last_price - p5) / p5 * 100
        r15 = (last_price - p15) / p15 * 100 if p15 else 0.0

        # 近5分钟成交笔数 vs 过去60分钟平均5分钟笔数
        c5 = sum(1 for t, _, _ in trades if t >= now - 300)
        buckets = [0] * 12
        for t, _, _ in trades:
            if t >= now - 3600:
                idx = min(11, int((now - t) // 300))
                buckets[idx] += 1
        avg5 = sum(buckets) / 12 if sum(buckets) > 0 else 1
        vol_mult = c5 / avg5 if avg5 > 0 else 0

        out = []
        if abs(r5) >= PRICE_5M_PCT:
            out.append(("price5",
                        f"{self.symbol} {'急涨' if r5 > 0 else '急跌'} {r5:+.2f}%（5分钟）",
                        f"现价 {last_price:.2f}，5 分钟涨跌 {r5:+.2f}%，15 分钟 {r15:+.2f}%"))
        elif abs(r15) >= PRICE_15M_PCT:
            out.append(("price15",
                        f"{self.symbol} {'大涨' if r15 > 0 else '大跌'} {r15:+.2f}%（15分钟）",
                        f"现价 {last_price:.2f}，15 分钟涨跌 {r15:+.2f}%"))
        if vol_mult >= VOL_MULT and abs(r5) >= VOL_PRICE_MIN:
            out.append(("volume",
                        f"{self.symbol} 放量异动 x{vol_mult:.1f}",
                        f"近 5 分钟成交 {c5} 笔，为均值 {avg5:.0f} 笔的 {vol_mult:.1f} 倍，价格 {r5:+.2f}%"))

        # 冷却过滤
        res = []
        for kind, title, body in out:
            if now - self.last_alert.get(kind, 0) >= COOLDOWN_SEC:
                self.last_alert[kind] = now
                res.append((kind, title, body))
        return res


def bark_push(bark_key, title, body):
    if not bark_key:
        log("BARK_KEY 未设置，跳过推送 |", title)
        return False
    try:
        data = json.dumps({"device_key": bark_key, "title": title,
                           "body": body, "group": "美股异动"}, ensure_ascii=False).encode()
        req = urllib.request.Request(BARK_PUSH, data=data,
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        with urllib.request.urlopen(req, timeout=15) as r:
            ok = r.status == 200
        log("Bark 推送", "成功" if ok else f"失败({r.status})", "|", title)
        return ok
    except Exception as e:
        log("Bark 推送异常:", str(e)[:120], "|", title)
        return False


def fetch_prev_close(finnhub_key, symbol):
    try:
        url = FINNHUB_QUOTE.format(sym=symbol, key=urllib.parse.quote(finnhub_key))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            d = json.loads(r.read().decode())
        pc = d.get("pc")
        return float(pc) if pc else None
    except Exception as e:
        log(symbol, "取 prev_close 失败:", str(e)[:80])
        return None


def write_latest(trackers, source_note):
    now_utc = datetime.now(timezone.utc)
    quotes = {}
    for sym, tr in trackers.items():
        trades = tr.snapshot()
        price = trades[-1][1] if trades else None
        pc = tr.prev_close
        chg = (price - pc) / pc * 100 if (price and pc) else None
        # 当日 5 分钟平均笔数用于 vol_ratio 参考
        now = time.time()
        c5 = sum(1 for t, _, _ in trades if t >= now - 300)
        quotes[sym] = {
            "price": round(price, 2) if price else None,
            "prev_close": pc,
            "change_pct": round(chg, 2) if chg is not None else None,
            "volume": int(tr.day_volume),
            "trades_5m": c5,
            "source": "finnhub-rt",
            "alerts": {},
        }
    payload = {
        "updated_at": now_utc.isoformat(),
        "updated_at_utc": now_utc.isoformat(),
        "source": "finnhub-rt",
        "note": source_note,
        "quotes": quotes,
    }
    tmp = LATEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(LATEST)


def git_sync():
    try:
        env = dict(os.environ, GIT_ASKPASS=str(Path.home() / ".config/github/askpass.sh"))
        subprocess.run(["git", "add", "data/stock-latest.json"], cwd=ROOT,
                       capture_output=True, env=env, timeout=30)
        r = subprocess.run(["git", "diff", "--staged", "--quiet"], cwd=ROOT,
                           capture_output=True, env=env, timeout=30)
        if r.returncode != 0:
            subprocess.run(["git", "-c", "user.name=GitHub Actions Bot",
                            "-c", "user.email=github-actions[bot]@users.noreply.github.com",
                            "commit", "-m", "chore: rt stock update",
                            "--", "data/stock-latest.json"],
                           cwd=ROOT, capture_output=True, env=env, timeout=60)
            subprocess.run(["git", "push", "origin", "main"], cwd=ROOT,
                           capture_output=True, env=env, timeout=90)
            log("数据已同步推送")
    except Exception as e:
        log("git 同步失败:", str(e)[:100])


def main():
    finnhub_key, bark_key = load_keys()
    if not finnhub_key:
        log("FATAL: 缺少 Finnhub key（~/.config/stock/keys.json），退出")
        sys.exit(3)
    symbols = load_symbols()
    log("监听:", ",".join(symbols))

    trackers = {s: Tracker(s) for s in symbols}
    # 取 prev_close（每天一次）
    pc_day = ""
    stop = threading.Event()

    def on_message(ws, message):
        try:
            msg = json.loads(message)
        except Exception:
            return
        if msg.get("type") != "trade":
            return
        now = time.time()
        for t in msg.get("data", []):
            sym, p, v, ts = t.get("s"), t.get("p"), t.get("v", 0), t.get("t", 0) / 1000
            if sym in trackers and p:
                trackers[sym].add(ts or now, float(p), float(v or 0))

    def on_error(ws, error):
        log("WS 错误:", str(error)[:120])

    def on_close(ws, status, msg):
        log("WS 关闭:", status, str(msg)[:80])

    def on_open(ws):
        log("WS 已连接，订阅", len(symbols), "只")
        for s in symbols:
            ws.send(json.dumps({"type": "subscribe", "symbol": s}))

    def evaluator():
        last_json, last_sync = 0, 0
        while not stop.wait(EVAL_SEC):
            nonlocal pc_day
            now = time.time()
            # 每天刷新一次 prev_close
            day = datetime.now(ET).strftime("%Y-%m-%d")
            if day != pc_day:
                pc_day = day
                for s, tr in trackers.items():
                    pc = fetch_prev_close(finnhub_key, s)
                    if pc:
                        tr.prev_close = pc
                for tr in trackers.values():
                    tr.day_volume = 0.0
                log("prev_close 已刷新", day)
            if market_open_now():
                for sym, tr in trackers.items():
                    for kind, title, body in tr.evaluate(now):
                        log("异动:", title)
                        bark_push(bark_key, "美股异动 " + title, body)
            if now - last_json >= JSON_SEC:
                last_json = now
                try:
                    write_latest(trackers, "Finnhub 实时 websocket；页面降级读取本文件")
                except Exception as e:
                    log("写 stock-latest.json 失败:", str(e)[:80])
            if market_open_now() and now - last_sync >= SYNC_SEC:
                last_sync = now
                git_sync()

    threading.Thread(target=evaluator, daemon=True).start()

    backoff = 5
    while not stop.is_set():
        try:
            ws = websocket.WebSocketApp(
                FINNHUB_WS.format(key=urllib.parse.quote(finnhub_key)),
                on_open=on_open, on_message=on_message,
                on_error=on_error, on_close=on_close)
            ws.run_forever(ping_interval=25, ping_timeout=10)
        except Exception as e:
            log("WS 异常:", str(e)[:120])
        log(f"{backoff}s 后重连")
        time.sleep(backoff)
        backoff = min(backoff * 2, 120)


if __name__ == "__main__":
    if "--check" in sys.argv:
        fh, bk = load_keys()
        print("finnhub key:", "已配置" if fh else "缺失")
        print("bark key:", "已配置" if bk else "缺失")
        print("symbols:", load_symbols())
        print("market open now (ET):", market_open_now())
        sys.exit(0 if fh else 3)
    main()
