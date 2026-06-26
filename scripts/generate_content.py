#!/usr/bin/env python3
"""从 Horizon 摘要文件提取新闻数据，生成小红书/公众号文案和封面图"""
import json
import os
import re
import subprocess
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
date_slug = datetime.now().strftime('%Y%m%d')
date_str = datetime.now().strftime('%Y年%m月%d日')

# ===== Step 1: 从 Horizon 读取摘要 =====
horizon_file = f'/workspace/Horizon/data/summaries/horizon-{today}-zh.md'
if not os.path.exists(horizon_file):
    # 找最新的
    summaries_dir = '/workspace/Horizon/data/summaries'
    files = sorted([f for f in os.listdir(summaries_dir) if f.endswith('-zh.md')], reverse=True)
    if not files:
        print('❌ 未找到 Horizon 摘要文件')
        exit(1)
    horizon_file = os.path.join(summaries_dir, files[0])
    print(f'⚠️ 未找到今日文件，使用: {files[0]}')

print(f'📰 {date_str} 新闻简讯')
print('━━━━━━━━━━━━━━━━━━━━')
print(f'\n📖 从 Horizon 读取: {os.path.basename(horizon_file)}')

with open(horizon_file, 'r', encoding='utf-8') as f:
    content = f.read()

# ===== Step 2: 解析新闻条目 =====
# 匹配 ## [标题](url) ⭐️ 分数 后面的内容
item_pattern = re.compile(
    r'## \[(.+?)\]\((https?://[^)]+)\)(?:\s*⭐️\s*([\d.]+)/10)?\n\n'
    r'(.+?)\n\n'
    r'(?:rss|hackernews|github)\s*·\s*(.+?)\s*·\s*(.+?)$',
    re.MULTILINE
)

news_list = []
for match in item_pattern.finditer(content):
    title, url, score, summary, source, time_info = match.groups()
    
    # 推断分类
    source_lower = source.lower()
    if 'ai' in source_lower or 'openai' in source_lower or 'anthropic' in source_lower or 'deepmind' in source_lower:
        category = 'AI'
    elif 'techcrunch' in source_lower or 'verge' in source_lower or 'wired' in source_lower or 'ars' in source_lower:
        category = '科技'
    elif 'ithome' in source_lower or 'ifanr' in source_lower or 'sspai' in source_lower:
        category = '数码'
    elif 'github' in source_lower:
        category = '开发'
    else:
        category = '科技'
    
    news_list.append({
        'title': title.strip(),
        'summary': summary.strip()[:200],
        'source': source.strip(),
        'link': url.strip(),
        'published': date_str,
        'category': category,
        'score': float(score) if score else 0
    })

# 按评分排序，取前18条
news_list.sort(key=lambda x: x['score'], reverse=True)
top_news = news_list[:18]

print(f'  ✅ 解析 {len(news_list)} 条新闻，精选 {len(top_news)} 条')

# ===== Step 3: 保存 news_data.json =====
output_dir = f'/workspace/news-repo/output/{date_slug}'
os.makedirs(output_dir, exist_ok=True)

with open(f'{output_dir}/news_data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'date': today,
        'date_str': date_str,
        'count': len(top_news),
        'news': top_news
    }, f, ensure_ascii=False, indent=2)
print(f'  📁 保存: {output_dir}/news_data.json')

# 同时更新根目录的 news_data.json（供前端读取）
with open('/workspace/news-repo/news_data.json', 'w', encoding='utf-8') as f:
    json.dump({
        'date': today,
        'date_str': date_str,
        'count': len(top_news),
        'news': top_news
    }, f, ensure_ascii=False, indent=2)

# ===== Step 4: 生成小红书文案 =====
def format_xhs_content(news_list, date_str):
    lines = [f'📰 {date_str} 新闻简讯', '', '今日精选 15 条重要新闻 👇', '━' * 20, '']
    
    category_emoji = {'国内': '🇨🇳', '国际': '🌍', '科技': '💻', '数码': '📱', 'AI': '🤖', '开发': '🛠️', '财经': '💰', '其他': '📋'}
    
    for i, news in enumerate(news_list[:15], 1):
        emoji = category_emoji.get(news.get('category', '其他'), '📋')
        lines.append(f'{emoji} {i}. {news["title"]}')
        if news.get('summary'):
            lines.append(f'   {news["summary"][:100]}')
        lines.append('')
    
    lines.extend(['━' * 20, '💡 觉得有用的话，记得点赞收藏哦～', '#新闻简讯 #每日新闻 #国内外新闻 #热点资讯 #新闻早知道'])
    return '\n'.join(lines)

# ===== Step 5: 生成公众号文案 =====
def format_wechat_content(news_list, date_str):
    lines = [f'📋 每日新闻简讯 | {date_str}', '', '各位读者好，以下是今日精选的 15 条国内外重要新闻：', '', '━' * 40, '']
    
    for i, news in enumerate(news_list[:15], 1):
        lines.append(f'{i}. {news["title"]}')
        if news.get('summary'):
            lines.append(f'   {news["summary"][:150]}')
        lines.append('')
    
    lines.extend(['━' * 40, '以上内容为今日精选新闻简讯，感谢阅读。', '欢迎转发分享，让更多人了解世界动态。'])
    return '\n'.join(lines)

