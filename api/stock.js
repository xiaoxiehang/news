// 美股行情代理（Vercel Serverless, Node.js）
// 浏览器直连 Stooq/Yahoo 会被 CORS 拦截，前端统一请求 /api/stock?symbols=AAPL,NVDA。
// 服务端先试 Stooq 批量 CSV，失败则逐只降级 Yahoo Finance v8 chart。
// 无需任何环境变量。

const UA = { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36' };
const TIMEOUT_MS = 10000;
const MAX_SYMBOLS = 20;

function withTimeout(ms) {
  const c = new AbortController();
  const t = setTimeout(() => c.abort(), ms);
  return { signal: c.signal, done: () => clearTimeout(t) };
}

async function fetchStooq(symbols) {
  const syms = symbols.map((s) => s.toLowerCase() + '.us').join(',');
  const url = `https://stooq.com/q/l/?s=${syms}&f=sd2t2ohlcv&h&e=csv`;
  const { signal, done } = withTimeout(TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: UA, signal });
    if (!r.ok) throw new Error('stooq http ' + r.status);
    const text = (await r.text()).trim();
    if (!text || text.startsWith('<')) throw new Error('stooq 非 CSV');
    const lines = text.split('\n').filter((l) => l.trim());
    const header = lines[0].split(',').map((h) => h.trim().toLowerCase());
    const iS = header.indexOf('symbol'), iC = header.indexOf('close'), iV = header.indexOf('volume');
    if (iS < 0 || iC < 0 || iV < 0) throw new Error('stooq 表头异常');
    const out = {};
    for (const ln of lines.slice(1)) {
      const p = ln.split(',');
      if (p.length <= Math.max(iS, iC, iV)) continue;
      const sym = p[iS].trim().toUpperCase().replace('.US', '');
      const price = parseFloat(p[iC]), vol = parseInt(p[iV], 10);
      if (sym && price > 0) out[sym] = { price: Math.round(price * 100) / 100, volume: vol || 0 };
    }
    if (!Object.keys(out).length) throw new Error('stooq 0 条');
    return out;
  } finally {
    done();
  }
}

async function fetchYahoo(sym) {
  const url = `https://query1.finance.yahoo.com/v8/finance/chart/${sym}?interval=1d&range=5d`;
  const { signal, done } = withTimeout(TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: UA, signal });
    if (!r.ok) throw new Error('yahoo http ' + r.status);
    const j = await r.json();
    const meta = j.chart.result[0].meta;
    const price = meta.regularMarketPrice;
    const prevClose = meta.previousClose || meta.chartPreviousClose;
    if (!price || !prevClose) throw new Error('yahoo 缺字段');
    const vols = (j.chart.result[0].indicators.quote[0].volume || []).filter((v) => v);
    const fullDays = vols.length > 1 ? vols.slice(0, -1) : [];
    const base = fullDays.slice(-5);
    const volBase = base.length ? Math.round(base.reduce((a, b) => a + b, 0) / base.length) : 0;
    return {
      price: Math.round(price * 100) / 100,
      prev_close: Math.round(prevClose * 100) / 100,
      change_pct: Math.round(((price - prevClose) / prevClose) * 10000) / 100,
      volume: meta.regularMarketVolume || 0,
      vol_base: volBase,
    };
  } finally {
    done();
  }
}

export default async function handler(req, res) {
  if (req.method !== 'GET') return res.status(405).json({ error: '只支持 GET' });
  const raw = String(req.query.symbols || '');
  const symbols = [...new Set(raw.split(',').map((s) => s.trim().toUpperCase()))]
    .filter((s) => /^[A-Z]{1,6}(\.[A-Z])?$/.test(s))
    .slice(0, MAX_SYMBOLS);
  if (!symbols.length) return res.status(400).json({ error: 'symbols 参数无效，如 ?symbols=AAPL,NVDA' });

  const quotes = {};
  let stooqOk = false;
  try {
    const sq = await fetchStooq(symbols);
    stooqOk = true;
    for (const s of symbols) if (sq[s]) quotes[s] = { ...sq[s], source: 'stooq', degraded: true };
  } catch (e) {
    // 降级到 Yahoo
  }
  await Promise.all(
    symbols.filter((s) => !quotes[s]).map(async (s) => {
      try {
        quotes[s] = { ...(await fetchYahoo(s)), source: 'yahoo' };
      } catch (e) {
        quotes[s] = { error: '行情获取失败' };
      }
    })
  );

  res.setHeader('Cache-Control', 's-maxage=30, stale-while-revalidate=60');
  return res.status(200).json({ ok: true, source: stooqOk ? 'stooq+yahoo' : 'yahoo', quotes });
}
