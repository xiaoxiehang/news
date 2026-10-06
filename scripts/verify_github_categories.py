#!/usr/bin/env python3
"""LLM 审核 GitHub 分类：把放错类的项目踢掉。

读取 data/github.json，对每个分类的前 N 个项目做归属校验，
不属于该分类的移除（不回填，保证展示的都是对的）。
没有 LLM_API_KEY 时静默跳过。
"""

import json
import os
from datetime import datetime

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').strip().rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', '').strip() or 'gpt-6-sol'

CHECK_TOP_N = 50  # 每个分类审核前 50 个（最显眼的）


def _post_llm(prompt):
    headers = {'Authorization': f'Bearer {LLM_API_KEY}', 'Content-Type': 'application/json'}
    urls = [f'{LLM_BASE_URL}/chat/completions']
    if not LLM_BASE_URL.rstrip('/').endswith('/v1'):
        urls.append(f'{LLM_BASE_URL}/v1/chat/completions')
    last_err = None
    for url in urls:
        try:
            r = requests.post(url, headers=headers, json={
                'model': LLM_MODEL,
                'messages': [
                    {'role': 'system', 'content': '你是一个严格的分类审核员。只输出合法 JSON，不要输出其他内容。'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.2,
                'response_format': {'type': 'json_object'},
            }, timeout=120)
            r.raise_for_status()
            data = r.json()
            return json.loads(data['choices'][0]['message']['content'])
        except Exception as e:
            last_err = e
    raise last_err


def build_prompt(cat_name, cat_desc, repos):
    lines = []
    for r in repos:
        topics = ','.join(r.get('topics', [])[:5])
        lines.append(f"- {r['full_name']} | 描述:{r.get('description') or '无'} | 标签:{topics or '无'}")
    return f"""下面这些 GitHub 项目被分到了「{cat_name}」（{cat_desc}）分类。

请逐个判断是否真的属于这个分类。标准要严：
- 通用工具、通用 AI 框架、跟该行业无关的项目，一律判为不属于
- 只有项目本身就是为该行业/领域服务的，才算属于
- 描述是中文的也要判断，不要因为看不懂就放过

项目列表：
{chr(10).join(lines)}

只输出 JSON，格式：
{{"results": [{{"full_name": "owner/repo", "ok": true}}, {{"full_name": "owner/repo", "ok": false}}]}}
full_name 必须与列表完全一致，一个都不能少。"""


def main():
    src = os.path.join(DATA_DIR, 'github.json')
    if not os.path.exists(src):
        print('⏭️ 没有 github.json，跳过审核')
        return
    if not LLM_API_KEY:
        print('⏭️ 未设置 LLM_API_KEY，跳过审核')
        return

    with open(src, encoding='utf-8') as f:
        data = json.load(f)

    total_removed = 0
    for cat_id, cat in (data.get('categories') or {}).items():
        repos = cat.get('repos') or []
        check = repos[:CHECK_TOP_N]
        if not check:
            continue
        print(f'🔍 审核 {cat["name"]}（{len(check)} 个）...')
        try:
            result = _post_llm(build_prompt(cat['name'], cat.get('desc', ''), check))
        except Exception as e:
            print(f'   ❌ 审核失败，保留原数据: {e}')
            continue
        ok_map = {x.get('full_name'): x.get('ok', True) for x in result.get('results', [])}
        kept, removed = [], []
        for r in repos:
            if r['full_name'] in ok_map and not ok_map[r['full_name']]:
                # 只踢掉已审核的前 N 个里的，不碰后面的
                if r in check:
                    removed.append(r['full_name'])
                    continue
            kept.append(r)
        if removed:
            print(f'   🗑️ 踢掉 {len(removed)} 个: {", ".join(removed[:5])}' + ('...' if len(removed) > 5 else ''))
            total_removed += len(removed)
        else:
            print('   ✅ 全部通过')
        cat['repos'] = kept

    # leaderboard / rising 也顺带审核（归属"热榜"无所谓，只踢明显垃圾）
    data['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(src, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'\n✅ 审核完成，共踢掉 {total_removed} 个错分类项目')


if __name__ == '__main__':
    main()
