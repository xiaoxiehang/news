#!/usr/bin/env python3
"""给 GitHub 热榜项目生成中文 AI 点评。

读取 data/github.json（hot 分类前 12 个项目），调用 LLM 一次生成全部点评，
输出 data/github_insights.json：
  {full_name: {what, why_hot, who}}

没有 LLM_API_KEY 时静默跳过（保留旧数据）。
"""
import json
import os
from datetime import datetime

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').strip().rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-chat').strip()

MAX_REPOS = 12


def _chat_urls():
    urls = [f'{LLM_BASE_URL}/chat/completions']
    if not LLM_BASE_URL.rstrip('/').endswith('/v1'):
        urls.append(f'{LLM_BASE_URL}/v1/chat/completions')
    return urls


def _post_llm(headers, payload):
    """POST chat completions；自动兼容网关地址带/不带 /v1 的情况"""
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
    headers = {'Authorization': f'Bearer {LLM_API_KEY}', 'Content-Type': 'application/json'}
    payload = {
        'model': LLM_MODEL,
        'messages': [
            {'role': 'system', 'content': '你是一个资深开发者，熟悉开源生态。你只输出合法的 JSON，不要输出其他内容。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.6,
        'response_format': {'type': 'json_object'},
    }
    data = _post_llm(headers, payload)
    content = data['choices'][0]['message']['content']
    return json.loads(content)


def build_prompt(repos):
    lines = []
    for i, r in enumerate(repos, 1):
        lines.append(
            f"{i}. {r['full_name']} | 语言:{r.get('language') or '未知'} | "
            f"stars:{r.get('stars', 0)} | 描述:{r.get('description') or '无'}"
        )
    return f"""下面是 GitHub 今日热榜项目，请为每个项目写中文点评。

项目列表：
{chr(10).join(lines)}

要求：
- what：用一句话中文说清楚这个项目是干什么的（不超过 40 字）
- why_hot：分析它最近为什么火，基于项目特点推测（不超过 40 字）
- who：一句话说明适合谁关注（不超过 30 字）
- 语言简洁、口语化，像朋友聊天，不说套话

只输出 JSON，格式：
{{"insights": [{{"full_name": "owner/repo", "what": "...", "why_hot": "...", "who": "..."}}]}}
按项目列表顺序返回，full_name 必须与列表完全一致。"""


def main():
    src = os.path.join(DATA_DIR, 'github.json')
    if not os.path.exists(src):
        print('⏭️ 没有 github.json，跳过点评生成')
        return
    if not LLM_API_KEY:
        print('⏭️ 未设置 LLM_API_KEY，跳过点评生成（保留旧数据）')
        return

    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    repos = (data.get('categories', {}).get('hot', {}).get('repos') or [])[:MAX_REPOS]
    if not repos:
        print('⏭️ 热榜为空，跳过')
        return

    print(f'🤖 正在生成 {len(repos)} 个项目的中文点评...')
    try:
        result = call_llm(build_prompt(repos))
    except Exception as e:
        print(f'❌ 点评生成失败: {e}')
        return

    insights = {}
    for item in result.get('insights', []):
        fn = item.get('full_name')
        if fn and item.get('what'):
            insights[fn] = {
                'what': item.get('what', ''),
                'why_hot': item.get('why_hot', ''),
                'who': item.get('who', ''),
            }
    if not insights:
        print('❌ 点评结果为空，跳过保存')
        return

    out = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'insights': insights,
    }
    out_path = os.path.join(DATA_DIR, 'github_insights.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f'✅ 点评已生成: {len(insights)} 个项目 -> {out_path}')


if __name__ == '__main__':
    main()
