// GET /api/sectors — 股市板块与全球股指实时代理（Vercel Serverless）
//
// 每次请求都实时打 1 次新浪 hq.sinajs.cn（单次 list 请求拉全部 21 个代码）。
// 无任何缓存：无边缘缓存、无进程内缓存、无静态回退。
// 新浪无 CORS 头，必须走服务端；返回 GBK 编码，需 Referer。
// 查不到/解析失败时返回 503，前端显示错误重试——绝不拿旧快照顶上。
//
// 代码核对（2026-11-08，本机 Yahoo 日线收盘价交叉核对）：
// - 11 只 ETF 用 gb_*：现价 [1]、涨跌幅% [2]，与 Yahoo 11-06 收盘价、11-05 收盘价逐个一致。
// - 美股指数用 gb_inx（标普500）、gb_ndx（纳斯达克100）、gb_dji（道琼斯），同上格式。
//   注意：gb_ixic 是纳斯达克综合指数（24579），不是纳斯达克100（26989），必须用 gb_ndx。
// - 上证 sh000001：[1]=今开、[2]=昨收、[3]=现价，涨跌幅自行算 (现价-昨收)/昨收。
// - 恒生 rt_hkHSI：[6]=现价、[7]=涨跌额、[8]=涨跌幅%（[2] 是今开，不是现价）。
// - 其余 5 个用 b_*：[1]=现价、[2]=涨跌额、[3]=涨跌幅%；int_* 系列已 stale（日经 44946 对不上），不用。
//   b_SX5E 现价比 Yahoo 收盘低约 0.06%（新浪快照时刻略早），昨收完全一致，可接受。
// - 另：Yahoo v8 chart 的 meta.chartPreviousClose 在本机实测是 stale 值
//   （如 XLK 179.51，真实 11-05 收盘 162.38），旧快照脚本用它算出的涨跌幅是错的
//   （XLK -8.23% 应为 +1.45%）；新浪 [2] 与 Yahoo 日线收盘逐个核对一致，以新浪为准。

const GROUPS = [
  {
    id: 'sectors', name: '美股行业板块',
    items: [
      { code: 'XLK', name: '科技', sina: 'gb_xlk', currency: 'USD' },
      { code: 'XLC', name: '通信服务', sina: 'gb_xlc', currency: 'USD' },
      { code: 'XLY', name: '非必需消费品', sina: 'gb_xly', currency: 'USD' },
      { code: 'XLP', name: '必需消费品', sina: 'gb_xlp', currency: 'USD' },
      { code: 'XLE', name: '能源', sina: 'gb_xle', currency: 'USD' },
      { code: 'XLF', name: '金融', sina: 'gb_xlf', currency: 'USD' },
      { code: 'XLV', name: '医疗保健', sina: 'gb_xlv', currency: 'USD' },
      { code: 'XLI', name: '工业', sina: 'gb_xli', currency: 'USD' },
      { code: 'XLB', name: '原材料', sina: 'gb_xlb', currency: 'USD' },
      { code: 'XLRE', name: '房地产', sina: 'gb_xlre', currency: 'USD' },
      { code: 'XLU', name: '公用事业', sina: 'gb_xlu', currency: 'USD' },
    ],
  },
  {
    id: 'indices', name: '全球主要股指',
    items: [
      { code: 'GSPC', name: '标普 500', sina: 'gb_inx', currency: 'USD' },
      { code: 'NDX', name: '纳斯达克 100', sina: 'gb_ndx', currency: 'USD' },
      { code: 'DJI', name: '道琼斯工业', sina: 'gb_dji', currency: 'USD' },
      { code: 'STOXX50E', name: '欧洲斯托克 50', sina: 'b_SX5E', currency: 'EUR' },
      { code: 'GDAXI', name: '德国 DAX', sina: 'b_DAX', currency: 'EUR' },
      { code: 'FTSE', name: '英国富时 100', sina: 'b_UKX', currency: 'GBP' },
      { code: 'N225', name: '日经 225', sina: 'b_NKY', currency: 'JPY' },
      { code: 'KS11', name: '韩国综合指数', sina: 'b_KOSPI', currency: 'KRW' },
      { code: '000001', name: '上证指数', sina: 'sh000001', currency: 'CNY' },
      { code: 'HSI', name: '恒生指数', sina: 'rt_hkHSI', currency: 'HKD' },
    ],
  },
];

