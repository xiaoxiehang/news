#!/usr/bin/env python3
"""小红书教程类卡片生成器 v4：浅色轻盈玻璃拟态（2026-10-11 全类型统一）。

设计语言：浅色透光底 + 柔光色块 + 悬浮玻璃面板 + 黄色点缀（见 xhs_light.py）。
内容结构不变：封面（kicker+标题+技巧列表）/ 技巧卡（标题+场景+你/AI
对话+避坑）/ 末页（金句+提问+收藏）。接口与之前版本完全一致。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import re as _re
from generate_xhs_cards import _clean, W, H
import xhs_light as xl
from PIL import Image, ImageDraw, ImageFilter

_PRICE_TAIL = _re.compile(r'¥[0-9.,/]*$')
_PUNCT = set('，。！？；：、）】”’')


def _wrap2(d, text, font, max_w, min_last=4):
    """换行：价格（¥开头）不拆散 + 防末行孤字。"""
    text = _clean(text)
    NO_START = set('，。！？；：、」』）】”’%·…—')
    lines, cur = [], ''
    for ch in text:
        t = cur + ch
        if d.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                m = _PRICE_TAIL.search(cur)
                if m and (ch.isdigit() or ch in '.,/' or ch == '年'):
                    head, price = cur[:m.start()], cur[m.start():]
                    if head:
                        lines.append(head)
                    cur = price + ch
                elif ch.isascii() and ch.isalnum():
                    i = len(cur)
                    while i > 0 and cur[i - 1].isascii() and cur[i - 1].isalnum():
                        i -= 1
                    if 0 < i < len(cur):
                        lines.append(cur[:i])
                        cur = cur[i:] + ch
                    else:
                        lines.append(cur)
                        cur = ch
                else:
                    lines.append(cur)
                    cur = ch
            else:
                cur = ch
    if cur:
        lines.append(cur)
    fixed = []
    for ln in lines:
        if fixed and ln and ln[0] in NO_START:
            fixed[-1] += ln[0]
            ln = ln[1:]
        if ln:
            fixed.append(ln)
    lines = fixed or ['']
    guard = 0
    while len(lines) >= 2 and len(lines[-1].strip()) < min_last and guard < 3:
        guard += 1
        last = lines.pop()
        prev = lines.pop()
        combo = prev + last
        n = len(combo)
        target = int(n * 0.55)
        cut = -1
        for i in range(target, n - 1):
            if combo[i] in _PUNCT:
                cut = i + 1
                break
        if cut < 0:
            for i in range(target, 1, -1):
                if combo[i] in _PUNCT:
                    cut = i + 1
                    break
        if cut < 0:
            cut = target
        l1, l2 = combo[:cut], combo[cut:]
        if (d.textlength(l1, font=font) <= max_w
                and d.textlength(l2, font=font) <= max_w
                and len(l2.strip()) >= min_last):
            lines.append(l1)
            lines.append(l2)
        else:
            lines.append(prev)
            lines.append(last)
            break
    return lines


def draw_cover_tutorial(kicker, title_lines, tips, path):
    img = xl.bg()
    d = xl.header(img, '鸡仔AI实战', '')
    f_kick, f_big = xl.fs(48), xl.fs(xl.T_HERO)
    kl = _wrap2(d, kicker, f_kick, W - 280)[:1]
    tl = []
    for t in title_lines:
        tl.extend(_wrap2(d, t, f_big, W - 280))
    tl = tl[:3]
    f_n, f_t = xl.fs(40), xl.fr(40)
    tip_ls = [_wrap2(d, tp, f_t, W - 280 - 90)[:2] for tp in tips]
    top_pad, bot_pad = 72, 72
    ch = (top_pad + len(kl) * 64 + 20 + len(tl) * 170 + 44
          + 10 + 60 + sum(len(x) * 56 + 40 for x in tip_ls) + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in kl:
        d.text((118, y), ln, font=f_kick, fill=xl.AMBER_D)
        y += 64
    y += 20
    for ln in tl:
        d.text((118, y), ln, font=f_big, fill=xl.INK)
        y += 170
    y += 44
    d.rectangle([118, y, 118 + 128, y + 10], fill=xl.YELLOW)
    y += 70
    for i, lines in enumerate(tip_ls):
        for j, ln in enumerate(lines):
            if j == 0:
                cy = y + 28
                d.ellipse([118, cy - 26, 170, cy + 26], fill=xl.YELLOW)
                xl.ctext(d, 144, cy, str(i + 1), f_n, xl.BROWN)
            d.text((198, y), ln, font=f_t, fill=xl.BODY)
            y += 56
        y += 40
    img.save(path)


def draw_tip_card(tip, idx, total, path):
    """与项目卡一模一样：标题 + 黄色圆点条目，无行内标签。"""
    from PIL import ImageDraw
    img = xl.bg()
    d = xl.header(img, '鸡仔AI实战', 'AI 提示词实战')
    f = xl.fr(34)
    t = '%02d / %02d' % (idx + 1, total)
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 112), t, font=f, fill=xl.MUTED)

    bullets = [tip['scene'], tip['user'], tip['ai'], tip['warn']]
    for tsize, bsize in [(60, 37), (56, 35), (52, 32)]:
        f_title, f_b = xl.fs(tsize), xl.fr(bsize)
        tl = xl.wrap2(d, tip['title'], f_title, W - 280)[:2]
        bl = [xl.wrap_first(d, b, f_b, W - 280 - 60, W - 280 - 60)[:4]
              for b in bullets]
        tstep, bstep = tsize + 28, bsize + 29
        ch = (68 + len(tl) * tstep + 44
              + sum(len(x) * bstep + 26 for x in bl) - 26 + 68)
        py = 150 + max(0, (H - 250 - ch) / 2)
        if py + ch <= H - 40:
            break

    img = xl.glass(img, (48, py, W - 48, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + 68
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=xl.INK)
        y += tstep
    y += 44
    for lines in bl:
        for j, ln in enumerate(lines):
            if j == 0:
                d.ellipse([120, y + 16, 142, y + 38], fill=xl.YELLOW)
            d.text((166, y), ln, font=f_b, fill=xl.BODY)
            y += bstep
        y += 26
    img.save(path)


def draw_end_tutorial(jinju, question, path, fav_text=None):
    img = xl.bg()
    d = xl.header(img, '鸡仔AI实战', '')
    f_j, f_q = xl.fs(48), xl.fr(40)
    jl = _wrap2(d, jinju, f_j, W - 280)[:3]
    ql = _wrap2(d, question, f_q, W - 280)[:3]
    t = fav_text or '收藏这篇，下次做报表时翻出来对照着用'
    f_btn = xl.fs(40)
    top_pad, bot_pad = 110, 72
    ch = (top_pad + len(jl) * 64 + 60 + 10 + 80 + len(ql) * 56 + 48 + 88 + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in jl:
        d.text((118, y), ln, font=f_j, fill=xl.INK)
        y += 64
    y += 60
    d.rectangle([118, y, 118 + 128, y + 10], fill=xl.YELLOW)
    y += 90
    for ln in ql:
        d.text((118, y), ln, font=f_q, fill=xl.GRAY)
        y += 56
    y += 48
    tw = d.textlength(t, font=f_btn)
    d.rounded_rectangle([(W - tw) / 2 - 34, y, (W + tw) / 2 + 34, y + 88],
                        radius=44, fill=xl.YELLOW)
    xl.ctext(d, W / 2, y + 44, t, f_btn, xl.BROWN)
    img.save(path)


TIPS = [
    {"title": "把 Excel 丢给 AI 洗",
     "scene": "电商运营，每月初导 3000 行订单明细，老板要各品类销售额+退货率汇总。",
     "user": "这是9月订单明细，A列下单日期、B列商品类目、C列金额、D列是否退货，按类目汇总销售额和退货率，输出一张表。",
     "ai": "搞定！3 个类目已汇总：数码 ¥68,200｜服装 ¥41,300（退货率 8.2% 最高）｜家居 ¥18,900。需要导出 Excel 吗？",
     "warn": "关键数字自己抽查两行，公式它偶尔手滑。"},
    {"title": "周报 5 分钟交差",
     "scene": "周五下午 5 点，周报还没动笔。",
     "user": "周一跟进 3 个客户，A 公司签了 2 万的单；周三写完 Q4 推广方案初稿；周四参加产品培训。扩写成正式周报，语气低调务实。",
     "ai": "周报已生成：本周跟进客户 3 家，签约 1 单（2 万元）；完成 Q4 推广方案初稿；参加产品培训 1 次。共 486 字。",
     "warn": "数字结论自己填，别让它编业绩。"},
    {"title": "汇报 PPT 10 分钟出大纲",
     "scene": "下周给总监汇报 Q4 推广方案，只有 15 分钟。",
     "user": "听众是总监，关心投入产出；讲 15 分钟；想让他记住：Q4 主攻短视频，预算 20 万，目标 200 万 GMV。",
     "ai": "大纲已生成：1. 现状：短视频 ROI 是图文 3 倍 2. 打法：Q4 主攻短视频 3. 预算 20 万 4. 目标 200 万 GMV。要展开第 2 部分吗？",
     "warn": "大纲是骨架，血肉必须是你的真实业务。"},
]


def build_from_data(data, d):
    """data: {kicker, title_lines, tips[{title,scene,user,ai,warn}], jinju, question} 到目录 d。"""
    os.makedirs(d, exist_ok=True)
    tips = data['tips']
    draw_cover_tutorial(data.get('kicker', '打工人必看'), data['title_lines'],
                        [t['title'] for t in tips], f'{d}/cover.png')
    for i, t in enumerate(tips):
        draw_tip_card(t, i, len(tips), f'{d}/card_{i + 1:02d}.png')
    draw_end_tutorial(data['jinju'], data['question'], f'{d}/end.png', data.get('fav_text'))
    return [f'{d}/cover.png'] + [f'{d}/card_{i + 1:02d}.png' for i in range(len(tips))] + [f'{d}/end.png']


if __name__ == '__main__':
    import json
    if len(sys.argv) > 1:
        data = json.load(open(sys.argv[1], encoding='utf-8'))
        out = sys.argv[2] if len(sys.argv) > 2 else 'data/xhs-drafts/' + data.get('slug', 'tutorial')
        print(build_from_data(data, out))
    else:
        d = 'data/xhs-drafts/2026-10-04'
        os.makedirs(d, exist_ok=True)
        draw_cover_tutorial('打工人必看', ['3个AI技巧', '报表1小时变10分钟'],
                            [t['title'] for t in TIPS], f'{d}/cover.png')
        for i, t in enumerate(TIPS):
            draw_tip_card(t, i, len(TIPS), f'{d}/card_{i + 1:02d}.png')
        draw_end_tutorial('AI 搭架子，你填里子，这个分工最稳。',
                          '这 3 招里，你最想先试哪一个？评论区扣 1，提示词原文发你。',
                          f'{d}/end.png')
        print('浅色玻璃拟态教程卡片已生成')
