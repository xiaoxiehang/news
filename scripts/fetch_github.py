#!/usr/bin/env python3
"""Fetch GitHub trending repos and save as static JSON"""

import json
import os
import time
import re
import requests
from datetime import datetime, timedelta

GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')

HEADERS = {
    'Accept': 'application/vnd.github.v3+json',
    'User-Agent': 'NewsDigest/1.0'
}
if GITHUB_TOKEN:
    HEADERS['Authorization'] = f'token {GITHUB_TOKEN}'

def get_recent_date(days=7):
    return (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

def fetch_trending():
    """Scrape GitHub trending page for truly trending repos"""
    print("Fetching trending (from github.com/trending)...")
    try:
        resp = requests.get(
            'https://github.com/trending?since=daily',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=30
        )
        resp.raise_for_status()
        html = resp.text
        
        # Extract repo links from trending page
        repos = []
        # Pattern: <h2 class="h3 lh-condensed">...<a href="/owner/repo"...>
        pattern = r'<h2[^>]*>\s*<a[^>]*href="(/[^"]+)"'
        matches = re.findall(pattern, html)
        
        for match in matches[:30]:
            full_name = match.strip('/')
            if '/' not in full_name or full_name.count('/') != 1:
                continue
            owner, name = full_name.split('/')
            repos.append({
                'name': name,
                'full_name': full_name,
                'owner': owner,
                'description': '',
                'stars': 0,
                'forks': 0,
                'language': None,
                'topics': [],
                '_need_details': True
            })
        
        # Fetch details for each trending repo
        detailed_repos = []
        for repo in repos:
            try:
                detail = fetch_repo_details(repo['full_name'])
                if detail:
                    detailed_repos.append(detail)
                time.sleep(0.5)
            except Exception as e:
                print(f"  ⚠️ {repo['full_name']}: {e}")
        
        print(f"  ✅ trending: {len(detailed_repos)} repos")
        return detailed_repos
    except Exception as e:
        print(f"  ❌ trending: {e}")
        return []

def fetch_repo_details(full_name):
    """Fetch details for a single repo"""
    url = f'https://api.github.com/repos/{full_name}'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    item = resp.json()
    return {
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
    }

CATEGORIES = {
    'trending': {
        'name': 'Trending',
        'desc': '近期最活跃的高星项目',
        'query': 'stars:>5000 pushed:>' + get_recent_date(),
        'sort': 'updated'
    },
    'ai': {
        'name': 'AI & ML',
        'desc': '人工智能、机器学习',
        'query': 'machine learning OR deep learning OR LLM stars:>1000',
        'sort': 'stars'
    },
    'frontend': {
        'name': 'Frontend',
        'desc': '前端框架、UI库',
        'query': 'react OR vue OR nextjs OR svelte stars:>3000',
        'sort': 'stars'
    },
    'devtools': {
        'name': 'Dev Tools',
        'desc': '开发者工具、CLI',
        'query': 'cli OR terminal OR vscode extension stars:>2000',
        'sort': 'stars'
    },
    'productivity': {
        'name': 'Productivity',
        'desc': '效率工具、自动化',
        'query': 'productivity OR automation OR workflow tool stars:>1000',
        'sort': 'stars'
    },
    'fullstack': {
        'name': 'Full Stack',
        'desc': '全栈框架',
        'query': 'nextjs OR nuxt OR fullstack OR trpc stars:>3000',
        'sort': 'stars'
    },
    'mobile': {
        'name': 'Mobile',
        'desc': '移动端开发',
        'query': 'flutter OR react-native OR swift OR kotlin stars:>3000',
        'sort': 'stars'
    },
    'backend': {
        'name': 'Backend',
        'desc': '后端框架、数据库',
        'query': 'api OR database OR server OR microservice stars:>3000',
        'sort': 'stars'
    }
}

def fetch_repos(category_id, config):
    url = 'https://api.github.com/search/repositories'
    params = {
        'q': config['query'],
        'sort': config['sort'],
        'order': 'desc',
        'per_page': 30
    }
    
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if resp.status_code == 403:
            print(f"  ⚠️ Rate limited, waiting 60s...")
            time.sleep(60)
            resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        
        resp.raise_for_status()
        data = resp.json()
        repos = []
        for item in data.get('items', [])[:30]:
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
        print(f"  ✅ {category_id}: {len(repos)} repos")
        return repos
    except Exception as e:
        print(f"  ❌ {category_id}: {e}")
        return []

def main():
    repo_dir = '/workspace/news-repo/data'
    os.makedirs(repo_dir, exist_ok=True)
    
    all_data = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'categories': {}
    }
    
    for cat_id, config in CATEGORIES.items():
        print(f"Fetching {cat_id}...")
        repos = fetch_repos(cat_id, config)
        all_data['categories'][cat_id] = {
            'name': config['name'],
            'desc': config['desc'],
            'repos': repos
        }
        time.sleep(2)  # Be nice to GitHub API
    
    output_file = os.path.join(repo_dir, 'github.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to {output_file}")
    print(f"   Updated: {all_data['updated_at']}")

if __name__ == '__main__':
    main()
