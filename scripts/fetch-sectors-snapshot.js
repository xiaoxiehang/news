// 每日行情快照：从本机拉 Yahoo v8 chart（本机出口可用），写入 data/sectors.json。
// 由 cron 每日执行两次（美股收盘后、亚洲收盘后），commit + push 后 Vercel 自动部署。
// stock.html 只读这份静态 JSON，不再经过 Vercel Serverless 打 Yahoo
//（Yahoo 会封 Vercel 机房 IP，serverless 方案已废弃，见 api/sectors.js 删除记录）。
//
// 用法：node scripts/fetch-sectors-snapshot.js

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT = path.join(__dirname, '..', 'data', 'sectors.json');

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';
const HOSTS = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com'];
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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchQuoteOnce(symbol, host) {
  const url = 'https://' + host + '/v8/finance/chart/' +
    encodeURIComponent(symbol) + '?interval=1d&range=5d';
  const r = await fetch(url, {
    headers: { 'User-Agent': UA },
    signal: AbortSignal.timeout(10000),
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

async function fetchQuote(symbol) {
  let lastErr = null;
  for (const host of HOSTS) {
    try {
      return await fetchQuoteOnce(symbol, host);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr;
}

async function main() {
  const all = [];
  for (const g of GROUPS) {
    for (const it of g.items) all.push({ group: g.id, name: it.name, symbol: it.symbol });
  }
  const okItems = [];
  for (let i = 0; i < all.length; i += BATCH) {
    const batch = all.slice(i, i + BATCH);
    const settled = await Promise.allSettled(batch.map(async (it) => {
      const q = await fetchQuote(it.symbol);
      return { group: it.group, name: it.name, code: displayCode(it.symbol), ...q };
    }));
    for (const s of settled) {
      if (s.status === 'fulfilled') okItems.push(s.value);
      else console.error('FAILED', s.reason && s.reason.message);
    }
    if (i + BATCH < all.length) await sleep(BATCH_GAP_MS);
  }
  if (!okItems.length) {
    console.error('snapshot failed: no quotes');
    process.exit(1);
  }
  const byId = (id) =>
    okItems.filter((i) => i.group === id).sort((a, b) => b.change_pct - a.change_pct);
  const payload = {
    ok: true,
    updated_at: new Date().toISOString(),
    partial: okItems.length < all.length,
    groups: GROUPS.map((g) => ({ id: g.id, name: g.name, items: byId(g.id) })),
  };
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, JSON.stringify(payload));
  console.log('snapshot ok:', okItems.length + '/' + all.length, '->', OUT);
}

main();
