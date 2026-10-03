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

DEFAULT_TAGS = ['鸡仔AI早报', 'AI资讯', '打工人日常', 'AI提效', '人工智能', '科技早报']
DEFAULT_QUESTION = '这 8 条里，你最想亲手试试的是哪个？评论区说说👇'
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
    today = briefing.get('date', '')
    try:
        _dt = datetime.strptime(today, '%Y-%m-%d')
        short_date = f'{_dt.month}月{_dt.day}日'
    except Exception:
        short_date = date_str
    return f"""你是小红书科技区博主"鸡仔"，每天发"鸡仔AI早报"图文笔记。
你的读者不是程序员，而是对 AI 感兴趣的普通打工人、学生党、自媒体人。
你的核心能力是"翻译"：把 AI 圈的黑话新闻，翻译成普通人能听懂、觉得有用的话。

今天是{date_str}，下面是今天的 8 条科技新闻：

{items}

请为今天的早报笔记写小红书文案。要求：
1. 标题不超过 20 个字，固定格式"{short_date}鸡仔AI早报｜+利益点"，利益点必须是完整词组（4-8字），
   比如"打工人提效8条""3个工具先收藏""学生党必看"，严禁输出"职效""你省"这类被截断的半截词。
   前 18 字内含"AI"关键词，不用"最/第一"等极限词。
2. 开头 hook：2 行口语化文案，先给结论、制造期待。
3. 为每条新闻写：
   - point（1-2 句口语化介绍，第一人称像朋友聊天，把技术黑话翻译成人话，不说公文腔，不超过 60 字）；
   - usage（一句话"普通人能怎么用"，具体、可行动，不超过 40 字；没有明确用法的就写实在话如"吃瓜了解一下就行"）；
   - comment（一句话点评，大白话、有观点，程序员和非程序员都能看懂，不超过 40 字）。
4. order：把 8 条按"普通人获得感"从强到弱排序，输出原序号数组（如 [7,6,1,5,4,2,3,8]），
   最有用的放最前，纯行业/时事放最后。
5. 结尾 question：一句具体的开放性提问，引导评论。
6. tags：5-8 个全中文话题标签，大词+人群词+精准词组合，必须包含"鸡仔AI早报"。
7. jinju：今日金句一句话，和效率/好奇心/打工人相关，口语化。
8. 平台限制：小红书正文最多 1000 字（含末尾 #标签行）。请控制 point/usage/comment
   的长度，让组装后的正文（hook + 8 条 + 结尾提问 + 声明 + 标签行）尽量不超过 1000 字。

只返回 JSON，不要有其他内容，格式：
{{"title": "标题", "hook": "开头两行文案（用\\n分隔）",
 "items": [{{"point": "口语化介绍", "usage": "普通人能怎么用", "comment": "一句话点评"}}],
 "order": [7, 6, 1, 5, 4, 2, 3, 8],
 "question": "结尾提问", "tags": ["鸡仔AI早报", "..."], "jinju": "今日金句"}}
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
    title = f'{short_date}鸡仔AI早报｜打工人必看8条'
    hook = '每天 3 分钟，跟上 AI 圈动态👇\n今天这 8 条值得你看看'
    items = [{'point': p['summary'], 'usage': '', 'comment': ''} for p in picks]
    return {
        'title': title[:20],
        'hook': hook,
        'items': items,
        'question': DEFAULT_QUESTION,
        'tags': DEFAULT_TAGS[:6],
        'jinju': '别追每一个新模型，追那个让你少加班的。',
        'fallback': True,
        'order': list(range(1, len(picks) + 1)),
    }


def assemble_body(post, picks, include_point=True,
                  list_title='📋 今日 8 条速览', fav_line='📌 收藏这篇，持续更新'):
    """组装完整正文：hook + 清单 + 结尾引导 + AI 声明。picks 为重排后的新闻列表。

    include_point=False 时去掉每条的 point 长描述（小红书正文上限 1000 字时的
    精简模式：保留标题/用法/点评/来源）。
    list_title / fav_line 供周盘点等其他栏目定制。
    """
    parts = [post['hook'], '', list_title, '']
    numerals = '①②③④⑤⑥⑦⑧'
    for i, p in enumerate(picks):
        item = post['items'][i] if i < len(post['items']) else {}
        parts.append(f"{numerals[i]} {p['title']}")
        if include_point and item.get('point'):
            parts.append(item['point'])
        if item.get('usage'):
            parts.append(f"💡 你能怎么用：{item['usage']}")
        if item.get('comment'):
            parts.append(f"💬 鸡仔说：{item['comment']}")
        if p.get('source'):
            parts.append(f"（来源：{p['source']}）")
        parts.append('')
    parts.append(fav_line)
    parts.append(post.get('question') or DEFAULT_QUESTION)
    parts.append('')
    parts.append(AI_DISCLAIMER)
    return '\n'.join(parts).strip()


def published_text(post):
    """发布时实际填入平台的完整文本：正文 + 换行 + #标签。"""
    tags_line = ' '.join('#' + t for t in (post.get('tags') or []))
    return (post.get('body') or '').strip() + '\n' + tags_line


