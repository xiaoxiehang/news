#!/usr/bin/env python3
"""小红书开源项目介绍卡片：浅色风 + 深色代码条。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_xhs_cards import _font, _wrap, _clean, W, H
from PIL import Image, ImageDraw

BG = (250, 247, 242)
INK = (26, 26, 28)
GRAY = (110, 108, 102)
DIM = (165, 160, 150)
YELLOW = (245, 197, 24)
YELLOW_D = (150, 110, 5)
WHITE = (255, 255, 255)
BROWN = (70, 50, 5)
CODE_BG = (28, 28, 32)
CODE_INK = (245, 197, 24)
WARN_BG = (253, 236, 234)
WARN_INK = (170, 44, 38)


def _new():
    img = Image.new('RGB', (W, H), BG)
    return img, ImageDraw.Draw(img)

_dummy_img = Image.new('RGB', (W, H), BG)
dummy_d = ImageDraw.Draw(_dummy_img)


def _pill(d, x, y, text):
    f = _font(34)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 56, y + 58], radius=29, fill=YELLOW)
    d.text((x + 28, y + 12), text, font=f, fill=BROWN)


def _header(d, idx, total):
    _pill(d, 70, 56, '开源项目介绍')
    f = _font(36)
    t = f'{idx + 1:02d} / {total:02d}'
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 68), t, font=f, fill=DIM)


GHOST = (235, 231, 221)

def _ghost_num(d, idx, y_center):
    """背景大数字水印"""
    f = _font(430)
    t = f'{idx + 1:02d}'
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, y_center - 215), t, font=f, fill=GHOST)

def _measure_card(title, bullets, code):
    """预量内容卡高度，返回 (title_lines, bullet_lines_list, code_h, total_h)"""
    f_title, f_b = _font(64), _font(38)
    tl = _wrap(dummy_d, _clean(title), f_title, W - 140)[:2]
    th = len(tl) * 90
    bl = []
    bh = 0
    for b in bullets:
        ln = _wrap(dummy_d, _clean(b), f_b, W - 140 - 56)[:3]
        bl.append(ln)
        bh += len(ln) * 58 + 22
    ch = 0
    if code:
        f_c = _font(38)
        cl = _wrap(dummy_d, _clean(code), f_c, W - 140 - 64)
        ch = 16 + 36 + len(cl) * 58 + 28
    total = th + 30 + bh + ch
    return tl, bl, ch, total

def draw_cover(kicker, title, subtitle, stats, points, path):
    img, d = _new()
    _pill(d, 70, 56, kicker)
    f_title, f_sub, f_st = _font(96), _font(46), _font(38)
    tl = _wrap(d, _clean(title), f_title, W - 140)[:2]
    sl = _wrap(d, _clean(subtitle), f_sub, W - 140)[:2]
    # 预量
    th = len(tl) * 124 + 10 + len(sl) * 64 + 30 + 72 + 130 + 10
    ph = 0
    f_t = _font(40)
    pl = []
    for pt in points:
        ln = _wrap(d, _clean(pt), f_t, W - 300)[:2]
        pl.append(ln)
        ph += len(ln) * 60 + 44
    total_h = th + 60 + ph
    top, bottom = 190, H - 120
    y = top + max(0, (bottom - top - total_h) / 2)
    for ln in tl:
        d.text((70, y), ln, font=f_title, fill=INK)
        y += 124
    y += 10
    for ln in sl:
        d.text((72, y), ln, font=f_sub, fill=YELLOW_D)
        y += 64
    y += 30
    tw = d.textlength(stats, font=f_st)
    d.rounded_rectangle([70, y, 70 + tw + 56, y + 72], radius=36, fill=INK)
    d.text((98, y + 16), stats, font=f_st, fill=WHITE)
    y += 130
    d.rectangle([72, y, 200, y + 10], fill=YELLOW)
    y += 60
    f_n = _font(42)
    for i, ln in enumerate(pl):
        cy = y + 30
        d.ellipse([78, cy - 30, 138, cy + 30], fill=YELLOW)
        n = str(i + 1)
        nw = d.textlength(n, font=f_n)
        d.text((108 - nw / 2, cy - 31), n, font=f_n, fill=BROWN)
        for l2 in ln:
            d.text((168, y), l2, font=f_t, fill=INK)
            y += 60
        y += 44
    img.save(path)


def draw_card(title, bullets, code, idx, total, path):
    img, d = _new()
    _header(d, idx, total)
    tl, bl, ch, total_h = _measure_card(title, bullets, code)
    # 内容在 header 下方区域垂直居中
    top, bottom = 190, H - 120
    y = top + max(0, (bottom - top - total_h) / 2)
    _ghost_num(d, idx, top + (bottom - top) / 2)
    f_title = _font(64)
    for ln in tl:
        d.text((70, y), ln, font=f_title, fill=INK)
        y += 90
    y += 30
    f_b = _font(38)
    for lines in bl:
        for j, ln in enumerate(lines):
            if j == 0:
                d.ellipse([72, y + 14, 96, y + 38], fill=YELLOW)
            d.text((118, y), ln, font=f_b, fill=INK)
            y += 58
        y += 22
    if code:
        y += 16
        f_c = _font(38)
        cl = _wrap(d, _clean(code), f_c, W - 140 - 64)
        chh = 36 + len(cl) * 58 + 28
        d.rounded_rectangle([70, y, W - 70, y + chh], radius=20, fill=CODE_BG)
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([100 + k * 34, y + 22, 122 + k * 34, y + 44], fill=c)
        ty = y + 58
        for ln in cl:
            d.text((104, ty), '$ ' + ln if not ln.startswith('/') else ln,
                   font=f_c, fill=CODE_INK)
            ty += 58
    img.save(path)


def draw_end(jinju, question, path):
    img, d = _new()
    _pill(d, 70, 56, '开源项目介绍')
    f_j, f_q, f_fav = _font(56), _font(42), _font(40)
    jl = _wrap(d, _clean(jinju), f_j, W - 140)[:3]
    ql = _wrap(d, _clean(question), f_q, W - 140)[:3]
    t = '收藏这篇，下次让 AI 做页面时翻出来'
    total_h = len(jl) * 84 + 60 + 10 + 70 + len(ql) * 66 + 40 + 84
    top, bottom = 190, H - 120
    y = top + max(0, (bottom - top - total_h) / 2)
    for ln in jl:
        d.text((70, y), ln, font=f_j, fill=INK)
        y += 84
    y += 60
    d.rectangle([72, y, 200, y + 10], fill=YELLOW)
    y += 70
    for ln in ql:
        d.text((70, y), ln, font=f_q, fill=GRAY)
        y += 66
    y += 40
    tw = d.textlength(t, font=f_fav)
    d.rounded_rectangle([(W - tw) / 2 - 30, y, (W + tw) / 2 + 30, y + 84],
                        radius=42, fill=YELLOW)
    d.text(((W - tw) / 2, y + 20), t, font=f_fav, fill=BROWN)
    img.save(path)


if __name__ == '__main__':
    d = 'data/xhs-drafts/2026-10-04-impeccable'
    os.makedirs(d, exist_ok=True)
    draw_cover('开源项目介绍 · GitHub 今日趋势', 'impeccable',
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
               '在 AI 编程工具里执行初始化，生成 PRODUCT.md',
               '以后直接喊话：/impeccable polish，收工'],
              'npx impeccable install', 2, 3, f'{d}/card_03.png')
    draw_end('AI 负责写代码，审美这件事有人替你盯着了。',
             '你被 AI 的"AI 味"页面丑到过吗？评论区聊聊。',
             f'{d}/end.png')
    print('项目介绍卡片已生成')
