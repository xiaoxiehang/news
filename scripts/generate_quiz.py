#!/usr/bin/env python3
"""每天生成一道开发者面试题（单选题）。

主题按日期轮换，避开最近 7 天出过的题目。
输出：
  data/quiz.json                  今日题目
  data/quiz/archive/YYYY-MM-DD.json  快照
  data/quiz/index.json            题目索引（倒序）

没有 LLM_API_KEY 时静默跳过（保留旧数据）。
"""
import json
import os
from datetime import datetime

import requests

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
QUIZ_DIR = os.path.join(DATA_DIR, 'quiz')
ARCHIVE_DIR = os.path.join(QUIZ_DIR, 'archive')

LLM_API_KEY = os.environ.get('LLM_API_KEY', '').strip()
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1').strip().rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', 'deepseek-chat').strip()

TOPICS = [
    'JavaScript 语言特性', 'TypeScript 类型体操', 'Python 实战',
    '网络与 HTTP', '数据库与 SQL', '系统设计', '算法与数据结构',
    'Git 与工程实践', 'AI 与大模型应用', 'CSS 与前端布局',
    'Go 并发编程', 'Rust 所有权', 'Web 安全', 'Linux 与运维',
]


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
            {'role': 'system', 'content': '你是一个资深技术面试官，擅长出有区分度的面试题。你只输出合法的 JSON，不要输出其他内容。'},
            {'role': 'user', 'content': prompt},
        ],
        'temperature': 0.8,
        'response_format': {'type': 'json_object'},
    }
    data = _post_llm(headers, payload)
    content = data['choices'][0]['message']['content']
    return json.loads(content)


def recent_questions():
    index_path = os.path.join(QUIZ_DIR, 'index.json')
    if not os.path.exists(index_path):
        return []
    try:
        with open(index_path, encoding='utf-8') as f:
            return [e.get('question', '') for e in json.load(f)[:7]]
    except Exception:
        return []


def build_prompt(topic, avoid):
    avoid_txt = ''
    if avoid:
        avoid_txt = '\n最近出过的题目（不要重复类似题目）：\n' + '\n'.join(f'- {q[:60]}' for q in avoid if q)
    return f"""请出一道「{topic}」方向的开发者面试单选题。

要求：
- 题目有区分度：考察真实理解，不是死记硬背；中等偏上难度
- 4 个选项，干扰项要有迷惑性（常见误区），但只有一个正确答案
- explanation：讲清楚为什么选这个，其他选项错在哪（150 字以内，中文）
- 口语化，像面试官在聊天
{avoid_txt}

只输出 JSON，格式：
{{"topic": "{topic}", "question": "...", "options": ["A...", "B...", "C...", "D..."], "answer": 0, "explanation": "..."}}
answer 是正确选项的下标（0-3）。题目和选项中不要出现"A."这类前缀字母。"""


def main():
    if not LLM_API_KEY:
        print('⏭️ 未设置 LLM_API_KEY，跳过出题（保留旧数据）')
        return

    today = datetime.now().strftime('%Y-%m-%d')
    topic = TOPICS[datetime.now().timetuple().tm_yday % len(TOPICS)]
    print(f'📝 今日主题：{topic}，正在出题...')

    try:
        result = call_llm(build_prompt(topic, recent_questions()))
    except Exception as e:
        print(f'❌ 出题失败: {e}')
        return

    options = result.get('options', [])
    answer = result.get('answer')
    if not result.get('question') or len(options) != 4 or answer not in (0, 1, 2, 3):
        print('❌ 题目格式不正确，跳过保存')
        return

    quiz = {
        'date': today,
        'date_str': datetime.now().strftime('%Y年%m月%d日'),
        'topic': result.get('topic', topic),
        'question': result['question'],
        'options': options,
        'answer': answer,
        'explanation': result.get('explanation', ''),
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, 'quiz.json'), 'w', encoding='utf-8') as f:
        json.dump(quiz, f, ensure_ascii=False, indent=2)
    with open(os.path.join(ARCHIVE_DIR, f'{today}.json'), 'w', encoding='utf-8') as f:
        json.dump(quiz, f, ensure_ascii=False, indent=2)

    index_path = os.path.join(QUIZ_DIR, 'index.json')
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
        'date_str': quiz['date_str'],
        'topic': quiz['topic'],
        'question': quiz['question'],
        'answer': quiz['answer'],
        'options': quiz['options'],
        'explanation': quiz['explanation'],
    })
    index.sort(key=lambda e: e['date'], reverse=True)
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'✅ 每日一题已生成: [{quiz["topic"]}] {quiz["question"][:40]}...')


if __name__ == '__main__':
    main()
