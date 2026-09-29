#!/usr/bin/env python3
"""小红书图文笔记文案生成：标题 + 正文 + 标签 + 每条新闻一句话点评。

读取 data/briefing.json，调用 OpenAI 兼容的 LLM API，
输出 data/xhs/<YYYY-MM-DD>/post.json，供人工审核后发布。

环境变量：
  LLM_API_KEY   必填，没有则用模板降级生成（不报错）
  LLM_BASE_URL  默认 https://api.deepseek.com
  LLM_MODEL     默认 gpt-6-sol
"""
import json
import os
import re
from datetime import datetime

import requests

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SITE_DIR, 'data')

LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.deepseek.com').rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', '').strip() or 'gpt-6-sol'

DEFAULT_TAGS = ['科技早报', 'AI资讯', '人工智能', '科技新闻', '数码科技', '每日早报']
DEFAULT_QUESTION = '今天哪条新闻最让你意外？评论区聊聊👇'
AI_DISCLAIMER = '🤖 本内容由 AI 辅助生成，仅供资讯参考'


def _chat_urls():
    urls = [f'{LLM_BASE_URL}/chat/completions']
    if not LLM_BASE_URL.rstrip('/').endswith('/v1'):
        urls.append(f'{LLM_BASE_URL}/v1/chat/completions')
    return urls


def _post_llm(headers, payload):
    last_err = None
    for url in _chat_urls():
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            if 'choices' not in data:
                raise ValueError(f'网关返回异常: {str(data)[:150]}')
            return data
        except Exception as e:
            last_err = e
            print(f'   ⚠️ {url} 失败: {e}')
    raise last_err


def call_llm(prompt):
    data = _post_llm(
        {'Authorization': f'Bearer {LLM_API_KEY}', 'Content-Type': 'application/json'},
        {
            'model': LLM_MODEL,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': 0.7,
            'response_format': {'type': 'json_object'},
        },
    )
    content = data['choices'][0]['message']['content']
    m = re.search(r'\{.*\}', content, re.DOTALL)
    return json.loads(m.group(0) if m else content)


def build_prompt(briefing):
    lines = []
    for i, p in enumerate(briefing['picks'], 1):
        lines.append(f"{i}. {p['title']}\n   摘要：{p['summary']}\n   来源：{p['source']}")
    items = '\n\n'.join(lines)
    date_str = briefing.get('date_str', '')
    return f"""你是小红书科技区博主"鸡仔"，每天发"科技早报"图文笔记。
今天是{date_str}，下面是今天的 8 条科技新闻：

{items}

请为今天的早报笔记写小红书文案。要求：
1. 标题不超过 20 个字，包含日期，格式参考"9月29日科技早报｜Sonnet 5.5引爆，8条AI大新闻"，前 18 字内包含"科技早报""AI"两个关键词，不用"最/第一"等极限词。
2. 开头 hook：2 行口语化文案，先给结论、制造期待，比如"今天AI圈有3个大动静，打工人的饭碗又悬了👇"。
3. 为每条新闻写：point（2-3 句口语化介绍，第一人称，像朋友聊天，不说公文腔），comment（一句话毒辣点评，带观点、有梗，不超过 40 字）。
4. 结尾 question：一句开放性提问，引导评论。
5. tags：5-8 个全中文话题标签，大词+精准词组合。
6. jinju：今日金句一句话，和科技/效率/好奇心相关。

只返回 JSON，不要有其他内容，格式：
{{"title": "标题", "hook": "开头两行文案（用\\n分隔）",
 "items": [{{"point": "口语化介绍", "comment": "一句话点评"}}],
 "question": "结尾提问", "tags": ["科技早报", "..."], "jinju": "今日金句"}}
items 数组顺序必须与上面 8 条新闻一一对应。"""