xhs_content = format_xhs_content(top_news, date_str)
wechat_content = format_wechat_content(top_news, date_str)

with open(f'{output_dir}/content_xhs.txt', 'w', encoding='utf-8') as f:
    f.write(xhs_content)
print(f'  ✅ 小红书内容: {output_dir}/content_xhs.txt')

with open(f'{output_dir}/content_wechat.txt', 'w', encoding='utf-8') as f:
    f.write(wechat_content)
print(f'  ✅ 公众号内容: {output_dir}/content_wechat.txt')

# 同时复制到根目录
with open('/workspace/news-repo/content_xhs.txt', 'w', encoding='utf-8') as f:
    f.write(xhs_content)
with open('/workspace/news-repo/content_wechat.txt', 'w', encoding='utf-8') as f:
    f.write(wechat_content)

# ===== Step 6: 生成封面 HTML =====
def generate_cover_html(news_list, date_str, variant='xhs'):
    """生成封面 HTML（小红书 3:4 或公众号 2.35:1）"""
    top5 = news_list[:5]
    
    if variant == 'xhs':
        width, height = 1080, 1440
        bg_gradient = 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)'
    else:
        width, height = 1080, 460
        bg_gradient = 'linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%)'
    
    news_html = ''
    for i, news in enumerate(top5, 1):
        title = news['title']
        if len(title) > 40:
            title = title[:37] + '...'
        news_html += f'''
        <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:16px;">
            <span style="background:#e94560;color:white;font-size:20px;font-weight:700;
                  min-width:32px;height:32px;border-radius:50%;display:flex;
                  align-items:center;justify-content:center;">{i}</span>
            <span style="color:#f0f0f0;font-size:{24 if variant=='xhs' else 22}px;
                  line-height:1.5;font-weight:500;">{title}</span>
        </div>'''
    
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{width}px; height:{height}px; overflow:hidden;
       font-family:'Noto Sans SC',sans-serif; }}
.cover {{ width:{width}px; height:{height}px; background:{bg_gradient};
          padding:{50 if variant=='xhs' else 30}px {50 if variant=='xhs' else 40}px;
          display:flex; flex-direction:column; justify-content:center; }}
.header {{ margin-bottom:30px; }}
.date {{ color:#e94560; font-size:18px; font-weight:700; letter-spacing:2px; }}
.title {{ color:white; font-size:{36 if variant=='xhs' else 30}px; font-weight:900;
          margin-top:8px; line-height:1.3; }}
.divider {{ width:60px; height:4px; background:#e94560; margin:20px 0; border-radius:2px; }}
.news-list {{ flex:1; }}
.footer {{ margin-top:20px; color:rgba(255,255,255,0.5); font-size:14px; }}
</style></head>
<body><div class="cover">
    <div class="header">
        <div class="date">📰 每日新闻简讯</div>
        <div class="title">{date_str}</div>
    </div>
    <div class="divider"></div>
    <div class="news-list">{news_html}</div>
    <div class="footer">今日精选 {len(news_list)} 条重要新闻</div>
</div></body></html>'''

# 生成小红书封面
xhs_html = generate_cover_html(top_news, date_str, 'xhs')
with open(f'{output_dir}/cover_xhs.html', 'w', encoding='utf-8') as f:
    f.write(xhs_html)

# 生成公众号封面
wechat_html = generate_cover_html(top_news, date_str, 'wechat')
with open(f'{output_dir}/cover_wechat.html', 'w', encoding='utf-8') as f:
    f.write(wechat_html)

# ===== Step 7: 截图生成 PNG =====
print('\n🎨 生成封面图...')

try:
    subprocess.run([
        'chromium-browser', '--headless=new', '--no-sandbox',
        '--disable-gpu', '--window-size=1080,1440',
        f'--screenshot={output_dir}/cover_xhs.png',
        f'file://{output_dir}/cover_xhs.html'
    ], capture_output=True, timeout=30)
    print(f'  ✅ 小红书封面: {output_dir}/cover_xhs.png')
    
    subprocess.run([
        'chromium-browser', '--headless=new', '--no-sandbox',
        '--disable-gpu', '--window-size=1080,460',
        f'--screenshot={output_dir}/cover_wechat.png',
        f'file://{output_dir}/cover_wechat.html'
    ], capture_output=True, timeout=30)
    print(f'  ✅ 公众号封面: {output_dir}/cover_wechat.png')
    
    # 复制到根目录
    import shutil
    shutil.copy2(f'{output_dir}/cover_xhs.png', '/workspace/news-repo/cover_xhs.png')
    shutil.copy2(f'{output_dir}/cover_wechat.png', '/workspace/news-repo/cover_wechat.png')
    
except Exception as e:
    print(f'  ⚠️ 封面生成失败: {e}')

print(f'\n✅ 全部完成！')
print(f'  📂 输出目录: {output_dir}/')
