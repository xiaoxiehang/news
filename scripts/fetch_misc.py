#!/usr/bin/env python3
"""Fetch random programming quotes and weather"""

import json
import os
import requests
from datetime import datetime

def fetch_quotes():
    """Fetch random programming quotes with multiple fallback sources."""
    print("Fetching quotes...")

    sources = [
        ('Quotable', lambda: _fetch_from_quotable()),
        ('AdviceSlip', lambda: _fetch_from_adviceslip()),
    ]

    for name, fetcher in sources:
        try:
            result = fetcher()
            if result and result.get('text'):
                print(f"  ✅ Quote via {name}")
                return result
        except Exception as e:
            print(f"  ⚠️ {name} API: {e}")

    print(f"  ℹ️ Using local fallback quote")
    quotes = [
        {"text": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "author": "Martin Fowler"},
        {"text": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
        {"text": "The best error message is the one that never shows up.", "author": "Thomas Fuchs"},
        {"text": "Code is like humor. When you have to explain it, it's bad.", "author": "Cory House"},
        {"text": "Make it work, make it right, make it fast.", "author": "Kent Beck"},
        {"text": "Simplicity is the soul of efficiency.", "author": "Austin Freeman"},
        {"text": "Before software can be reusable it first has to be usable.", "author": "Ralph Johnson"},
        {"text": "The most damaging phrase in the language is.. it's always been done this way", "author": "Grace Hopper"}
    ]
    return quotes[int(datetime.now().timestamp()) % len(quotes)]

def _fetch_from_quotable():
    """Fetch quote from Quotable API."""
    resp = requests.get(
        'https://api.quotable.io/random?tags=technology|programming|wisdom',
        timeout=10,
        verify=False
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        'text': data.get('content', ''),
        'author': data.get('author', '')
    }

def _fetch_from_adviceslip():
    """Fetch quote from AdviceSlip API (fallback)."""
    resp = requests.get('https://api.adviceslip.com/advice', timeout=10)
    resp.raise_for_status()
    data = resp.json()
    slip = data.get('slip', {})
    return {
        'text': slip.get('advice', ''),
        'author': 'Daily Wisdom'
    }

def fetch_weather(city='Beijing'):
    """Fetch weather from Open-Meteo"""
    print("Fetching weather...")
    try:
        # Get coordinates for major cities
        cities = {
            'Beijing': (39.9042, 116.4074),
            'Shanghai': (31.2304, 121.4737),
            'Shenzhen': (22.5431, 114.0579),
            'Hangzhou': (30.2741, 120.1551)
        }
        
        lat, lon = cities.get(city, cities['Beijing'])
        
        url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code,relative_humidity_2m,wind_speed_10m&timezone=Asia/Shanghai'
        
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            current = data.get('current', {})
            
            weather_codes = {
                0: '晴', 1: '大部晴朗', 2: '多云', 3: '阴',
                45: '雾', 48: '雾凇', 51: '小毛毛雨', 53: '中毛毛雨',
                61: '小雨', 63: '中雨', 65: '大雨', 71: '小雪',
                73: '中雪', 75: '大雪', 80: '阵雨', 95: '雷暴'
            }
            
            return {
                'city': city,
                'temperature': current.get('temperature_2m', 0),
                'weather': weather_codes.get(current.get('weather_code', 0), '未知'),
                'humidity': current.get('relative_humidity_2m', 0),
                'wind_speed': current.get('wind_speed_10m', 0)
            }
    except Exception as e:
        print(f"  ⚠️ Weather: {e}")
    
    return None

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.join(script_dir, '..', 'data')
    repo_dir = os.path.abspath(repo_dir)
    os.makedirs(repo_dir, exist_ok=True)
    
    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'quote': fetch_quotes(),
        'weather': fetch_weather('Beijing')
    }
    
    output_file = os.path.join(repo_dir, 'misc.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved to {output_file}")

if __name__ == '__main__':
    main()