def fallback_post(briefing):
    """LLM 不可用时的模板降级：标题/正文/标签直接由早报数据拼装。"""
    today = briefing.get('date', '')
    try:
        dt = datetime.strptime(today, '%Y-%m-%d')
        short_date = f'{dt.month}月{dt.day}日'
    except Exception:
        short_date = briefing.get('date_str', today)
    picks = briefing['picks']
    title = f'{short_date}科技早报｜8条AI大新闻速览'
    hook = '每天 3 分钟，跟上 AI 圈动态👇\n今天这 8 条值得你看看'
    items = [{'point': p['summary'], 'comment': ''} for p in picks]
    return {
        'title': title[:20],
        'hook': hook,
        'items': items,
        'question': DEFAULT_QUESTION,
        'tags': DEFAULT_TAGS[:6],
        'jinju': '保持好奇，明天见。',
        'fallback': True,
    }


def assemble_body(post, briefing):
    """组装完整正文：hook + 清单 + 结尾引导 + AI 声明。"""
    parts = [post['hook'], '', '📋 今日 8 条速览', '']
    numerals = '①②③④⑤⑥⑦⑧'
    for i, p in enumerate(briefing['picks']):
        item = post['items'][i] if i < len(post['items']) else {}
        parts.append(f"{numerals[i]} {p['title']}")
        if item.get('point'):
            parts.append(item['point'])
        if item.get('comment'):
            parts.append(f"💬 {item['comment']}")
        parts.append('')
    parts.append('📌 收藏这篇，明早接着看')
    parts.append(post.get('question') or DEFAULT_QUESTION)
    parts.append('')
    parts.append(AI_DISCLAIMER)
    return '\n'.join(parts).strip()


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    bpath = os.path.join(DATA_DIR, 'briefing.json')
    if not os.path.exists(bpath):
        print('❌ 缺少 data/briefing.json，先跑 generate_briefing.py')
        return
    with open(bpath, encoding='utf-8') as f:
        briefing = json.load(f)
    if not briefing.get('picks'):
        print('❌ 早报没有 picks，跳过')
        return

    out_dir = os.path.join(DATA_DIR, 'xhs', today)
    os.makedirs(out_dir, exist_ok=True)
    # 快照当天的 picks，供制卡脚本使用（与线上数据解耦）
    with open(os.path.join(out_dir, 'picks.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {'date': today, 'date_str': briefing.get('date_str', today),
             'overview': briefing.get('overview', ''), 'picks': briefing['picks']},
            f, ensure_ascii=False, indent=2)

    if LLM_API_KEY:
        print(f'📝 调用 {LLM_MODEL} 生成小红书文案...')
        try:
            result = call_llm(build_prompt(briefing))
            items = result.get('items', [])
            # 对齐条数：少了就用 summary 补
            while len(items) < len(briefing['picks']):
                items.append({'point': briefing['picks'][len(items)]['summary'], 'comment': ''})
            post = {
                'title': (result.get('title') or '')[:20],
                'hook': result.get('hook', ''),
                'items': [{'point': it.get('point', ''), 'comment': it.get('comment', '')}
                          for it in items[:len(briefing['picks'])]],
                'question': result.get('question') or DEFAULT_QUESTION,
                'tags': [t for t in result.get('tags', []) if t][:8] or DEFAULT_TAGS[:6],
                'jinju': result.get('jinju', ''),
                'fallback': False,
            }
        except Exception as e:
            print(f'❌ LLM 生成失败，降级为模板文案: {e}')
            post = fallback_post(briefing)
    else:
        print('⏭️ 未设置 LLM_API_KEY，使用模板降级文案')
        post = fallback_post(briefing)

    post['body'] = assemble_body(post, briefing)
    post['date'] = today
    post['generated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    out_path = os.path.join(out_dir, 'post.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(post, f, ensure_ascii=False, indent=2)
    print(f"✅ 小红书文案已生成 -> {out_path}")
    print(f"   标题: {post['title']}")
    print(f"   标签: {' '.join('#' + t for t in post['tags'])}")
    print(f"   正文 {len(post['body'])} 字{'（模板降级）' if post.get('fallback') else ''}")


if __name__ == '__main__':
    main()
