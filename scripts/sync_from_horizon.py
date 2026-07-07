#!/usr/bin/env python3
"""从 Horizon 直接同步数据到 news-repo，按来源分类，不使用 AI 生成文案"""
import json
import os
import re
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
date_slug = datetime.now().strftime('%Y%m%d')

# 读取 Horizon 摘要文件
horizon_file = f'/workspace/Horizon/data/summaries/horizon-{today}-zh.md'
if not os.path.exists(horizon_file):
    print(f'❌ Horizon 文件不存在: {horizon_file}')
    exit(1)

print(f'📖 读取: {os.path.basename(horizon_file)}')

with open(horizon_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 解析新闻条目
# 匹配格式: ## [标题](链接) ⭐️ 分数/10\n\n内容\n\n来源 · 时间
pattern = re.compile(
    r'## \[(.+?)\]\((https?://[^)]+)\)(?:\s*⭐️\s*([\d.]+)/10)?\n\n'
    r'(.+?)\n\n'
    r'(rss|hackernews|github)\s*·\s*(.+?)\s*·\s*(\d+月\d+日\s*\d+:\d+)',
    re.MULTILINE | re.DOTALL
)

# 按来源分类
news_by_source = {
    'rss': [],
    'hackernews': [],
    'github': []
}

rss_by_site = {}
all_items = []

for match in pattern.finditer(content):
    title, url, score, summary, source, detail, time_info = match.groups()
    
    item = {
        'title': title.strip(),
        'url': url.strip(),
        'score': float(score) if score else 0,
        'summary': summary.strip(),
        'source': source,
        'detail': detail.strip(),
        'time': time_info.strip(),
        'timestamp': datetime.now().isoformat()
    }
    
    # 按来源分类
    if source == 'rss':
        # RSS 条目添加到 by_source
        news_by_source[source].append(item)
        # 同时按站点分类
        site = detail
        if site not in rss_by_site:
            rss_by_site[site] = []
        rss_by_site[site].append(item)
    else:
        news_by_source[source].append(item)
    
    all_items.append(item)

# 构建输出结构
output = {
    'date': today,
    'date_slug': date_slug,
    'generated_at': datetime.now().isoformat(),
    'total_count': len(all_items),
    'all_items': all_items,
    'by_source': news_by_source,
    'rss_by_site': rss_by_site
}

# 保存
output_dir = f'/workspace/news-repo/output/{date_slug}'
os.makedirs(output_dir, exist_ok=True)

output_file = f'{output_dir}/news_data.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f'✅ 已保存: {output_file}')
print(f'   总数: {output["total_count"]}')
print(f'   RSS: {len(news_by_source["rss"])} 条 (来自 {len(rss_by_site)} 个站点)')
print(f'   HackerNews: {len(news_by_source["hackernews"])} 条')
print(f'   GitHub: {len(news_by_source["github"])} 条')

# 按站点统计 RSS
for site, items in sorted(rss_by_site.items(), key=lambda x: len(x[1]), reverse=True):
    print(f'     - {site}: {len(items)} 条')
