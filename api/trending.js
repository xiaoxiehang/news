// GET /api/trending — GitHub 趋势实时代理（Vercel Serverless）
//
// 服务端持有 GITHUB_TOKEN（Vercel 环境变量），浏览器只调本接口，token 不暴露。
// 边缘缓存 5 分钟：每次打开要打 13 个搜索查询，GitHub 上限 30 次/分钟；
// 零缓存的话连刷两下就触发限流、反而掉回静态快照。5 分钟体感与实时无异。
// 返回结构与 data/github.json 一致，只是不带 stars_gain——
// 涨星数由前端用"实时 star − data/github-stars-history.json 最新快照"算出。
// 无 token 或被限流时返回 503，前端自动回退到静态 github.json。

const CATEGORIES = [
  // 注意：不加引号的多词会被 GitHub 当 AND 处理（machine learning 会误中
  // "machine image" + README 里的 learning），短语必须加引号；
  // media 不再用 topic:streaming（数据流引擎/消息队列全带 streaming 标签，
  // 和影音娱乐完全不是一回事，连续两夜 14 个误配都栽在这）。
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

// 分类修正表：full_name -> 正确分类。
// 查询再精确也拦不住语义误判；这些顽固个案每天都会被放错位置，在此强制归位。
// 来源：2026-10-08 / 10-09 夜间质检的人工修正结论。与 scripts/fetch_github.py 的
// CATEGORY_OVERRIDES 保持一致（实时接口和每日管线走同一套规则）。
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

function applyCategoryOverrides(categories) {
  for (const [fullName, targetId] of Object.entries(CATEGORY_OVERRIDES)) {
    const target = categories[targetId];
    if (!target) continue;
    let moved = null;
    for (const cat of Object.values(categories)) {
      const idx = (cat.repos || []).findIndex(r => r.full_name === fullName);
      if (idx >= 0) {
        const [r] = cat.repos.splice(idx, 1);
        if (!moved) moved = r;
      }
    }
    if (moved && !(target.repos || []).some(r => r.full_name === fullName)) {
      target.repos.push(moved);
    }
  }
}

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

// 进程内兜底缓存（边缘缓存为主，这个防同一实例连续打）
let memCache = null;

export default async function handler(req, res) {
  try {
    if (memCache && Date.now() - memCache.at < 5 * 60 * 1000) {
      res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=60');
      res.setHeader('CDN-Cache-Control', 'max-age=300');
      res.setHeader('X-Trending-Cache', 'memory');
      return res.status(200).json(memCache.body);
    }

    const token = process.env.GITHUB_TOKEN || '';
    const headers = {
      'Accept': 'application/vnd.github.v3+json',
      'User-Agent': 'xiaojj-pro-trending/1.0',
    };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const hotQ = 'stars:>100 pushed:>' + recentDate(1);
    const risingQ = 'created:>' + recentDate(120) + ' stars:>100';

    const jobs = [
      search(hotQ, 'stars', 30, headers).then(r => ({ key: 'leaderboard', repos: r })),
      search(risingQ, 'stars', 50, headers).then(r => ({ key: 'rising', repos: r })),
      ...CATEGORIES.map(c =>
        search(c.query, c.sort, 80, headers)
          .then(repos => ({ key: 'cat:' + c.id, repos, meta: c }))
          .catch(() => ({ key: 'cat:' + c.id, repos: [], meta: c }))
      ),
    ];
    const results = await Promise.all(jobs);

    const body = { ok: true, updated_at: new Date().toISOString().slice(0, 19).replace('T', ' '), categories: {} };
    for (const r of results) {
      if (r.key === 'leaderboard' || r.key === 'rising') {
        if (!r.repos.length) throw new Error('empty ' + r.key);
        body[r.key] = r.repos;
      } else {
        body.categories[r.meta.id] = { name: r.meta.name, desc: r.meta.desc, repos: r.repos };
      }
    }

    // 顽固误分类项目强制归位（与每日管线的 apply_category_overrides 同规则）
    applyCategoryOverrides(body.categories);

    memCache = { at: Date.now(), body };
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=60');
      res.setHeader('CDN-Cache-Control', 'max-age=300');
    res.setHeader('X-Trending-Cache', 'miss');
    return res.status(200).json(body);
  } catch (e) {
    const code = e && e.rateLimited ? 503 : 500;
    res.setHeader('Cache-Control', 'no-store');
    return res.status(code).json({ ok: false, error: (e && e.message) || 'trending failed' });
  }
}
