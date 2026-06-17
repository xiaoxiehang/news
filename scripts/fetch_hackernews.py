#!/usr/bin/env python3
"""Fetch Hacker News top stories"""

import json
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_story(story_id):
    """Fetch single story"""
    try:
        story_resp = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json', timeout=10)
        story = story_resp.json()
        
        if story and story.get('type') == 'story':
            return {
                'id': story['id'],
                'title': story.get('title', ''),
                'url': story.get('url', f"https://news.ycombinator.com/item?id={story['id']}"),
                'score': story.get('score', 0),
                'by': story.get('by', ''),
                'time': datetime.fromtimestamp(story.get('time', 0)).strftime('%Y-%m-%d %H:%M'),
                'descendants': story.get('descendants', 0),
                'hn_url': f"https://news.ycombinator.com/item?id={story['id']}"
            }
    except Exception as e:
        print(f"  ⚠️ Story {story_id}: {e}")
    return None

def fetch_hackernews(limit=30):
    """Fetch top stories from Hacker News API"""
    print("Fetching Hacker News...")
    try:
        # Get top story IDs
        resp = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json', timeout=30)
        resp.raise_for_status()
        story_ids = resp.json()[:limit]
        
        # Fetch stories concurrently
        stories = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_story, sid): sid for sid in story_ids}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    stories.append(result)
        
        # Sort by score descending
        stories.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        print(f"  ✅ Hacker News: {len(stories)} stories")
        return stories
    except Exception as e:
        print(f"  ❌ Hacker News: {e}")
        return []

def main():
    repo_dir = '/workspace/news-repo/data'
    os.makedirs(repo_dir, exist_ok=True)
    
    stories = fetch_hackernews(30)
    
    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stories': stories
    }
    
    output_file = os.path.join(repo_dir, 'hackernews.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to {output_file}")

if __name__ == '__main__':
    main()
