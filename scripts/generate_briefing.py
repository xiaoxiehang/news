#!/usr/bin/env python3
"""AI 每日早报：从各数据源挑选最值得读的新闻，生成中文一句话摘要。

读取 data/github.json、data/hackernews.json、data/juejin.json，
调用 OpenAI 兼容的 LLM API（默认 DeepSeek），输出 data/briefing.json。

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

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.deepseek.com').rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-chat')

MAX_CANDIDATES = 24
MAX_PICKS = 8


def load_json(name):
    path = os.path.join(DATA_DIR, name)
    if not os.path.exists(path):
        print(f'  ⚠️ 缺少 {name}，跳过')
        return None
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def collect_candidates():
    """从各数据源收集候选条目，返回 [{title, url, source, desc}]"""
    candidates = []

    gh = load_json('github.json')
    if gh:
        cats = gh.get('categories', {})
        for cat_id in ('hot', 'trending'):
            for r in cats.get(cat_id, {}).get('repos', [])[:6]:
                candidates.append({
                    'title': r.get('full_name') or r.get('name', ''),
                    'url': r.get('html_url', ''),
                    'source': 'GitHub',
                    'desc': (r.get('description') or '')[:200],
                    'meta': f"⭐ {r.get('stars', 0)} · {r.get('language') or ''}",
                })

    hn = load_json('hackernews.json')
    if hn:
        stories = sorted(hn.get('stories', []), key=lambda s: s.get('score', 0), reverse=True)
        for s in stories[:8]:
            candidates.append({
                'title': s.get('title', ''),
                'url': s.get('url', ''),
                'source': 'Hacker News',
                'desc': (s.get('desc') or s.get('text') or '')[:200],
                'meta': f"▲ {s.get('score', 0)}",
            })

    jj = load_json('juejin.json')
    if jj:
        for a in jj.get('articles', [])[:8]:
            candidates.append({
                'title': a.get('title', ''),
                'url': a.get('url', ''),
                'source': '掘金',
                'desc': (a.get('desc') or a.get('brief') or '')[:200],
                'meta': '',
            })

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
    return f"""你是科技新闻编辑。从下面的候选新闻中挑选出今天最值得中文读者关注的 {MAX_PICKS} 条，
为每条写一句不超过 40 字的中文摘要（英文标题要翻译成中文），并写一段 2-3 句话的「今日速览」概括整体热点。

候选新闻：
{items}

只返回 JSON，不要有其他内容，格式如下：
{{"overview": "今日速览内容", "picks": [{{"title": "中文标题", "summary": "一句话摘要", "url": "原文链接", "source": "来源"}}]}}
picks 数组中 url 和 source 必须与候选新闻中的原文一致，不要编造链接。"""


def call_llm(prompt):
    resp = requests.post(
        f'{LLM_BASE_URL}/chat/completions',
        headers={'Authorization': f'Bearer {LLM_API_KEY}', 'Content-Type': 'application/json'},
        json={
            'model': LLM_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.3,
            'response_format': {'type': 'json_object'},
        },
        timeout=120,
    )
    resp.raise_for_status()
    content = resp.json()['choices'][0]['message']['content']
    # 兼容模型返回 markdown 包裹的情况
    m = re.search(r'\{.*\}', content, re.DOTALL)
    return json.loads(m.group(0) if m else content)


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    out_path = os.path.join(DATA_DIR, 'briefing.json')

    if not LLM_API_KEY:
        print('⏭️ 未设置 LLM_API_KEY，跳过 AI 早报生成（保留旧数据）')
        return

    candidates = collect_candidates()
    if not candidates:
        print('❌ 没有候选新闻，跳过')
        return
    print(f'📰 候选 {len(candidates)} 条，调用 {LLM_MODEL} 生成早报...')

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

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(briefing, f, ensure_ascii=False, indent=2)
    print(f'✅ 早报已生成: {len(briefing["picks"])} 条 -> {out_path}')


if __name__ == '__main__':
    main()
