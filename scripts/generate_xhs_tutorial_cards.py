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
    f_kick, f_big = xl.fs(48), xl.fs(96)
    kl = _wrap2(d, kicker, f_kick, W - 280)[:1]
    tl = []
    for t in title_lines:
        tl.extend(_wrap2(d, t, f_big, W - 280))
    tl = tl[:3]
    f_n, f_t = xl.fs(40), xl.fr(40)
    tip_ls = [_wrap2(d, tp, f_t, W - 280 - 90)[:2] for tp in tips]
    top_pad, bot_pad = 72, 72
    ch = (top_pad + len(kl) * 64 + 20 + len(tl) * 128 + 44
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
        y += 128
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
    """tip: {title, scene, user, ai, warn}。
    字号联动自适应：(气泡, 标题, 场景) 从 (40,76,38) 逐级降到 (34,66,32)，
    保证 16 行以内的内容避坑条不溢出。"""
    from PIL import ImageDraw
    img = xl.bg()
    d = xl.header(img, '鸡仔AI实战', '%02d / %02d' % (idx + 1, total))
    f_w = xl.fr(32)
    wl = _wrap2(d, '避坑：' + tip['warn'], f_w, W - 140 - 52)
    warn_h = 28 + len(wl) * 44 + 24
    px0, px1 = 70, W - 70
    max_w = px1 - px0 - 200

    f_scene = xl.fr(32)
    sl = _wrap2(d, tip['scene'], f_scene, W - 280)[:2]
    sstep = 52
    def _layout(bsize, tsize):
        f_bub, f_title = xl.fr(bsize), xl.fs(tsize)
        tl = _wrap2(d, tip['title'], f_title, W - 280)[:2]
        ul = _wrap2(d, tip['user'], f_bub, max_w - 52)
        al = _wrap2(d, tip['ai'], f_bub, max_w - 52)
        bstep, tstep = bsize + 16, tsize + 24
        uh = 30 + len(ul) * bstep + 26
        ah = 30 + len(al) * bstep + 26
        panel_h = 32 + uh + 24 + ah + 32
        total_h = (150 + len(tl) * tstep + 12 + len(sl) * sstep + 24
                   + panel_h + 24 + warn_h + 30)
        return (f_bub, f_title, tl, ul, al, bstep,
                uh, ah, panel_h, total_h)

    for combo in [(40, 72), (38, 68), (36, 64)]:
        (f_bub, f_title, tl, ul, al, bstep,
         uh, ah, panel_h, total_h) = _layout(*combo)
        if total_h <= H:
            break

    y = 150
    tstep = f_title.size + 24
    for ln in tl:
        d.text((70, y), ln, font=f_title, fill=xl.INK)
        y += tstep
    y += 12
    for ln in sl:
        d.text((70, y), ln, font=f_scene, fill=xl.GRAY)
        y += sstep
    y += 24
    img = xl.glass(img, (px0, y, px1, y + panel_h), radius=30)
    d = ImageDraw.Draw(img)
    by = y + 32
    bw = min(max_w, max(d.textlength(ln, font=f_bub) for ln in ul) + 52) if ul else 0
    bx = px1 - 96 - bw
    d.rounded_rectangle([bx, by, bx + bw, by + uh], radius=24,
                        fill=xl.USER_BUBBLE, outline=xl.USER_EDGE, width=2)
    ty = by + 26
    for ln in ul:
        d.text((bx + 26, ty), ln, font=f_bub, fill=xl.INK)
        ty += bstep
    xl.avatar(d, px1 - 44, by + 44, '你', xl.YELLOW, xl.BROWN)
    by2 = by + uh + 24
    bw2 = min(max_w, max(d.textlength(ln, font=f_bub) for ln in al) + 52) if al else 0
    bx2 = px0 + 96
    d.rounded_rectangle([bx2, by2, bx2 + bw2, by2 + ah], radius=24,
                        fill=xl.AI_BUBBLE, outline=xl.AI_EDGE, width=2)
    ty = by2 + 26
    for ln in al:
        d.text((bx2 + 26, ty), ln, font=f_bub, fill=xl.INK)
        ty += bstep
    xl.avatar(d, px0 + 44, by2 + 44, 'AI', (28, 28, 36), xl.WHITE)
    y = y + panel_h + 24
    crop = img.crop((70, y, W - 70, y + warn_h))
    tinted = Image.alpha_composite(
        crop.filter(ImageFilter.GaussianBlur(18)).convert('RGBA'),
        Image.new('RGBA', (W - 140, warn_h), xl.WARN_BG + (150,)))
    mask = Image.new('L', (W - 140, warn_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 140, warn_h], radius=20, fill=255)
    img.paste(tinted, (70, y), mask)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([70, y, W - 70, y + warn_h], radius=20,
                        outline=xl.WARN_EDGE, width=2)
    ty = y + 24
    for i, ln in enumerate(wl):
        d.text((104, ty), ln, font=f_w,
               fill=xl.WARN_TITLE if i == 0 else xl.INK)
        ty += 44
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
