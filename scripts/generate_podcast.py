#!/usr/bin/env python3
"""把 data/briefing.json 转成播客音频（edge-tts 免费中文语音）。

输出：
  data/podcast/YYYY-MM-DD.mp3   当期音频
  data/podcast/index.json       节目列表（倒序）
  feed-podcast.xml              播客 RSS（含 enclosure，可订阅）

没有 briefing.json 或 TTS 失败时静默跳过，不影响流水线。
只保留最近 30 期音频。
"""
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SITE_ROOT = os.path.dirname(DATA_DIR)
PODCAST_DIR = os.path.join(DATA_DIR, 'podcast')
SITE_URL = 'https://xiaojj.pro'
VOICE = 'zh-CN-XiaoxiaoNeural'
HOST_NAME = '鸡仔'
KEEP_EPISODES = 30
WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']


def ensure_edge_tts():
    try:
        import edge_tts  # noqa
        return True
    except ImportError:
        print('  正在安装 edge-tts...')
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'edge-tts'])
            return True
        except Exception as e:
            print(f'  ❌ edge-tts 安装失败: {e}')
            return False


def num_to_cn(n):
    """1-10 转中文数字，用于第X条"""
    cn = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
    if 1 <= n <= 10:
        return cn[n - 1]
    return str(n)


def build_script(briefing):
    """把早报拼成口播稿"""
    today = briefing.get('date', datetime.now().strftime('%Y-%m-%d'))
    dt = datetime.strptime(today, '%Y-%m-%d')
    date_str = briefing.get('date_str') or dt.strftime('%Y年%m月%d日')
    weekday = WEEKDAYS[dt.weekday()]

    parts = [
        f'大家好，我是{HOST_NAME}，欢迎收听今日科技早报。',
        f'今天是{date_str}，星期{weekday}。',
    ]
    if briefing.get('overview'):
        parts.append(f'先来听听今天的大局：{briefing["overview"]}')

    picks = briefing.get('picks', [])
    if picks:
        parts.append(f'接下来是今天的{len(picks)}条必读。')
        for i, p in enumerate(picks, 1):
            seg = f'第{num_to_cn(i)}条，{p.get("title", "")}。'
            if p.get('summary'):
                seg += p['summary']
            parts.append(seg)

    parts.append(f'以上就是今天的科技早报，我是{HOST_NAME}，我们明天早上八点再见。')
    script = '\n'.join(parts)
    return script, len(picks)


async def synthesize(script, mp3_path):
    import edge_tts
    communicate = edge_tts.Communicate(script, VOICE)
    await communicate.save(mp3_path)


def estimate_duration(script):
    """按中文语速估算时长（秒）"""
    chars = len(script.replace('\n', ''))
    return max(30, int(chars / 4.2))


def fmt_duration(secs):
    m, s = divmod(secs, 60)
    return f'{m:02d}:{s:02d}'


def main():
    briefing_path = os.path.join(DATA_DIR, 'briefing.json')
    if not os.path.exists(briefing_path):
        print('⏭️ 没有 briefing.json，跳过播客生成')
        return

    with open(briefing_path, encoding='utf-8') as f:
        briefing = json.load(f)
    if not briefing.get('picks'):
        print('⏭️ 早报为空，跳过播客生成')
        return

    if not ensure_edge_tts():
        return

    today = briefing.get('date', datetime.now().strftime('%Y-%m-%d'))
    date_str = briefing.get('date_str', today)
    os.makedirs(PODCAST_DIR, exist_ok=True)
    mp3_path = os.path.join(PODCAST_DIR, f'{today}.mp3')

    script, count = build_script(briefing)
    print(f'🎙️ 口播稿 {len(script)} 字，{count} 条新闻，正在合成...')

    try:
        asyncio.run(synthesize(script, mp3_path))
    except Exception as e:
        print(f'❌ TTS 合成失败: {e}')
        if os.path.exists(mp3_path):
            os.remove(mp3_path)
        return

    size = os.path.getsize(mp3_path)
    duration = estimate_duration(script)
    print(f'✅ 音频已生成: {mp3_path} ({size // 1024} KB, 约{fmt_duration(duration)})')

    # 更新节目列表
    index_path = os.path.join(PODCAST_DIR, 'index.json')
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
        'date_str': date_str,
        'title': f'{date_str} 科技早报',
        'file': f'data/podcast/{today}.mp3',
        'overview': briefing.get('overview', ''),
        'count': count,
        'duration': fmt_duration(duration),
        'size': size,
    })
    index.sort(key=lambda e: e['date'], reverse=True)

    # 只保留最近 KEEP_EPISODES 期
    for old in index[KEEP_EPISODES:]:
        old_mp3 = os.path.join(PODCAST_DIR, f'{old["date"]}.mp3')
        if os.path.exists(old_mp3):
            os.remove(old_mp3)
    index = index[:KEEP_EPISODES]
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    # 生成播客 RSS
    items = []
    for e in index:
        url = f'{SITE_URL}/{e["file"]}'
        pub = datetime.strptime(e['date'], '%Y-%m-%d').strftime('%a, %d %b %Y 08:00:00 +0800')
        items.append(
            f'    <item>\n'
            f'      <title>{xml_escape(e["title"])}</title>\n'
            f'      <link>{SITE_URL}/podcast.html</link>\n'
            f'      <guid>{url}</guid>\n'
            f'      <pubDate>{pub}</pubDate>\n'
            f'      <description>{xml_escape(e["overview"])}</description>\n'
            f'      <enclosure url="{url}" length="{e["size"]}" type="audio/mpeg"/>\n'
            f'      <itunes:duration>{e["duration"]}</itunes:duration>\n'
            f'    </item>'
        )
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
        '<channel>\n'
        f'  <title>今日科技早报 · 播客版</title>\n'
        f'  <link>{SITE_URL}/podcast.html</link>\n'
        f'  <description>每天早上八点，{HOST_NAME}用五分钟带你听完科技圈大事。AI 精选 GitHub、Hacker News、掘金最值得读的新闻。</description>\n'
        f'  <language>zh-CN</language>\n'
        f'  <itunes:author>xiaojj.pro</itunes:author>\n'
        f'  <itunes:image href="{SITE_URL}/podcast-cover.png"/>\n'
        + '\n'.join(items) + '\n'
        + '</channel>\n</rss>\n'
    )
    feed_path = os.path.join(SITE_ROOT, 'feed-podcast.xml')
    with open(feed_path, 'w', encoding='utf-8') as f:
        f.write(feed)
    print(f'✅ 播客 RSS 已生成: {feed_path}（共 {len(index)} 期）')


if __name__ == '__main__':
    main()
