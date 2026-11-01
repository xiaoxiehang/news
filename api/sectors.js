// GET /api/sectors — 全球股市板块热度代理（Vercel Serverless）
//
// 分批并行拉 Yahoo v8 chart（每批 4 个，批间歇 300ms），无 key、服务端 UA；
// 单个失败换 host（query1/query2）重试一次。
// 边缘缓存 5 分钟：盘中数据不需要秒级新鲜，缓存省掉重复打 Yahoo。
// 任一标的失败只丢该标的；全部失败才返回 503，前端显示错误重试——
// 假装实时比诚实报错更糟。

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const HOSTS = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com'];
// Yahoo 对机房 IP 并发限流：分批拉，失败换 host 重试一次。
const BATCH = 4;
const BATCH_GAP_MS = 200;

const GROUPS = [
  {
    id: 'sectors', name: '美股行业板块',
    items: [
      { symbol: 'XLK', name: '科技' },
      { symbol: 'XLC', name: '通信服务' },
      { symbol: 'XLY', name: '非必需消费品' },
      { symbol: 'XLP', name: '必需消费品' },
      { symbol: 'XLE', name: '能源' },
      { symbol: 'XLF', name: '金融' },
      { symbol: 'XLV', name: '医疗保健' },
      { symbol: 'XLI', name: '工业' },
      { symbol: 'XLB', name: '原材料' },
      { symbol: 'XLRE', name: '房地产' },
      { symbol: 'XLU', name: '公用事业' },
    ],
  },
  {
    id: 'indices', name: '全球主要股指',
    items: [
      { symbol: '^GSPC', name: '标普 500' },
      { symbol: '^NDX', name: '纳斯达克 100' },
      { symbol: '^DJI', name: '道琼斯工业' },
      { symbol: '^STOXX50E', name: '欧洲斯托克 50' },
      { symbol: '^GDAXI', name: '德国 DAX' },
      { symbol: '^FTSE', name: '英国富时 100' },
      { symbol: '^N225', name: '日经 225' },
      { symbol: '^KS11', name: '韩国综合指数' },
      { symbol: '000001.SS', name: '上证指数' },
      { symbol: '^HSI', name: '恒生指数' },
    ],
  },
];

function displayCode(symbol) {
  return symbol.replace(/^\^/, '').replace(/\.SS$/, '');
}

