#!/usr/bin/env python3
"""Fetch Juejin trending articles"""

import json
import os
import requests
from datetime import datetime

def fetch_juejin(limit=30):
    """Fetch trending articles from Juejin"""
    print("Fetching Juejin...")
    try:
        # Juejin API for hot articles
        url = 'https://api.juejin.cn/recommend_api/v1/article/recommend_all_feed'
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'id_type': 2,
            'sort_type': 200,  # Hot articles
            'cursor': '0',
            'limit': limit
        }
        
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        articles = []
        for item in data.get('data', []):
            article_info = item.get('article_info', {})
            if article_info:
                articles.append({
                    'id': article_info.get('article_id', ''),
                    'title': article_info.get('title', ''),
                    'url': f"https://juejin.cn/post/{article_info.get('article_id', '')}",
                    'cover': article_info.get('cover_image', ''),
                    'digest': article_info.get('digest', '')[:200],
                    'views': int(article_info.get('view_count', 0)),
                    'likes': int(article_info.get('digg_count', 0)),
                    'comments': int(article_info.get('comment_count', 0)),
                    'author': article_info.get('author_name', ''),
                    'category': article_info.get('category', {}).get('category_name', ''),
                    'created_at': datetime.fromtimestamp(
                        int(article_info.get('ctime', 0))
                    ).strftime('%Y-%m-%d') if article_info.get('ctime') else ''
                })
        
        print(f"  ✅ Juejin: {len(articles)} articles")
        return articles
    except Exception as e:
        print(f"  ❌ Juejin: {e}")
        return []

def main():
    repo_dir = '/workspace/news-repo/data'
    os.makedirs(repo_dir, exist_ok=True)
    
    articles = fetch_juejin(30)
    
    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'articles': articles
    }
    
    output_file = os.path.join(repo_dir, 'juejin.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to {output_file}")

if __name__ == '__main__':
    main()
