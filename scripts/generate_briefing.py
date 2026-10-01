#!/usr/bin/env python3
"""AI 每日早报：从权威 RSS 新闻源挑选最值得读的 AI 新闻，生成中文一句话摘要。

读取 data/rss.json（10 个 AI/科技媒体 RSS 源），
调用 OpenAI 兼容的 LLM API（默认 DeepSeek），输出 data/briefing.json。

定位：AI 行业早报（官方动态 + 权威媒体 + AI 新品），
与「极客资讯」（GitHub/HN 原始流）零重叠。

环境变量：
  LLM_API_KEY   必填，没有则跳过（不报错，保留旧早报）
  LLM_BASE_URL  默认 https://api.deepseek.com
  LLM_MODEL     默认 deepseek-chat
"""
import json
import os
import re
import requests
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SITE_ROOT = os.path.dirname(DATA_DIR)  # 网站根目录
ARCHIVE_DIR = os.path.join(DATA_DIR, 'archive')
SITE_URL = 'https://xiaojj.pro'

LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.deepseek.com').rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', '').strip() or 'gpt-6-sol'

MAX_CANDIDATES = 40
MAX_PICKS = 8


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        print(f'  ⚠️ 缺少 {name}，跳过')
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def collect_candidates():
    """从 RSS 新闻源收集候选条目，返回 [{title, url, source, desc}]
    （GitHub/HN 已移出选题池，归极客资讯，避免内容重复）"""
    candidates = []

    rss = load_json('rss.json')
    if rss:
        feeds = rss.get('feeds', [])
        # 轮询取条目：每个源每轮贡献 1 条，保证所有源都有机会进入候选池
        #（之前按源顺序取，前面的源会把 MAX_CANDIDATES 占满，后面的源永远进不来）
        per_feed = [f.get('items', [])[:8] for f in feeds]
        idx = 0
        while len(candidates) < MAX_CANDIDATES:
            added = False
            for fi, items in enumerate(per_feed):
                if idx < len(items) and len(candidates) < MAX_CANDIDATES:
                    it = items[idx]
                    candidates.append({
                        'title': it.get('title', ''),
                        'url': it.get('url', ''),
                        'source': feeds[fi].get('name', 'RSS'),
                        'desc': (it.get('desc') or '')[:200],
                        'meta': it.get('published') or '',
                    })
                    added = True
            if not added:
                break
            idx += 1

    # 去重（按 url）
    seen, uniq = set(), []
    for c in candidates:
        if not c['title'] or not c['url'] or c['url'] in seen:
            continue
        seen.add(c['url'])
        uniq.append(c)
    return uniq[:MAX_CANDIDATES]


def build_prompt(candidates):
    lines = []
    for i, c in enumerate(candidates, 1):
        meta = f'（{c["meta"]}）' if c['meta'] else ''
        desc = f'\n简介：{c["desc"]}' if c['desc'] else ''
        lines.append(f'{i}. [{c["source"]}] {c["title"]} {meta}\n链接：{c["url"]}{desc}')
    items = '\n\n'.join(lines)
    return f"""你是科技新闻编辑，读者是对 AI 感兴趣的普通中文读者（非程序员）。
从下面的候选新闻中挑选出今天最值得关注的 {MAX_PICKS} 条，为每条写一句不超过 40 字的中文摘要
（英文标题要翻译成中文），并写一段 2-3 句话的「今日速览」概括整体热点。

选题标准（按优先级）：
1. 必须是新闻：过去 48 小时内发生的事件、发布、数据、动态；
2. 一手官方发布（OpenAI 官方等大厂公告）和权威媒体（机器之心/虎嗅/InfoQ/The Verge/TechCrunch/MIT 科技评论）优先；
3. 坚决排除：观点评论、行业分析、前瞻预测、职业建议、年度盘点、软文推广、旧闻重发——标题像"未来五年…"、"为什么…"、"怎么办"的不要选；
4. 兼顾受众广度：8 条大致按「官方/大厂动态 2-3 条、权威媒体解读 3-4 条、AI 工具新品 1-2 条」搭配；
5. 优先选普通人能看懂、觉得有用的，纯技术黑话、重复报道靠后。

候选新闻：
{items}

只返回 JSON，不要有其他内容，格式如下：
{{"overview": "今日速览内容", "picks": [{{"title": "中文标题", "summary": "一句话摘要", "url": "原文链接", "source": "来源"}}]}}
picks 数组中 url 和 source 必须与候选新闻中的原文一致，不要编造链接。"""


def _chat_urls():
    urls = [f'{LLM_BASE_URL}/chat/completions']
    if not LLM_BASE_URL.rstrip('/').endswith('/v1'):
        urls.append(f'{LLM_BASE_URL}/v1/chat/completions')
    return urls