async function getYahooAuth() {
  // fc.yahoo.com 经常回 404，但会照常 Set-Cookie；只取 cookie，不校验状态码。
  const r = await fetch('https://fc.yahoo.com', {
    headers: { 'User-Agent': UA },
    signal: AbortSignal.timeout(5000),
  });
  const setCookie = r.headers.get('set-cookie') || '';
  const cookie = setCookie.split(';')[0];
  if (!cookie) throw new Error('no yahoo cookie');
  let lastErr = null;
  for (const host of HOSTS) {
    try {
      const r2 = await fetch('https://' + host + '/v1/test/getcrumb', {
        headers: { 'User-Agent': UA, Cookie: cookie },
        signal: AbortSignal.timeout(5000),
      });
      if (!r2.ok) throw new Error('crumb ' + r2.status);
      const crumb = (await r2.text()).trim();
      if (!crumb || crumb.length > 64) throw new Error('bad crumb');
      return { crumb, cookie };
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

async function fetchQuoteOnce(symbol, host, auth) {
  let url = 'https://' + host + '/v8/finance/chart/' +
    encodeURIComponent(symbol) + '?interval=1d&range=5d';
  const headers = { 'User-Agent': UA };
  if (auth) {
    url += '&crumb=' + encodeURIComponent(auth.crumb);
    headers.Cookie = auth.cookie;
  }
  const r = await fetch(url, {
    headers,
    signal: AbortSignal.timeout(8000),
  });
  if (!r.ok) throw new Error('yahoo ' + r.status + ' for ' + symbol);
  const j = await r.json();
  const meta = j && j.chart && j.chart.result && j.chart.result[0] && j.chart.result[0].meta;
  if (!meta || meta.regularMarketPrice == null || meta.chartPreviousClose == null) {
    throw new Error('bad meta for ' + symbol);
  }
  const price = meta.regularMarketPrice;
  const prev = meta.chartPreviousClose;
  return {
    price: Math.round(price * 100) / 100,
    change_pct: Math.round(((price - prev) / prev) * 10000) / 100,
    currency: meta.currency || '',
    market_time: meta.regularMarketTime || null,
  };
}

async function fetchQuote(symbol, auth) {
  // auth 由 decideStrategy 统一决策：全体用同一种策略，不再逐标的试错。
  let lastErr = null;
  for (const host of HOSTS) {
    try {
      return await fetchQuoteOnce(symbol, host, auth);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

// 策略决策：会话和裸奔并行探路，哪个先通全体就用哪个。
// 返回 auth 对象（走会话）、null（裸奔）或 'fail'（都走不通）。
async function decideStrategy() {
  const authPending = getYahooAuth();
  authPending.catch(() => {}); // 避免后台未处理 rejection
  const plainProbe = fetchQuoteOnce('XLK', 'query1.finance.yahoo.com', null)
    .then(() => true)
    .catch(() => false);
  // 会话最多等 2.5s，超时不等了（裸奔探针同时在跑）
  const authFast = await Promise.race([
    authPending.then((a) => a).catch(() => null),
    sleep(2500).then(() => 'slow'),
  ]);
  const plainOk = await plainProbe;
  if (plainOk) return null;
  if (authFast && authFast !== 'slow') {
    const ok = await fetchQuoteOnce('XLK', 'query1.finance.yahoo.com', authFast)
      .then(() => true)
      .catch(() => false);
    if (ok) return authFast;
    return 'fail';
  }
  // 会话来得慢：再宽限 4s，行就行、不行就认
  const auth = await Promise.race([
    authPending.catch(() => null),
    sleep(4000).then(() => null),
  ]);
  if (auth) {
    const ok = await fetchQuoteOnce('XLK', 'query1.finance.yahoo.com', auth)
      .then(() => true)
      .catch(() => false);
    if (ok) return auth;
  }
  return 'fail';
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// 分批并行：每批 BATCH 个，批间歇 BATCH_GAP_MS，避免触发 Yahoo 并发限流。
async function fetchAllBatched(items, auth) {
  const out = new Array(items.length);
  for (let i = 0; i < items.length; i += BATCH) {
    const batch = items.slice(i, i + BATCH);
    const settled = await Promise.allSettled(batch.map(async (it) => {
      const q = await fetchQuote(it.symbol, auth);
      return { group: it.group, name: it.name, code: displayCode(it.symbol), ...q };
    }));
    settled.forEach((s, k) => { out[i + k] = s; });
    if (i + BATCH < items.length) await sleep(BATCH_GAP_MS);
  }
  return out;
}

export default async function handler(req, res) {
  try {
    const all = [];
    for (const g of GROUPS) {
      for (const it of g.items) all.push({ group: g.id, name: it.name, symbol: it.symbol });
    }
    // 先决策走会话还是裸奔（两种出口环境自适应），再分批拉全量。
    const strategy = await decideStrategy();
    if (strategy === 'fail') {
      res.status(503).json({ ok: false, error: 'quote_unavailable' });
      return;
    }
    const settled = await fetchAllBatched(all, strategy);
    const okItems = settled
      .filter((s) => s.status === 'fulfilled')
      .map((s) => s.value);
    if (!okItems.length) {
      res.status(503).json({ ok: false, error: 'quote_unavailable' });
      return;
    }
    const byId = (id) =>
      okItems.filter((i) => i.group === id).sort((a, b) => b.change_pct - a.change_pct);
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=3600');
    res.status(200).json({
      ok: true,
      updated_at: new Date().toISOString(),
      partial: okItems.length < all.length,
      groups: GROUPS.map((g) => ({ id: g.id, name: g.name, items: byId(g.id) })),
    });
  } catch (e) {
    res.status(503).json({ ok: false, error: 'quote_unavailable' });
  }
}
