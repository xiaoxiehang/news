// 小红书文案生成 API（Vercel Serverless, Node.js）
// POST /api/generate  { topic, points?, style? } -> { title, hook, body, tags, cover_points }
//
// 环境变量（与 GitHub Actions 的 LLM Secrets 取同一套值）：
//   LLM_API_KEY   必填
//   LLM_BASE_URL  默认 https://api.deepseek.com
//   LLM_MODEL     默认 gpt-6-sol

const STYLE_LABEL = {
  zhongcao: '种草推荐',
  ganhuo: '干货教程',
  ceping: '真实测评',
};

// 简易 IP 限流：每个 IP 每天最多 20 次。
// 注意 serverless 实例内存不共享，这是软限制，防随手刷不防恶意。
const quota = new Map();
function checkQuota(ip) {
  const day = new Date().toISOString().slice(0, 10);
  const key = ip + '|' + day;
  const n = (quota.get(key) || 0) + 1;
  quota.set(key, n);
  if (quota.size > 5000) quota.clear();
  return n <= 20;
}

function buildPrompt(topic, points, style) {
  const styleName = STYLE_LABEL[style] || STYLE_LABEL.zhongcao;
  const structure =
    style === 'ganhuo'
      ? '正文按"步骤 1/2/3"组织，每步一句话讲清操作，最后给一个避坑提醒。'
      : style === 'ceping'
        ? '正文逐个测评，每个给一句话结论+星级，最后一段总结"谁适合买/不适合谁"。'
        : '正文按"痛点→种草→怎么用→避坑"组织，像朋友聊天一样推荐。';
  return `你是小红书博主"鸡仔"，擅长写高点击的图文笔记，读者是爱尝鲜的年轻人、打工人、学生党。
你的核心能力是"说人话"：不说公文腔，不说黑话，像朋友一样分享。

用户给的主题：${topic}
用户补充的卖点/要点：${points || '无'}
笔记风格：${styleName}

请写一篇小红书图文笔记文案。要求：
1. 标题不超过 20 个字，开头抓眼球，含 1-2 个搜索关键词，不用"最/第一"等极限词，可加 1 个 emoji。
2. hook：开头 2 行口语化文案，先给结论、制造期待（两行之间用\\n分隔）。
3. 正文：${structure}口语化、第一人称、分段清晰，适当用 emoji，300-600 字。
4. tags：5-8 个全中文话题标签，大词+人群词+精准词组合。
5. cover_points：3 条封面亮点，每条不超过 14 个字，要具体、有钩子（用于封面图）。

只返回 JSON，不要有其他内容，格式：
{"title": "标题", "hook": "第一行\\n第二行", "body": "正文段落1\\n\\n正文段落2",
 "tags": ["标签1", "标签2"], "cover_points": ["亮点1", "亮点2", "亮点3"]}`;
}

function chatUrls(base) {
  const urls = [`${base}/chat/completions`];
  if (!base.endsWith('/v1')) urls.push(`${base}/v1/chat/completions`);
  return urls;
}

async function callLlm(prompt) {
  const apiKey = process.env.LLM_API_KEY || '';
  const base = (process.env.LLM_BASE_URL || 'https://api.deepseek.com').replace(/\/$/, '');
  const model = process.env.LLM_MODEL || 'gpt-6-sol';
  let lastErr = null;
  for (const url of chatUrls(base)) {
    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          messages: [{ role: 'user', content: prompt }],
          temperature: 0.7,
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

  const { topic, points, style } = req.body || {};
  if (!topic || !String(topic).trim()) {
    return res.status(400).json({ error: '请填写主题' });
  }

  try {
    const raw = await callLlm(buildPrompt(String(topic).trim(), String(points || '').trim(), style));
    const tags = Array.isArray(raw.tags) ? raw.tags.map((t) => cleanStr(t)).filter(Boolean).slice(0, 8) : [];
    const coverPoints = Array.isArray(raw.cover_points)
      ? raw.cover_points.map((t) => cleanStr(t, 14)).filter(Boolean).slice(0, 3)
      : [];
    while (coverPoints.length < 3) coverPoints.push('');
    res.status(200).json({
      title: cleanStr(raw.title, 20),
      hook: cleanStr(raw.hook),
      body: cleanStr(raw.body),
      tags: tags.length ? tags : ['种草', '好物分享'],
      cover_points: coverPoints,
    });
  } catch (e) {
    console.error('generate failed:', e?.message || e);
    res.status(502).json({ error: '生成失败，请稍后重试' });
  }
}