def _post_llm(headers, payload):
    """POST chat completions；自动兼容网关地址带/不带 /v1 的情况"""
    last_err = None
    for url in _chat_urls():
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            if 'choices' not in data:
                raise ValueError(f'网关返回异常: {str(data)[:150]}')
            return data
        except Exception as e:
            last_err = e
            detail = ''
            resp = getattr(e, 'response', None)
            if resp is not None:
                try:
                    detail = f' | 网关返回: {resp.text[:300]}'
                except Exception:
                    pass
            print(f'   ⚠️ {url} 失败: {e}{detail}')
    raise last_err


def call_llm(prompt):
    data = _post_llm(
        {'Authorization': f'Bearer {LLM_API_KEY}', 'Content-Type': 'application/json'},
        {
            'model': LLM_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
            'response_format': {'type': 'json_object'},
        },
    )
    content = data['choices'][0]['message']['content']
    # 兼容模型返回 markdown 包裹的情况
    m = re.search(r'\{.*\}', content, re.DOTALL)
    return json.loads(m.group(0) if m else content)


def save_outputs(briefing, today):
    """保存早报：briefing.json + 归档快照 + 归档索引 + RSS"""
    # 1. 最新早报
    out_path = os.path.join(DATA_DIR, 'briefing.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)
    print(f'✅ 早报已生成: {len(briefing["picks"])} 条 -> {out_path}')

    # 2. 归档快照
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    snap_path = os.path.join(ARCHIVE_DIR, f'briefing-{today}.json')
    with open(snap_path, 'w', encoding='utf-8') as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)

    # 3. 归档索引
    index_path = os.path.join(ARCHIVE_DIR, 'index.json')
    index = []
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding='utf-8') as f:
                index = json.load(f)
        except Exception:
            index = []
    index = [e for e in index if e.get('date') != today]
    index.append({
        'date': today,
        'date_str': briefing.get('date_str', today),
        'overview': briefing.get('overview', ''),
        'count': len(briefing['picks']),
    })
    index.sort(key=lambda e: e['date'], reverse=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f'✅ 归档已更新: {snap_path}（共 {len(index)} 期）')

    # 4. RSS
    pub_date = datetime.strptime(today, '%Y-%m-%d').strftime('%a, %d %b %Y 08:00:00 +0800')
    items_xml = []
    for p in briefing['picks']:
        title = xml_escape(p.get('title', ''))
        link = xml_escape(p.get('url', SITE_URL))
        desc = xml_escape(p.get('summary', ''))
        source = xml_escape(p.get('source', ''))
        items_xml.append(
            f'    <item>\n'
            f'      <title>{title}</title>\n'
            f'      <link>{link}</link>\n'
            f'      <guid>{link}</guid>\n'
            f'      <description>{desc}（来源：{source}）</description>\n'
            f'      <pubDate>{pub_date}</pubDate>\n'
            f'    </item>'
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '<channel>\n'
        f'  <title>今日科技早报 | xiaojj.pro</title>\n'
        f'  <link>{SITE_URL}/</link>\n'
        f'  <description>每天早上 8 点，一份中文 AI 早报：精选权威科技媒体最值得读的 AI 新闻。</description>\n'
        f'  <language>zh-CN</language>\n'
        f'  <lastBuildDate>{pub_date}</lastBuildDate>\n'
        + '\n'.join(items_xml) + '\n'
        + '</channel>\n</rss>\n'
    )
    feed_path = os.path.join(SITE_ROOT, 'feed.xml')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(feed)
    print(f'✅ RSS 已生成: {feed_path}')


def main():
    today = datetime.now().strftime('%Y-%m-%d')

    if not LLM_API_KEY:
        print('⏭️ 未设置 LLM_API_KEY，跳过 AI 早报生成（保留旧数据）')
        return

    candidates = collect_candidates()
    if not candidates:
        print('❌ 没有候选新闻，跳过')
        return
    print(f'📰 候选 {len(candidates)} 条，调用 {LLM_MODEL} 生成早报...')
    print(f'   网关: {LLM_BASE_URL}/chat/completions')

    try:
        result = call_llm(build_prompt(candidates))
        picks = result.get('picks', [])[:MAX_PICKS]
        briefing = {
            'date': today,
            'date_str': datetime.now().strftime('%Y年%m月%d日'),
            'overview': result.get('overview', ''),
            'picks': [
                {
                    'title': p.get('title', ''),
                    'summary': p.get('summary', ''),
                    'url': p.get('url', ''),
                    'source': p.get('source', ''),
                }
                for p in picks if p.get('title') and p.get('url')
            ],
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    except Exception as e:
        print(f'❌ AI 生成失败: {e}')
        return

    save_outputs(briefing, today)


if __name__ == '__main__':
    main()
