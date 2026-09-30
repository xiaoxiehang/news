#!/usr/bin/env python3
"""抓取权威 RSS 资讯源：官方一手 + 权威科技媒体 + AI 工具新品。

输出 data/rss.json：{fetched_at, feeds: [{name, items: [{title, url, desc, published}]}]}，
供 generate_briefing.py 做选题候选。

依赖：pip install feedparser requests
"""
import json
import os
import re
from datetime import datetime

import requests

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SITE_DIR, 'data')

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}

# (显示名, RSS 地址, 是否需要 AI 关键词过滤, 取几条)
FEEDS = [
    ('OpenAI 官方', 'https://openai.com/news/rss.xml', False, 5),
    ('量子位', 'https://www.qbitai.com/feed', False, 8),
    ('IT之家', 'https://www.ithome.com/rss/', True, 8),
    ('少数派', 'https://sspai.com/feed', True, 6),
    ('爱范儿', 'https://www.ifanr.com/feed', True, 6),
    ('V2EX', 'https://www.v2ex.com/index.xml', True, 8),
    ('The Verge', 'https://www.theverge.com/rss/index.xml', True, 6),
    ('TechCrunch', 'https://techcrunch.com/feed/', True, 6),
    ('MIT 科技评论', 'https://www.technologyreview.com/feed/', True, 6),
    ('Product Hunt', 'https://www.producthunt.com/feed', True, 8),
]

AI_KEYWORDS = re.compile(
    r'ai\b|人工智能|artificial intelligence|openai|anthropic|claude|gemini|'
    r'gpt|llm|大模型|chatgpt|copilot|智能体|agent|机器学习|深度学习|'
    r'machine learning|deep learning|neural|神经网络|diffusion|transformer|'
    r'sora|midjourney|stable diffusion|机器人|robot|自动驾驶|autonomous|'
    r'芯片|chip|nvidia|英伟达|算力|算法|algorithm',
    re.IGNORECASE,
)


def clean_html(text):
    text = re.sub(r'<[^>]+>', ' ', text or '')
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_feed(name, url, ai_filter, limit):
    try:
        import feedparser
    except ImportError:
        print('  ❌ 缺少 feedparser，请 pip install feedparser')
        return []
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        fp = feedparser.parse(r.content)
        items = []
        for e in fp.entries:
            title = (e.get('title') or '').strip()
            link = (e.get('link') or '').strip()
            if not title or not link:
                continue
            desc = clean_html(e.get('summary') or e.get('description') or '')[:200]
            if ai_filter and not AI_KEYWORDS.search(f'{title} {desc}'):
                continue
            items.append({
                'title': title,
                'url': link,
                'desc': desc,
                'published': (e.get('published') or '')[:16],
            })
            if len(items) >= limit:
                break
        print(f'  ✅ {name}: {len(items)} 条')
        return items
    except Exception as ex:
        print(f'  ⚠️ {name} 抓取失败: {ex}')
        return []


def main():
    feeds = []
    for name, url, ai_filter, limit in FEEDS:
        feeds.append({'name': name, 'items': fetch_feed(name, url, ai_filter, limit)})
    out = {'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'feeds': feeds}
    path = os.path.join(DATA_DIR, 'rss.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    total = sum(len(f['items']) for f in feeds)
    print(f'✅ RSS 抓取完成，共 {total} 条 -> {path}')


if __name__ == '__main__':
    main()