def apply_order(picks, order):
    """按 LLM 返回的 order（原序号 1-based）重排 picks；非法时返回原序。"""
    n = len(picks)
    if (not isinstance(order, list) or len(order) != n
            or sorted(order) != list(range(1, n + 1))):
        return picks
    return [picks[i - 1] for i in order]


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

    if LLM_API_KEY:
        print(f'📝 调用 {LLM_MODEL} 生成小红书文案...')
        try:
            result = call_llm(build_prompt(briefing))
            n = len(briefing['picks'])
            items = result.get('items', [])
            # 对齐条数：少了就用 summary 补
            while len(items) < n:
                items.append({'point': briefing['picks'][len(items)]['summary'],
                              'usage': '', 'comment': ''})
            _raw_title = (result.get('title') or '').strip()
            _tail = _raw_title.rsplit('｜', 1)[-1].strip() if '｜' in _raw_title else _raw_title
            if len(_tail) < 4:
                _tail = '今日必看'
            _bt = briefing.get('date', '')
            try:
                _bdt = datetime.strptime(_bt, '%Y-%m-%d')
                short_date = f'{_bdt.month}月{_bdt.day}日'
            except Exception:
                short_date = briefing.get('date_str', _bt)
            _title = f'{short_date}鸡仔AI早报｜{_tail[:8]}'
            post = {
                'title': _title[:20],
                'hook': result.get('hook', ''),
                'items': [{'point': it.get('point', ''), 'usage': it.get('usage', ''),
                           'comment': it.get('comment', '')}
                          for it in items[:n]],
                'question': result.get('question') or DEFAULT_QUESTION,
                'tags': [t for t in result.get('tags', []) if t][:8] or DEFAULT_TAGS[:6],
                'jinju': result.get('jinju', ''),
                'fallback': False,
                'order': result.get('order') or list(range(1, n + 1)),
            }
        except Exception as e:
            print(f'❌ LLM 生成失败，降级为模板文案: {e}')
            post = fallback_post(briefing)
    else:
        print('⏭️ 未设置 LLM_API_KEY，使用模板降级文案')
        post = fallback_post(briefing)

    # 按获得感排序重排 picks 与 items（正文/卡片/封面头条保持一致）
    n = len(briefing['picks'])
    order = post.get('order') or list(range(1, n + 1))
    ordered_picks = apply_order(briefing['picks'], order)
    idx = [i - 1 for i in order]
    if len(post['items']) == n and sorted(idx) == list(range(n)):
        post['items'] = [post['items'][i] for i in idx]
        post['order'] = order
    # 快照当天重排后的 picks，供制卡脚本使用（与线上数据解耦）
    with open(os.path.join(out_dir, 'picks.json'), 'w', encoding='utf-8') as f:
        json.dump(
            {'date': today, 'date_str': briefing.get('date_str', today),
             'overview': briefing.get('overview', ''), 'picks': ordered_picks},
            f, ensure_ascii=False, indent=2)

    post['body'] = assemble_body(post, ordered_picks)
    # 小红书正文上限 1000 字（含末尾 #标签行）：超限则去掉每条的 point 长描述
    if len(published_text(post)) > 1000:
        post['body'] = assemble_body(post, ordered_picks, include_point=False)
        print(f"   正文超 1000 字，已按精简模式重组（去 point 长描述）")
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
