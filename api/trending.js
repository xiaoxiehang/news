// GET /api/trending?tab=rising|leaderboard|<categoryId> — GitHub 趋势实时代理（Vercel Serverless）
//
// 点哪个 tab 查哪个 tab：每次只打 1 个 GitHub 搜索（之前是 13 个全量）。
// 服务端持有 GITHUB_TOKEN（Vercel 环境变量），浏览器只调本接口，token 不暴露。
// 缓存：边缘 5 分钟 + 进程内 5 分钟（按 tab 分开）。
// 查不到/被限流时返回 503，前端显示错误重试，不再回退静态快照——
// 假装实时比诚实报错更糟。

const CATEGORIES = [
  // 注意：不加引号的多词会被 GitHub 当 AND 处理（machine learning 会误中
  // "machine image" + README 里的 learning），短语必须加引号。
  { id: 'ai', name: 'AI 机器学习', desc: '大模型、机器学习框架', query: '"machine learning" OR "deep learning" OR LLM stars:>1000', sort: 'stars' },
  { id: 'ai-apps', name: 'AI 应用', desc: 'AI 智能体、AI 工具', query: 'ai agent OR llm app OR chatbot stars:>500', sort: 'stars' },
  { id: 'frontend-mobile', name: '前端移动', desc: '前端、移动端、全栈', query: 'react OR vue OR flutter OR react-native OR nextjs stars:>2000', sort: 'stars' },
  { id: 'backend-infra', name: '后端基建', desc: '后端、数据库、云原生', query: 'kubernetes OR docker OR postgres OR redis OR microservice stars:>2000', sort: 'stars' },
  { id: 'devtools', name: '开发者工具', desc: '开发工具、效率自动化', query: 'cli OR developer tool OR productivity OR automation stars:>1000', sort: 'stars' },
  { id: 'game', name: '游戏', desc: '游戏引擎、游戏开发', query: 'game engine OR godot OR gamedev stars:>1000', sort: 'stars' },
  { id: 'healthcare', name: '医疗健康', desc: '医疗、健康信息化', query: 'topic:healthcare stars:>50', sort: 'stars' },
  { id: 'fintech', name: '金融科技', desc: '交易、量化、金融工具', query: 'topic:fintech stars:>50', sort: 'stars' },
  { id: 'education', name: '教育学习', desc: '在线教育、课程、教程', query: 'topic:education stars:>100', sort: 'stars' },
  { id: 'research', name: '科学研究', desc: '科研工具、数据集', query: 'topic:science stars:>50', sort: 'stars' },
  { id: 'media', name: '影音娱乐', desc: '视频、流媒体、媒体中心', query: 'topic:video OR topic:audio OR topic:music OR topic:podcast OR topic:video-player OR topic:iptv stars:>100', sort: 'stars' },
];

// 分类修正表：full_name -> 正确分类。只做"过滤"（把放错 tab 的拿掉），
// 不做跨分类"搬运"——实测那 16 个历史误配项在实时查询里根本不出现，
// 为极小概率多打十几个 /repos 查询不划算。
const CATEGORY_OVERRIDES = {
  'apache/iggy': 'backend-infra',
  'travisjeffery/jocko': 'backend-infra',
  'memgraph/memgraph': 'backend-infra',
  'Cysharp/MagicOnion': 'backend-infra',
  'apache/streampark': 'backend-infra',
  'lakesoul-io/LakeSoul': 'backend-infra',
  'apache/incubator-heron': 'backend-infra',
  'fastly/pushpin': 'backend-infra',
  'piskvorky/smart_open': 'backend-infra',
  'adaltas/node-csv': 'backend-infra',
  'iusztinpaul/hands-on-llms': 'ai',
  'TanStack/ai': 'ai-apps',
  'OpenMOSS/MOSS-TTS': 'ai',
  'hashicorp/packer': 'backend-infra',
  'prometheus/node_exporter': 'backend-infra',
  'rathena/rathena': 'game',
  'noob-hackers/infect': 'devtools',
  'flink-china/flink-training-course': 'education',
};

function recentDate(days) {
  const d = new Date(Date.now() - days * 86400000);
  return d.toISOString().slice(0, 10);
}

function pick(it) {
  return {
    name: it.name,
    full_name: it.full_name,
    owner: (it.owner && it.owner.login) || '',
    description: (it.description || '').slice(0, 200),
    html_url: it.html_url,
    language: it.language || null,
    stars: it.stargazers_count || 0,
    forks: it.forks_count || 0,
    topics: (it.topics || []).slice(0, 5),
    created_at: (it.created_at || '').slice(0, 10),
    updated_at: (it.updated_at || '').slice(0, 10),
  };
}

async function search(query, sort, perPage, headers) {
  const url = 'https://api.github.com/search/repositories?q=' +
    encodeURIComponent(query) + '&sort=' + sort + '&order=desc&per_page=' + perPage;
  const r = await fetch(url, { headers });
  if (r.status === 403 || r.status === 429) {
    const e = new Error('github rate limited');
    e.rateLimited = true;
    throw e;
  }
  if (!r.ok) throw new Error('github api ' + r.status);
  const data = await r.json();
  return (data.items || []).map(pick);
}

function setCacheHeaders(res) {
  res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=60');
  res.setHeader('CDN-Cache-Control', 'max-age=300');
}

// 进程内缓存，按 tab 分开（防同一实例连续打）
let memCache = {};

export default async function handler(req, res) {
  try {
    const tab = String((req.query && req.query.tab) || 'rising');

    const hit = memCache[tab];
    if (hit && Date.now() - hit.at < 5 * 60 * 1000) {
      setCacheHeaders(res);
      res.setHeader('X-Trending-Cache', 'memory');
      return res.status(200).json(hit.body);
    }

    const token = process.env.GITHUB_TOKEN || '';
    const headers = {
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'xiaojj-pro-trending/1.0',
    };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    let repos;
    if (tab === 'rising') {
      repos = await search('created:>' + recentDate(120) + ' stars:>100', 'stars', 50, headers);
      if (!repos.length) throw new Error('empty rising');
    } else if (tab === 'leaderboard') {
      repos = await search('stars:>100 pushed:>' + recentDate(1), 'stars', 30, headers);
      if (!repos.length) throw new Error('empty leaderboard');
    } else {
      const c = CATEGORIES.find(x => x.id === tab);
      if (!c) {
        res.setHeader('Cache-Control', 'no-store');
        return res.status(400).json({ ok: false, error: 'unknown tab' });
      }
      repos = await search(c.query, c.sort, 80, headers).catch(() => []);
      // 只过滤放错的，不搬运补回
      repos = repos.filter(r => {
        const t = CATEGORY_OVERRIDES[r.full_name];
        return !t || t === tab;
      });
    }

    const body = {
      ok: true,
      updated_at: new Date().toISOString().slice(0, 19).replace('T', ' '),
      repos,
    };
    memCache[tab] = { at: Date.now(), body };
    setCacheHeaders(res);
    res.setHeader('X-Trending-Cache', 'miss');
    return res.status(200).json(body);
  } catch (e) {
    const code = e && e.rateLimited ? 503 : 500;
    res.setHeader('Cache-Control', 'no-store');
    return res.status(code).json({ ok: false, error: (e && e.message) || 'trending failed' });
  }
}
