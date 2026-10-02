// 小红书 7 天选题日历 API（Vercel Serverless, Node.js）
// POST /api/topics  { field, product? } -> { days: [{ date, weekday, topic, angle, keywords[] }] }
//
// 环境变量（与 /api/generate 取同一套值）：
//   LLM_API_KEY   必填
//   LLM_BASE_URL  默认 https://api.deepseek.com
//   LLM_MODEL     默认 deepseek-chat

// 简易 IP 限流：每个 IP 每天最多 20 次（与 generate.js 同口径）。
const quota = new Map();
function checkQuota(ip) {
  const day = new Date().toISOString().slice(0, 10);
  const key = ip + '|' + day;
  const n = (quota.get(key) || 0) + 1;
  quota.set(key, n);
  if (quota.size > 5000) quota.clear();
  return n <= 20;
}

function buildPrompt(field, product) {
  return `你是小红书资深选题策划，熟悉平台流量逻辑：搜索流量吃关键词，推荐流量吃情绪和争议，干货收藏高、种草转化高。

博主领域：${field}
产品/方向补充：${product || '无'}

请为这位博主生成未来 7 天的选题日历。要求：
1. 每天 1 个选题，选题即笔记标题，不超过 20 个字，含 1-2 个搜索关键词，不用"最/第一"等极限词。
2. 7 天搭配要有节奏：2 条干货教程类（收藏向）、2 条种草推荐类（转化向）、1 条热点/节日/季节结合、1 条讨论/争议型（评论向）、1 条人设/日常类（粘性向）。
3. angle：一句话说明这个选题的切入角度和"为什么值得写"（比如：切中什么痛点、蹭什么热点、预期什么数据）。
4. keywords：2-3 个该选题适合埋的搜索关键词。
5. 选题要具体、可执行，不写"分享我的日常"这种空话。

只返回 JSON，不要有其他内容，格式：
{"days": [{"topic": "选题标题", "angle": "切入角度一句话", "keywords": ["关键词1", "关键词2"]}, ...共7条]}`;
}

function chatUrls(base) {
  const urls = [`${base}/chat/completions`];
  if (!base.endsWith('/v1')) urls.push(`${base}/v1/chat/completions`);
  return urls;
}

async function callLlm(prompt) {
  const apiKey = process.env.LLM_API_KEY || '';
  const base = (process.env.LLM_BASE_URL || 'https://api.deepseek.com').replace(/\/$/, '');
  const model = process.env.LLM_MODEL || 'deepseek-chat';
  let lastErr = null;
  for (const url of chatUrls(base)) {
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: prompt }],
          temperature: 0.8,
          response_format: { type: 'json_object' },
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      const content = data?.choices?.[0]?.message?.content;
      if (!content) throw new Error('网关返回为空');
      const m = content.match(/\{[\s\S]*\}/);
      return JSON.parse(m ? m[0] : content);
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error('LLM 调用失败');
}

const WEEK = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
function cleanStr(s, maxLen) {
  s = String(s || '').trim();
  return maxLen ? s.slice(0, maxLen) : s;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: '只支持 POST' });
  }
  const ip =
    (req.headers['x-forwarded-for'] || '').split(',')[0].trim() ||
    req.socket?.remoteAddress ||
    'unknown';
  if (!checkQuota(ip)) {
    return res.status(429).json({ error: '今天免费次数用完了，明天再来吧' });
  }
  if (!process.env.LLM_API_KEY) {
    return res.status(500).json({ error: '服务端未配置 LLM_API_KEY' });
  }

  const { field, product } = req.body || {};
  if (!field || !String(field).trim()) {
    return res.status(400).json({ error: '请填写你的领域' });
  }

  try {
    const raw = await callLlm(buildPrompt(String(field).trim(), String(product || '').trim()));
    const days = Array.isArray(raw.days) ? raw.days : [];
    const today = new Date();
    const out = days.slice(0, 7).map((d, i) => {
      const dt = new Date(today.getTime() + i * 86400000);
      return {
        date: `${dt.getMonth() + 1}月${dt.getDate()}日`,
        weekday: WEEK[dt.getDay()],
        topic: cleanStr(d.topic, 24),
        angle: cleanStr(d.angle, 80),
        keywords: Array.isArray(d.keywords)
          ? d.keywords.map((k) => cleanStr(k)).filter(Boolean).slice(0, 3)
          : [],
      };
    });
    if (!out.length) throw new Error('选题生成为空，请重试');
    res.status(200).json({ days: out });
  } catch (e) {
    console.error('topics failed:', e?.message || e);
    res.status(502).json({ error: '生成失败，请稍后重试' });
  }
}
