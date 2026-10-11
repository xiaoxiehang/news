#!/usr/bin/env python3
"""小红书开源项目介绍卡片 v4：浅色轻盈玻璃拟态（2026-10-11 全类型统一）。

- 背景：浅色透光 + 柔光色块
- 内容：悬浮玻璃面板（重模糊 + 白透 + 白描边 + 柔阴影）
- 字体：标题 SemiBold / 正文 Regular
- 视觉 helper 见 xhs_light.py（教程/周报共用）。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_xhs_cards import _clean, W, H
from PIL import Image, ImageDraw
import xhs_light as xl


def draw_cover(title, subtitle, stats, points, path):
    img = xl.bg()
    d = xl.header(img, '开源项目介绍', 'GitHub 今日趋势')
    f_t, f_s, f_st = xl.fs(xl.T_HERO), xl.fr(42), xl.fr(36)
    tl = []
    for seg in title.split('｜'):
        tl.extend(xl.wrap2(d, seg, f_t, W - 280))
    tl = tl[:2]
    sl = xl.wrap2(d, subtitle, f_s, W - 280)[:2]
    f_p = xl.fr(38)
    pl = [xl.wrap2(d, p, f_p, W - 280 - 90)[:2] for p in points]
    top_pad, bot_pad = 72, 72
    ch = (top_pad + len(tl) * 170 + 14 + len(sl) * 62 + 44
          + 96 + sum(len(x) * 62 + 40 for x in pl) + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in tl:
        d.text((118, y), ln, font=f_t, fill=xl.INK)
        y += 170
    y += 14
    for ln in sl:
        d.text((120, y), ln, font=f_s, fill=xl.AMBER_D)
        y += 62
    y += 44
    d.text((120, y), stats, font=f_st, fill=xl.MUTED)
    y += 110
    f_n = xl.fs(40)
    for i, lines in enumerate(pl):
        for j, ln in enumerate(lines):
            if j == 0:
                cy = y + 28
                d.ellipse([120, cy - 26, 172, cy + 26], fill=xl.YELLOW)
                xl.ctext(d, 146, cy, str(i + 1), f_n, xl.BROWN)
            d.text((200, y), ln, font=f_p, fill=xl.BODY)
            y += 62
        y += 48
    img.save(path)


def draw_card(title, bullets, code, idx, total, path):
    img = xl.bg()
    d = xl.header(img, '开源项目介绍', 'GitHub 今日趋势')
    f = xl.fr(34)
    t = '%02d / %02d' % (idx + 1, total)
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 112), t, font=f, fill=xl.MUTED)
    f_title, f_b = xl.fs(60), xl.fr(37)
    tl = xl.wrap2(d, title, f_title, W - 280)[:2]
    bl = [xl.wrap2(d, b, f_b, W - 280 - 60)[:3] for b in bullets]
    chh = 0
    cl = []
    if code:
        f_c = xl.fr(36)
        cl = xl.wrap2(d, code, f_c, W - 280 - 80)
        chh = 30 + 40 + len(cl) * 56 + 34
    top_pad, bot_pad = 68, 68
    ch = (top_pad + len(tl) * 88 + 44 + sum(len(x) * 66 + 26 for x in bl)
          + (chh + 30 if code else 0) + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=xl.INK)
        y += 88
    y += 44
    for lines in bl:
        for j, ln in enumerate(lines):
            if j == 0:
                d.ellipse([120, y + 16, 142, y + 38], fill=xl.YELLOW)
            d.text((166, y), ln, font=f_b, fill=xl.BODY)
            y += 66
        y += 26
    if code:
        y += 4
        d.rounded_rectangle([118, y, px1 - 70, y + chh], radius=24,
                            fill=xl.CODE_BG)
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([148 + k * 32, y + 26, 168 + k * 32, y + 46], fill=c)
        ty = y + 70
        for ln in cl:
            d.text((148, ty), '$ ' + ln, font=xl.fr(36), fill=xl.CODE_INK)
            ty += 56
    img.save(path)


def draw_end(jinju, question, path):
    img = xl.bg()
    d = xl.header(img, '开源项目介绍', 'GitHub 今日趋势')
    f_j, f_q = xl.fs(52), xl.fr(40)
    jl = xl.wrap2(d, jinju, f_j, W - 280)[:3]
    ql = xl.wrap2(d, question, f_q, W - 280)[:3]
    t = '收藏这篇，用得上时翻出来'
    f_btn = xl.fs(38)
    top_pad, bot_pad = 120, 72
    ch = (top_pad + len(jl) * 80 + 70 + len(ql) * 62 + 48 + 88 + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in jl:
        d.text((118, y), ln, font=f_j, fill=xl.INK)
        y += 80
    y += 70
    for ln in ql:
        d.text((118, y), ln, font=f_q, fill=xl.GRAY)
        y += 62
    y += 48
    tw = d.textlength(t, font=f_btn)
    d.rounded_rectangle([(W - tw) / 2 - 34, y, (W + tw) / 2 + 34, y + 88],
                        radius=44, fill=xl.YELLOW)
    xl.ctext(d, W / 2, y + 44, t, f_btn, xl.BROWN)
    img.save(path)


def build_from_data(data, d):
    """data: {kicker, title, subtitle, stats, points[], cards[{title,bullets[],code}], jinju, question} 到目录 d。"""
    os.makedirs(d, exist_ok=True)
    cards = data['cards']
    draw_cover(data['title'], data['subtitle'], data['stats'], data['points'], f'{d}/cover.png')
    for idx, c in enumerate(cards):
        draw_card(c['title'], c['bullets'], c.get('code'), idx, len(cards), f'{d}/card_{idx + 1:02d}.png')
    draw_end(data['jinju'], data['question'], f'{d}/end.png')
    return [f'{d}/cover.png'] + [f'{d}/card_{idx + 1:02d}.png' for idx in range(len(cards))] + [f'{d}/end.png']


if __name__ == '__main__':
    import json
    if len(sys.argv) > 1:
        data = json.load(open(sys.argv[1], encoding='utf-8'))
        out = sys.argv[2] if len(sys.argv) > 2 else 'data/xhs-drafts/' + data.get('slug', 'project')
        print(build_from_data(data, out))
    else:
        d = 'data/xhs-drafts/2026-10-04-impeccable'
        os.makedirs(d, exist_ok=True)
        draw_cover('impeccable',
                   '专治 AI 生成页面的"AI 味"',
                   '今日涨星 623 · 总 Star 74k',
                   ['作者 Paul Bakaus，前谷歌工程师',
                    '1 个 skill + 24 条设计命令 + 61 条检测规则',
                    '开源免费，Apache 2.0 协议'],
                   f'{d}/cover.png')
        draw_card('为什么 AI 做的页面一眼假',
                  ['Inter 字体包打天下，紫蓝渐变走天下',
                   '卡片套卡片，每个标题上顶个圆角图标',
                   '灰字印在彩色底上，根本看不清',
                   '所有模型都学同一套 SaaS 模板，审美趋同'],
                  None, 0, 3, f'{d}/card_01.png')
        draw_card('它给 AI 立了 61 条设计军规',
                  ['别用 Inter 和系统默认字体，别玩紫蓝渐变',
                   '禁止卡片套卡片，禁止灰字压彩底',
                   '24 条命令：polish 润色、critique 评审、bolder 加料、quieter 收敛',
                   '检测规则不用 LLM 也能跑，浏览器插件直接扫'],
                  None, 1, 3, f'{d}/card_02.png')
        draw_card('三步上手，5 分钟装好',
                  ['项目根目录运行安装命令',
                   '在 AI 编程工具里执行初始化',
                   '以后直接喊话 /impeccable polish 收工'],
                  'npx impeccable install', 2, 3, f'{d}/card_03.png')
        draw_end('AI 负责写代码，审美有人替你盯着了。',
                 '你被 AI 的"AI 味"页面丑到过吗？评论区聊聊。',
                 f'{d}/end.png')
        print('浅色玻璃拟态项目卡片已生成')
