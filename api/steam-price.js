// Steam 查价代理（Vercel Serverless, Node.js）
// 浏览器直调 store.steampowered.com 会被 CORS 拦截，前端统一走 /api/steam-price?appid=xxx
// 可选 full=1 返回完整数据（含游戏名），默认只返回 price_overview。

export default async function handler(req, res) {
  const appid = String((req.query && req.query.appid) || '');
  if (!/^\d{1,10}$/.test(appid)) {
    return res.status(400).json({ error: 'appid 非法' });
  }
  const full = String((req.query && req.query.full) || '') === '1';
  const url =
    'https://store.steampowered.com/api/appdetails?appids=' + appid +
    '&cc=cn' + (full ? '' : '&filters=price_overview');
  try {
    const r = await fetch(url, { headers: { 'User-Agent': 'xiaojj-price-watch/1.0' } });
    if (!r.ok) return res.status(502).json({ error: 'Steam 接口请求失败' });
    const data = await r.json();
    res.setHeader('Cache-Control', 's-maxage=300');
    return res.status(200).json(data);
  } catch (e) {
    return res.status(502).json({ error: 'Steam 接口请求失败' });
  }
}
