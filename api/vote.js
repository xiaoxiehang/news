// Vercel Serverless Function: 早报投票 API
//
// GET  /api/vote?date=2026-09-29  -> { date, votes: {pick: n}, total }
// POST /api/vote  { date, pick }   -> 投票 +1，返回最新票数
//
// 票数存在 GitHub 仓库 data/votes/YYYY-MM-DD.json。
// 需要在 Vercel 环境变量里配置：
//   GITHUB_TOKEN  - 有 news 仓库 Contents 读写权限的 token
//   VOTE_REPO     - 可选，默认 xiaoxiehang/news

const REPO = process.env.VOTE_REPO || 'xiaoxiehang/news';
const TOKEN = process.env.GITHUB_TOKEN;
const BRANCH = 'main';

function hashIp(ip) {
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < ip.length; i++) {
    const ch = ip.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36);
}

function getIp(req) {
  const fwd = req.headers['x-forwarded-for'];
  if (fwd) return fwd.split(',')[0].trim();
  return (req.socket && req.socket.remoteAddress) || 'unknown';
}

async function gh(path, method, body) {
  const r = await fetch(`https://api.github.com/repos/${REPO}/contents/${path}`, {
    method,
    headers: {
      'Authorization': `Bearer ${TOKEN}`,
      'Accept': 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'User-Agent': 'xiaojj-pro-vote',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r;
}

async function readVotes(date) {
  const path = `data/votes/${date}.json`;
  const r = await gh(path, 'GET');
  if (r.status === 404) return { file: null, data: { date, votes: {}, total: 0, voters: [] } };
  if (!r.ok) throw new Error(`GitHub read failed: ${r.status}`);
  const j = await r.json();
  const data = JSON.parse(Buffer.from(j.content, 'base64').toString('utf8'));
  return { file: j, data };
}

async function writeVotes(date, data, sha, retries = 1) {
  const path = `data/votes/${date}.json`;
  data.updated_at = new Date().toISOString();
  const content = Buffer.from(JSON.stringify(data, null, 2)).toString('base64');
  const r = await gh(path, 'PUT', {
    message: `🗳️ 投票数据 ${date}`,
    content,
    branch: BRANCH,
    ...(sha ? { sha } : {}),
  });
  if (r.status === 409 && retries > 0) {
    // 并发冲突：重读再写
    const fresh = await readVotes(date);
    return writeVotes(date, mergeVotes(fresh.data, data), fresh.file && fresh.file.sha, 0);
  }
  if (r.status === 422 && retries > 0) {
    const fresh = await readVotes(date);
    return writeVotes(date, mergeVotes(fresh.data, data), fresh.file && fresh.file.sha, 0);
  }
  if (!r.ok) throw new Error(`GitHub write failed: ${r.status}`);
  return r.json();
}

function mergeVotes(base, incoming) {
  // 合并票数：取各自最大值（避免并发投票丢失太多）
  const votes = { ...(base.votes || {}) };
  for (const [k, v] of Object.entries(incoming.votes || {})) {
    votes[k] = Math.max(votes[k] || 0, v);
  }
  const voters = [...new Set([...(base.voters || []), ...(incoming.voters || [])])].slice(-3000);
  return { date: base.date, votes, voters, total: Object.values(votes).reduce((a, b) => a + b, 0) };
}

function json(res, code, obj) {
  res.status(code).setHeader('Content-Type', 'application/json').end(JSON.stringify(obj));
}

module.exports = async (req, res) => {
  if (!TOKEN) return json(res, 503, { error: '投票服务未配置' });

  const date = (req.query.date || (req.body && req.body.date) || '').toString();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return json(res, 400, { error: 'date 格式错误' });

  try {
    if (req.method === 'GET') {
      const { data } = await readVotes(date);
      return json(res, 200, { date, votes: data.votes || {}, total: data.total || 0 });
    }

    if (req.method === 'POST') {
      const pick = req.body && req.body.pick;
      if (pick === undefined || pick === null || !/^\d+$/.test(String(pick))) {
        return json(res, 400, { error: 'pick 格式错误' });
      }
      const pickKey = String(Number(pick));
      const voterId = `${hashIp(getIp(req))}:${pickKey}`;

      const { file, data } = await readVotes(date);
      data.votes = data.votes || {};
      data.voters = data.voters || [];
      if (data.voters.includes(voterId)) {
        return json(res, 200, { date, votes: data.votes, total: data.total || 0, dup: true });
      }
      data.votes[pickKey] = (data.votes[pickKey] || 0) + 1;
      data.total = (data.total || 0) + 1;
      data.voters.push(voterId);
      if (data.voters.length > 3000) data.voters = data.voters.slice(-3000);

      await writeVotes(date, data, file && file.sha);
      return json(res, 200, { date, votes: data.votes, total: data.total });
    }

    return json(res, 405, { error: 'Method Not Allowed' });
  } catch (e) {
    console.error('vote error:', e.message);
    return json(res, 500, { error: '投票服务异常' });
  }
};
