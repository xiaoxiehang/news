#!/usr/bin/env python3
"""Fetch GitHub trending repos and save as static JSON.
输出结构：{ updated_at, leaderboard(今日热榜), categories(7个技术领域) }"""

import json
import os
import time
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'NewsDigest/1.0'
}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

def get_recent_date(days=30):
    return (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

# 7 个技术领域（中文名）
CATEGORIES = {
    'ai': {
        'name': 'AI 机器学习',
        'desc': '人工智能、机器学习',
        'query': 'machine learning OR deep learning OR LLM stars:>1000',
        'sort': 'stars'
    },
    'frontend': {
        'name': '前端',
        'desc': '前端框架、UI库',
        'query': 'react OR vue OR nextjs OR svelte stars:>3000',
        'sort': 'stars'
    },
    'backend': {
        'name': '后端',
        'desc': '后端框架、数据库',
        'query': 'api OR database OR server OR microservice stars:>3000',
        'sort': 'stars'
    },
    'fullstack': {
        'name': '全栈',
        'desc': '全栈框架',
        'query': 'nextjs OR nuxt OR fullstack OR trpc stars:>3000',
        'sort': 'stars'
    },
    'mobile': {
        'name': '移动端',
        'desc': '移动端开发',
        'query': 'flutter OR react-native OR swift OR kotlin stars:>3000',
        'sort': 'stars'
    },
    'devtools': {
        'name': '开发者工具',
        'desc': '开发者工具、CLI',
        'query': 'cli OR terminal OR vscode extension stars:>2000',
        'sort': 'stars'
    },
    'productivity': {
        'name': '效率工具',
        'desc': '效率工具、自动化',
        'query': 'productivity OR automation OR workflow tool stars:>1000',
        'sort': 'stars'
    },
    'cloudnative': {
        'name': '云原生',
        'desc': 'K8s、Docker、云原生',
        'query': 'kubernetes OR docker OR helm stars:>2000',
        'sort': 'stars'
    },
    'database': {
        'name': '数据库',
        'desc': '数据库、向量库',
        'query': 'database OR postgres OR redis OR mongodb stars:>2000',
        'sort': 'stars'
    },
    'game': {
        'name': '游戏',
        'desc': '游戏引擎、游戏开发',
        'query': 'game engine OR godot OR gamedev stars:>1000',
        'sort': 'stars'
    },
}

# 热榜数据源：昨日有推送的高星项目（只供榜单用，不单独成分类）
HOT_SOURCE = {
    'query': 'stars:>100 pushed:' + get_recent_date(1),
    'sort': 'stars'
}

# 新项目数据源：120 天内创建的新项目（供"升星新秀"用）
RISING_SOURCE = {
    'query': 'created:>' + get_recent_date(120) + ' stars:>100',
    'sort': 'stars'
}

def fetch_repos(query, sort, per_page=30):
    url = 'https://api.github.com/search/repositories'
    params = {'q': query, 'sort': sort, 'order': 'desc', 'per_page': per_page}

    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 403:
            print("  ⚠️ Rate limited, waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)

        resp.raise_for_status()
        data = resp.json()
        repos = []
        for item in data.get('items', [])[:per_page]:
            repos.append({
                'name': item['name'],
                'full_name': item['full_name'],
                'owner': item['owner']['login'],
                'description': (item.get('description') or '')[:200],
                'html_url': item['html_url'],
                'language': item.get('language'),
                'stars': item['stargazers_count'],
                'forks': item['forks_count'],
                'topics': item.get('topics', [])[:5],
                'created_at': item.get('created_at', '')[:10],
                'updated_at': item.get('updated_at', '')[:10]
            })
        return repos
    except Exception as e:
        print(f"  ❌ {e}")
        return []

def main():
    repo_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(repo_dir, exist_ok=True)

    all_repos = {}  # full_name -> repo（去重，供榜单用）
    categories = {}

    for cat_id, config in CATEGORIES.items():
        print(f"Fetching {cat_id}...")
        repos = fetch_repos(config['query'], config['sort'], per_page=50)
        print(f"  ✅ {cat_id}: {len(repos)} repos")
        categories[cat_id] = {
            'name': config['name'],
            'desc': config['desc'],
            'repos': repos
        }
        for r in repos:
            all_repos.setdefault(r['full_name'], r)
        time.sleep(2)

    print("Fetching hot source...")
    hot_repos = fetch_repos(HOT_SOURCE['query'], HOT_SOURCE['sort'])
    print(f"  ✅ hot source: {len(hot_repos)} repos")
    for r in hot_repos:
        all_repos.setdefault(r['full_name'], r)

    print("Fetching rising source...")
    rising_repos = fetch_repos(RISING_SOURCE['query'], RISING_SOURCE['sort'], per_page=20)
    print(f"  ✅ rising source: {len(rising_repos)} repos")
    for r in rising_repos:
        all_repos.setdefault(r['full_name'], r)
    time.sleep(2)

    # 每日涨星：先算 stars_gain，再写文件（修写入顺序 bug）
    hist_file = os.path.join(repo_dir, 'github-stars-history.json')
    history = {}
    if os.path.exists(hist_file):
        try:
            history = json.load(open(hist_file, encoding='utf-8'))
        except Exception:
            history = {}
    today = datetime.now().strftime('%Y-%m-%d')
    for fn, repo in all_repos.items():
        h = history.setdefault(fn, {})
        prev = None
        for d in sorted(h.keys(), reverse=True):
            if d != today:
                prev = h[d]
                break
        repo['stars_gain'] = repo['stars'] - prev if prev is not None else None
        h[today] = repo['stars']
    # 只保留 30 天历史
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    for fn in list(history.keys()):
        history[fn] = {d: s for d, s in history[fn].items() if d >= cutoff}
        if not history[fn]:
            del history[fn]
    with open(hist_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=1)
    print("✅ star 历史已更新")

    # 今日热榜：按日增星排（无增量数据时按总星数兜底），取前 12
    leaderboard = sorted(
        all_repos.values(),
        key=lambda r: (r['stars_gain'] if r['stars_gain'] is not None else -1, r['stars']),
        reverse=True
    )[:12]

    # 新星榜：按日增星排，取前 12（从 all_repos 取对象，保证有 stars_gain）
    rising = sorted(
        [all_repos[r['full_name']] for r in rising_repos],
        key=lambda r: (r['stars_gain'] if r['stars_gain'] is not None else -1, r['stars']),
        reverse=True
    )[:12]

    all_data = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'leaderboard': leaderboard,
        'rising': rising,
        'categories': categories
    }
    output_file = os.path.join(repo_dir, 'github.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Saved to {output_file}")
    print(f"   Updated: {all_data['updated_at']}")
    print(f"   榜单: {len(leaderboard)} | 新秀: {len(rising)} | 分类: {len(categories)}")

if __name__ == '__main__':
    main()
