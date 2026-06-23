#!/usr/bin/env python3
"""Generate aggregated news_data.json from multiple sources.
Aggregates Hacker News, GitHub trending, and Juejin articles
into a unified news feed for the homepage.
"""

import json
import os
import re
import html
from datetime import datetime


def strip_html(text):
    """Remove HTML tags and decode entities."""
    if not text:
        return ''
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def truncate(text, max_len=200):
    """Truncate text to max_len characters."""
    if not text:
        return ''
    text = str(text)
    if len(text) > max_len:
        return text[:max_len] + '...'
    return text


def load_json(filepath):
    """Load JSON file if exists."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️ Cannot load {filepath}: {e}")
        return None


def news_from_hackernews(hackernews_data, limit=10):
    """Extract news from Hacker News data."""
    news_items = []
    if not hackernews_data or 'stories' not in hackernews_data:
        return news_items

    stories = hackernews_data.get('stories', [])[:limit]
    for story in stories:
        title = story.get('title', '')
        url = story.get('url', '')
        score = story.get('score', 0)
        comments = story.get('descendants', 0)

        summary_parts = []
        if score:
            summary_parts.append(f"Points: {score}")
        if comments:
            summary_parts.append(f"Comments: {comments}")
        summary = ' | '.join(summary_parts) if summary_parts else ''

        category = '科技'
        title_lower = title.lower()
        if any(k in title_lower for k in ['show hn', 'ask hn', 'launch', 'announce', 'release']):
            category = '开发'
        if any(k in title_lower for k in ['ai', 'llm', 'gpt', 'machine learning', 'deep learning', 'model']):
            category = 'AI'

        news_items.append({
            'title': title,
            'summary': summary,
            'link': url or story.get('hn_url', ''),
            'source': 'Hacker News',
            'category': category,
            'published': story.get('time', '')[:10] if story.get('time') else datetime.now().strftime('%Y-%m-%d'),
            'score': score
        })

    return news_items


def news_from_github(github_data, limit=8):
    """Extract news from GitHub trending data."""
    news_items = []
    if not github_data or 'categories' not in github_data:
        return news_items

    categories = github_data.get('categories', {})
    hot_repos = categories.get('hot', {}).get('repos', [])[:limit]

    for repo in hot_repos:
        name = repo.get('full_name', repo.get('name', ''))
        description = repo.get('description', '')
        stars = repo.get('stars', 0)
        language = repo.get('language', '')
        topics = repo.get('topics', [])

        summary_parts = []
        if language:
            summary_parts.append(language)
        if stars:
            summary_parts.append(f"⭐ {stars:,} stars")
        if topics:
            summary_parts.append(' | '.join(topics[:3]))
        summary = ' · '.join(summary_parts) if summary_parts else ''

        category = '开发'
        topics_str = ' '.join(topics).lower()
        if any(k in topics_str or k in description.lower() for k in ['ai', 'llm', 'gpt', 'machine-learning', 'deep-learning']):
            category = 'AI'
        if any(k in topics_str for k in ['frontend', 'react', 'vue', 'ui', 'component']):
            category = '前端'

        news_items.append({
            'title': f"⭐ {name}",
            'summary': truncate(strip_html(description), 150) + (f" — {summary}" if summary else ''),
            'link': repo.get('html_url', ''),
            'source': 'GitHub Trending',
            'category': category,
            'published': datetime.now().strftime('%Y-%m-%d'),
            'score': stars
        })

    return news_items


def news_from_juejin(juejin_data, limit=7):
    """Extract news from Juejin articles."""
    news_items = []
    if not juejin_data or 'articles' not in juejin_data:
        return news_items

    articles = juejin_data.get('articles', [])[:limit]
    for article in articles:
        title = article.get('title', '')
        digest = article.get('digest', '')
        views = article.get('views', 0)
        likes = article.get('likes', 0)
        category = article.get('category', '开发')

        summary_parts = []
        if views:
            summary_parts.append(f"👁 {views} 阅读")
        if likes:
            summary_parts.append(f"👍 {likes} 点赞")
        extra = ' · '.join(summary_parts) if summary_parts else ''

        clean_digest = truncate(strip_html(digest), 150)
        summary = clean_digest + (f" — {extra}" if extra and clean_digest else extra)

        news_items.append({
            'title': title,
            'summary': summary,
            'link': article.get('url', ''),
            'source': '掘金',
            'category': category or '开发',
            'published': article.get('created_at', datetime.now().strftime('%Y-%m-%d')),
            'score': likes + views // 10
        })

    return news_items


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.abspath(os.path.join(script_dir, '..', 'data'))
    os.makedirs(data_dir, exist_ok=True)

    print("Generating aggregated news feed...")

    hackernews_data = load_json(os.path.join(data_dir, 'hackernews.json'))
    github_data = load_json(os.path.join(data_dir, 'github.json'))
    juejin_data = load_json(os.path.join(data_dir, 'juejin.json'))

    all_news = []

    hn_news = news_from_hackernews(hackernews_data, limit=10)
    print(f"  📰 Hacker News: {len(hn_news)} items")
    all_news.extend(hn_news)

    gh_news = news_from_github(github_data, limit=8)
    print(f"  🐙 GitHub: {len(gh_news)} items")
    all_news.extend(gh_news)

    jj_news = news_from_juejin(juejin_data, limit=7)
    print(f"  📖 掘金: {len(jj_news)} items")
    all_news.extend(jj_news)

    all_news.sort(key=lambda x: x.get('score', 0), reverse=True)

    for item in all_news:
        item.pop('score', None)

    today = datetime.now()
    date_str_cn = today.strftime('%Y年%m月%d日')
    date_str = today.strftime('%Y-%m-%d')

    output = {
        'date': date_str,
        'date_str': date_str_cn,
        'count': len(all_news),
        'news': all_news
    }

    output_file = os.path.join(data_dir, 'news_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Generated {len(all_news)} news items")
    print(f"   Saved to: {output_file}")
    print(f"   Date: {date_str_cn}")


if __name__ == '__main__':
    main()
