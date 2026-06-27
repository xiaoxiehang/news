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

# 同时更新根目录和 data 目录的 news_data.json（供前端读取）
news_json = {
    'date': today,
    'date_str': date_str,
    'count': len(top_news),
    'news': top_news
}
with open('/workspace/news-repo/news_data.json', 'w', encoding='utf-8') as f:
    json.dump(news_json, f, ensure_ascii=False, indent=2)
with open('/workspace/news-repo/data/news_data.json', 'w', encoding='utf-8') as f:
    json.dump(news_json, f, ensure_ascii=False, indent=2)

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
    # 小红书显示8条新闻，公众号显示5条
    display_count = 8 if variant == 'xhs' else 5
    top_news_display = news_list[:display_count]
    
    # 分类图标映射
    category_icons = {
        'AI': '🤖',
        '科技': '💻',
        '数码': '📱',
        '开发': '🛠️',
        '国内': '🇨🇳',
        '国际': '🌍',
        '财经': '💰',
        '其他': '📋'
    }
    
    if variant == 'xhs':
        width, height = 1080, 1440
        # 小红书：更鲜艳的渐变 + 装饰背景
        bg_gradient = 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%)'
        decor_circles = '''
        <div style="position:absolute;top:-50px;right:-50px;width:300px;height:300px;
             background:rgba(255,255,255,0.1);border-radius:50%;"></div>
        <div style="position:absolute;bottom:-80px;left:-80px;width:400px;height:400px;
             background:rgba(255,255,255,0.08);border-radius:50%;"></div>
        <div style="position:absolute;top:50%;right:10%;width:200px;height:200px;
             background:rgba(255,255,255,0.05);border-radius:50%;"></div>
        '''
    else:
        width, height = 1080, 460
        bg_gradient = 'linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #7e8ba3 100%)'
        decor_circles = '''
        <div style="position:absolute;top:-30px;right:-30px;width:200px;height:200px;
             background:rgba(255,255,255,0.1);border-radius:50%;"></div>
        <div style="position:absolute;bottom:-50px;left:-50px;width:250px;height:250px;
             background:rgba(255,255,255,0.08);border-radius:50%;"></div>
        '''
    
    # 生成新闻列表（带分类图标）
    news_html = ''
    for i, news in enumerate(top_news_display, 1):
        title = news['title']
        category = news.get('category', '其他')
        icon = category_icons.get(category, '📋')
        
        # 根据变体调整标题长度
        max_len = 45 if variant == 'xhs' else 40
        if len(title) > max_len:
            title = title[:max_len-3] + '...'
        
        # 小红书：卡片式布局；公众号：简洁列表
        if variant == 'xhs':
            news_html += f'''
            <div style="display:flex;align-items:center;gap:16px;margin-bottom:20px;
                 background:rgba(255,255,255,0.15);backdrop-filter:blur(10px);
                 border-radius:16px;padding:18px 24px;box-shadow:0 8px 32px rgba(0,0,0,0.1);">
                <div style="font-size:32px;min-width:48px;height:48px;display:flex;
                     align-items:center;justify-content:center;">{icon}</div>
                <div style="flex:1;color:white;font-size:26px;line-height:1.4;
                     font-weight:600;">{title}</div>
            </div>'''
        else:
            news_html += f'''
            <div style="display:flex;align-items:flex-start;gap:12px;margin-bottom:14px;">
                <span style="background:#e94560;color:white;font-size:18px;font-weight:700;
                      min-width:28px;height:28px;border-radius:50%;display:flex;
                      align-items:center;justify-content:center;">{i}</span>
                <span style="color:#f0f0f0;font-size:22px;line-height:1.5;
                      font-weight:500;">{icon} {title}</span>
            </div>'''
    
    return f'''<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ width:{width}px; height:{height}px; overflow:hidden;
       font-family:'Noto Sans SC',sans-serif;position:relative; }}
.cover {{ width:{width}px; height:{height}px; background:{bg_gradient};
          padding:{50 if variant=='xhs' else 30}px;
          display:flex; flex-direction:column; position:relative; }}
.header {{ margin-bottom:30px;position:relative;z-index:10; }}
.date {{ color:rgba(255,255,255,0.9); font-size:20px; font-weight:700; 
         letter-spacing:2px;text-shadow:0 2px 8px rgba(0,0,0,0.2); }}
.title {{ color:white; font-size:{42 if variant=='xhs' else 32}px; font-weight:900;
          margin-top:10px; line-height:1.3; text-shadow:0 2px 8px rgba(0,0,0,0.2); }}
.divider {{ width:80px; height:5px; background:white; margin:25px 0; border-radius:3px;
           box-shadow:0 2px 8px rgba(0,0,0,0.2); }}
.news-list {{ flex:1; position:relative;z-index:10; }}
.footer {{ margin-top:auto; color:rgba(255,255,255,0.8); font-size:16px; 
          font-weight:600; position:relative;z-index:10;
          text-shadow:0 2px 8px rgba(0,0,0,0.2); }}
</style></head>
<body><div class="cover">
    {decor_circles}
    <div class="header">
        <div class="date">📰 每日新闻简讯</div>
        <div class="title">{date_str}</div>
    </div>
    <div class="divider"></div>
    <div class="news-list">{news_html}</div>
    <div class="footer">✨ 今日精选 {len(news_list)} 条重要新闻</div>
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