const ALL = GROUPS.flatMap((g) => g.items.map((it) => ({ group: g.id, ...it })));

// 按新浪代码前缀解析一行 hq_str_* 返回值，返回 { price, change_pct } 或 null。
function parseQuote(sina, fields) {
  const num = (i) => {
    const v = parseFloat(fields[i]);
    return Number.isFinite(v) ? v : null;
  };
  if (sina.startsWith('gb_')) {
    const price = num(1);
    const changePct = num(2);
    if (price == null || changePct == null) return null;
    return { price, change_pct: Math.round(changePct * 100) / 100 };
  }
  if (sina.startsWith('b_')) {
    const price = num(1);
    const changePct = num(3);
    if (price == null || changePct == null) return null;
    return { price, change_pct: Math.round(changePct * 100) / 100 };
  }
  if (sina === 'sh000001') {
    const prev = num(2);
    const price = num(3);
    if (price == null || prev == null || prev === 0) return null;
    return { price, change_pct: Math.round(((price - prev) / prev) * 10000) / 100 };
  }
  if (sina === 'rt_hkHSI') {
    const price = num(6);
    const changePct = num(8);
    if (price == null || changePct == null) return null;
    return { price, change_pct: Math.round(changePct * 100) / 100 };
  }
  return null;
}

function noStore(res) {
  res.setHeader('Cache-Control', 'no-store');
}

export default async function handler(req, res) {
  try {
    const codes = ALL.map((it) => it.sina).join(',');
    const url = 'https://hq.sinajs.cn/list=' + codes;
    const r = await fetch(url, {
      headers: {
        'Referer': 'https://finance.sina.com.cn',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      },
      signal: AbortSignal.timeout(10000),
    });
    if (!r.ok) throw new Error('sina http ' + r.status);
    const buf = await r.arrayBuffer();
    let text;
    try {
      text = new TextDecoder('gbk').decode(buf);
    } catch (e) {
      // GBK 解码不可用时退回 latin1：数字字段是 ASCII，解析不受影响（仅中文名会乱码，
      // 而展示名用的是本地硬编码，不依赖新浪返回的名字）。
      text = new TextDecoder('latin1').decode(buf);
    }
    const byCode = {};
    for (const line of text.split('\n')) {
      const m = line.match(/var hq_str_([^=]+)="([^"]*)"/);
      if (m) byCode[m[1]] = m[2].split(',');
    }
    const okItems = [];
    for (const it of ALL) {
      const fields = byCode[it.sina];
      if (!fields) continue;
      const q = parseQuote(it.sina, fields);
      if (!q) continue;
      okItems.push({
        group: it.group,
        name: it.name,
        code: it.code,
        price: Math.round(q.price * 100) / 100,
        change_pct: q.change_pct,
        currency: it.currency,
      });
    }
    if (!okItems.length) throw new Error('sina empty: no quotes parsed');
    const byId = (id) =>
      okItems.filter((i) => i.group === id).sort((a, b) => b.change_pct - a.change_pct);
    const body = {
      ok: true,
      realtime: true,
      updated_at: new Date().toISOString(),
      partial: okItems.length < ALL.length,
      groups: GROUPS.map((g) => ({ id: g.id, name: g.name, items: byId(g.id) })),
    };
    noStore(res);
    return res.status(200).json(body);
  } catch (e) {
    noStore(res);
    return res.status(503).json({ ok: false, error: (e && e.message) || 'sectors failed' });
  }
}
