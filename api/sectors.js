// GET /api/sectors — 全球股市板块热度代理（Vercel Serverless）
//
// 一次并行拉 Yahoo v8 chart（每个标的 1 个请求），无 key、服务端 UA。
// 边缘缓存 5 分钟：盘中数据不需要秒级新鲜，缓存省掉重复打 Yahoo。
// 任一标的失败只丢该标的；全部失败才返回 503，前端显示错误重试——
// 假装实时比诚实报错更糟。

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

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

async function fetchQuote(symbol) {
  const url = 'https://query1.finance.yahoo.com/v8/finance/chart/' +
    encodeURIComponent(symbol) + '?interval=1d&range=5d';
  const r = await fetch(url, {
    headers: { 'User-Agent': UA },
    signal: AbortSignal.timeout(9000),
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

export default async function handler(req, res) {
  try {
    const all = [];
    for (const g of GROUPS) {
      for (const it of g.items) all.push({ group: g.id, name: it.name, symbol: it.symbol });
    }
    const settled = await Promise.allSettled(all.map(async (it) => {
      const q = await fetchQuote(it.symbol);
      return { group: it.group, name: it.name, code: displayCode(it.symbol), ...q };
    }));
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
