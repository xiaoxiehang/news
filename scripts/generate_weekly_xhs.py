#!/usr/bin/env python3
"""每周日生成「本周 AI 大事盘点」小红书发布包。

读取 data/archive/briefing-YYYY-MM-DD.json 最近 7 天，用 LLM 选出
本周 5 大事件 + 3 个最值得用的工具/技巧，输出到 data/xhs_weekly/<周日日期>/：
  post.json / picks.json / cover.png / card_01..08.png / end.png

用法: python scripts/generate_weekly_xhs.py [--date YYYY-MM-DD]
环境变量: LLM_API_KEY（必填）/ LLM_BASE_URL / LLM_MODEL（与 generate_xhs_post.py 同）
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta

SITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SITE_ROOT, 'scripts'))
from generate_xhs_post import call_llm, assemble_body, published_text, LLM_API_KEY
from generate_xhs_cards import draw_cover, draw_card, draw_end

N_EVENTS = 5
N_TOOLS = 3
N_TOTAL = N_EVENTS + N_TOOLS
MIN_CANDIDATES = 12


def _norm(title):
    return re.sub(r'[\s\W_]+', '', (title or '').lower())


def collect_candidates(sunday):
    """收集最近 7 天（含周日）的 briefing picks，去重。"""
    seen = set()
    cands = []
    for i in range(6, -1, -1):
        d = (sunday - timedelta(days=i)).strftime('%Y-%m-%d')
        path = os.path.join(SITE_ROOT, 'data', 'archive', 'briefing-%s.json' % d)
        if not os.path.isfile(path):
            print('   跳过缺失: %s' % d)
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get('picks', []):
            key = _norm(p.get('title', ''))
            if not key or key in seen:
                continue
            seen.add(key)
            cands.append({'title': p.get('title', ''), 'summary': p.get('summary', ''),
                          'source': p.get('source', ''), 'url': p.get('url', ''),
                          'date': d})
    print('collect: %d 条候选（去重后）' % len(cands))
    return cands


def build_prompt(cands):
    lines = []
    for i, c in enumerate(cands):
        lines.append('%d. %s（%s，来源：%s）\n   %s' % (
            i, c['title'], c['date'], c['source'], c['summary']))
    cands_text = '\n'.join(lines)
    return (
        '你是小红书账号"鸡仔AI早报"的运营，每周日发布一篇"本周AI大事盘点"图文。\n'
        '从下面这一周的 AI 新闻候选中，选出【本周 5 大事件】+【3 个普通人最值得用的工具/技巧】，\n'
        '按重要性/获得感排序（5 个事件在前，3 个工具在后），为每条写小红书文案。\n\n'
        '候选（共 %d 条）：\n%s\n\n'
        '要求：\n'
        '1. 只输出 JSON，不要解释。格式：\n'
        '{"title": "...", "hook": "...", '
        '"items": [{"pick": 候选编号, "point": "...", "usage": "...", "comment": "..."}], '
        '"question": "...", "tags": ["鸡仔AI早报", ...], "jinju": "..."}\n'
        '2. title 不超过 20 个字，示例"本周AI盘点｜8条必看+3神器"，不要带日期。\n'
        '3. hook 一句话开场钩子，点出本周最大看点。\n'
        '4. point：这条新闻讲了什么，1-2 句大白话，不超过 60 字，不要极客梗。\n'
        '5. usage：一句话"普通人能怎么用"，必须具体可操作；纯资讯类可写"适合谁关注"。\n'
        '6. comment：一句话"鸡仔说"点评，大白话、有态度，20-40 字。\n'
        '7. tags：首位必须是"鸡仔AI早报"，再加 4-6 个相关标签（含"一周盘点"）。\n'
        '8. question：结尾互动提问，问本周相关的问题。\n'
        '9. jinju：一句本周金句，20 字以内。\n'
        '10. 注意：最终发布正文（含标签）最多 1000 字，point 务必精简。'
        % (len(cands), cands_text)
    )


def main():
    parser = argparse.ArgumentParser(description='生成本周 AI 大事盘点小红书发布包')
    parser.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'),
                        help='周日日期 YYYY-MM-DD，默认当天')
    args = parser.parse_args()
    sunday = datetime.strptime(args.date, '%Y-%m-%d')
    date_str = args.date

    cands = collect_candidates(sunday)
    if len(cands) < MIN_CANDIDATES:
        print('FAIL: 候选不足（%d < %d），本周跳过' % (len(cands), MIN_CANDIDATES))
        sys.exit(1)
    if not LLM_API_KEY:
        print('FAIL: 缺少 LLM_API_KEY，无法生成周盘点文案')
        sys.exit(1)

    print('calling LLM...')
    post = call_llm(build_prompt(cands))
    items_in = post.get('items', [])
    if len(items_in) != N_TOTAL:
        print('FAIL: LLM 返回条目数不对（%d != %d）' % (len(items_in), N_TOTAL))
        sys.exit(1)

    picks, items = [], []
    for it in items_in:
        idx = it.get('pick', 0)
        if not isinstance(idx, int) or not (0 <= idx < len(cands)):
            print('FAIL: 非法候选编号: %r' % (idx,))
            sys.exit(1)
        c = cands[idx]
        picks.append({'title': c['title'], 'summary': c['summary'],
                      'source': c['source'], 'url': c['url']})
        items.append({'point': it.get('point', ''), 'usage': it.get('usage', ''),
                      'comment': it.get('comment', '')})

    def _pub_len(b):
        # 与质检脚本完全一致的发布全文长度：正文 + 换行 + #标签行
        return len(published_text(dict(post, body=b)))

    slim_items = [dict(it) for it in items]
    body = assemble_body(dict(post, items=slim_items), picks,
                         list_title='本周 8 大看点',
                         fav_line='收藏这篇，下周接着看')
    if _pub_len(body) > 1000:
        print('正文超 1000 字，自动精简 point 描述')
        body = assemble_body(dict(post, items=slim_items), picks, include_point=False,
                             list_title='本周 8 大看点',
                             fav_line='收藏这篇，下周接着看')
    # 兜底压缩：去掉 point 仍超限时，逐轮截短最长的 usage/comment，
    # 直到全文 <=1000，保证质检长度项必过（卡片与正文用同一套 slim_items）
    while _pub_len(body) > 1000:
        target = None
        for it in slim_items:
            for k in ('usage', 'comment'):
                v = it.get(k) or ''
                if len(v) > 20 and (target is None or len(v) > len(target[2])):
                    target = (it, k, v)
        if target is None:
            break
        it, k, v = target
        it[k] = v[:max(20, int(len(v) * 0.7))]
        body = assemble_body(dict(post, items=slim_items), picks, include_point=False,
                             list_title='本周 8 大看点',
                             fav_line='收藏这篇，下周接着看')
    if _pub_len(body) > 1000:
        # 最后一道防线：硬截断正文（保留标签行），绝不让超长包流到质检
        tags_line = ' '.join('#' + t for t in (post.get('tags') or []))
        body = body[:1000 - 1 - len(tags_line)].rstrip()
    print('正文定稿：全文 %d 字' % _pub_len(body))
    post = dict(post, body=body, items=slim_items,
                fallback=False, generated_at=datetime.now().isoformat())

    out_dir = os.path.join(SITE_ROOT, 'data', 'xhs_weekly', date_str)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'post.json'), 'w', encoding='utf-8') as f:
        json.dump(post, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, 'picks.json'), 'w', encoding='utf-8') as f:
        json.dump({'date': date_str, 'picks': picks}, f, ensure_ascii=False, indent=2)

    footer = '鸡仔 · 每周日晚的AI盘点'
    draw_cover(picks, os.path.join(out_dir, 'cover.png'),
               big_title='本周AI盘点', footer_text=footer,
               tip_text='一次看懂本周 AI 大事')
    for i, p in enumerate(picks):
        draw_card(p, slim_items[i], i, N_TOTAL,
                  os.path.join(out_dir, 'card_%02d.png' % (i + 1)))
    draw_end(post.get('jinju', ''), post.get('question', ''),
             os.path.join(out_dir, 'end.png'),
             fav_text='收藏这篇，下周接着看', footer_text=footer)
    print('cards ok: %d 张 -> %s/' % (N_TOTAL + 2, out_dir))

    root = os.path.join(SITE_ROOT, 'data', 'xhs_weekly')
    index = []
    for d in sorted(os.listdir(root), reverse=True):
        pp = os.path.join(root, d, 'post.json')
        if not os.path.isfile(pp):
            continue
        try:
            with open(pp, encoding='utf-8') as f:
                pj = json.load(f)
            index.append({'date': d, 'title': pj.get('title', '')})
        except Exception:
            continue
    with open(os.path.join(root, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print('index ok: %d 期' % len(index))
    print('标题: %s' % post.get('title'))


if __name__ == '__main__':
    main()
