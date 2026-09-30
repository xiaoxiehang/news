// TMDB API 代理（Vercel Serverless, Node.js）
// 前端统一请求 /api/tmdb?path=/movie/popular&language=zh-CN...，
// 本接口校验 path 白名单后转发到 api.themoviedb.org，API key 只存在服务端。
//
// 环境变量：
//   TMDB_API_KEY  必填（themoviedb.org → Settings → API → API Key (v3 auth)）

const TMDB_BASE = 'https://api.themoviedb.org/3';

// 允许前端调用的接口白名单（防止 key 被滥用）
const ALLOWED = [
  /^\/trending\/movie\/(day|week)$/,
  /^\/movie\/(popular|top_rated|upcoming|now_playing)$/,
  /^\/movie\/\d+$/,
  /^\/search\/movie$/,
  /^\/genre\/movie\/list$/,
  /^\/discover\/movie$/,
];

export default async function handler(req, res) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    return res.status(405).json({ error: '只支持 GET/POST' });
  }
  const apiKey = process.env.TMDB_API_KEY || '';
  if (!apiKey) {
    return res.status(500).json({ error: '服务端未配置 TMDB_API_KEY' });
  }

  const q = req.method === 'GET' ? req.query : { ...req.query, ...req.body };
  const path = String(q.path || '');
  if (!ALLOWED.some((re) => re.test(path))) {
    return res.status(400).json({ error: '接口不在白名单内' });
  }

  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(q)) {
    if (k === 'path' || v === undefined || v === null) continue;
    params.append(k, String(v));
  }
  if (!params.has('language')) params.set('language', 'zh-CN');
  params.set('api_key', apiKey);

  try {
    const r = await fetch(`${TMDB_BASE}${path}?${params.toString()}`, {
      headers: { Accept: 'application/json' },
    });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      return res.status(r.status).json({ error: data.status_message || 'TMDB 请求失败' });
    }
    // 列表类数据 CDN 缓存 10 分钟，减轻配额压力
    res.setHeader('Cache-Control', 's-maxage=600, stale-while-revalidate=3600');
    return res.status(200).json(data);
  } catch (e) {
    console.error('tmdb proxy failed:', e?.message || e);
    return res.status(502).json({ error: '请求 TMDB 失败，请稍后重试' });
  }
}
