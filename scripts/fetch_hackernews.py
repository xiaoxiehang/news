#!/usr/bin/env python3
"""Fetch Hacker News top stories with fallback APIs."""

import json
import os
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_from_firebase(limit=30):
    """Fetch from official Firebase API."""
    try:
        resp = requests.get(
            'https://hacker-news.firebaseio.com/v0/topstories.json',
            timeout=15
        )
        resp.raise_for_status()
        story_ids = resp.json()[:limit]

        def fetch_story(story_id):
            try:
                story_resp = requests.get(
                    f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json',
                    timeout=10
                )
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
                print(f"    ⚠️ Story {story_id}: {e}")
            return None

        stories = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_story, sid): sid for sid in story_ids}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    stories.append(result)

        stories.sort(key=lambda x: x.get('score', 0), reverse=True)
        return stories
    except Exception as e:
        print(f"  ⚠️ Firebase API failed: {e}")
        return None

def fetch_from_algolia(limit=30):
    """Fetch from Algolia HN Search API (fallback)."""
    try:
        resp = requests.get(
            'https://hn.algolia.com/api/v1/search',
            params={
                'tags': 'front_page',
                'hitsPerPage': limit
            },
            timeout=15
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get('hits', [])

        stories = []
        for hit in hits:
            created_at = hit.get('created_at', '')
            try:
                dt = datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')
                time_str = dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                time_str = created_at[:16].replace('T', ' ')

            story_id = hit.get('objectID', '')
            stories.append({
                'id': int(story_id) if story_id.isdigit() else 0,
                'title': hit.get('title', ''),
                'url': hit.get('url') or f"https://news.ycombinator.com/item?id={story_id}",
                'score': hit.get('points', 0),
                'by': hit.get('author', ''),
                'time': time_str,
                'descendants': hit.get('num_comments', 0),
                'hn_url': f"https://news.ycombinator.com/item?id={story_id}"
            })

        stories.sort(key=lambda x: x.get('score', 0), reverse=True)
        return stories
    except Exception as e:
        print(f"  ⚠️ Algolia API failed: {e}")
        return None

def fetch_hackernews(limit=30):
    """Fetch top stories from Hacker News with multiple fallback sources."""
    print("Fetching Hacker News...")

    sources = [
        ('Firebase', fetch_from_firebase),
        ('Algolia', fetch_from_algolia),
    ]

    for name, fetcher in sources:
        print(f"  Trying {name} API...")
        stories = fetcher(limit)
        if stories and len(stories) > 0:
            print(f"  ✅ Hacker News: {len(stories)} stories (via {name})")
            return stories

    print(f"  ❌ Hacker News: All sources failed")
    return []

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.join(script_dir, '..', 'data')
    repo_dir = os.path.abspath(repo_dir)
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
