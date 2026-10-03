#!/usr/bin/env python3
"""小红书开源项目介绍卡片 v3：苹果简约风 + 毛玻璃。

- 背景：浅色渐变 + 柔光色块
- 内容：毛玻璃面板（模糊背景 + 半透明白）
- 字体：标题 SemiBold / 正文 Regular，宽松行距
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate_xhs_cards import _wrap, _clean, W, H
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_SEMI = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'fonts', 'NotoSansSC-SemiBold.ttf')
FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def _fs(size):
    return ImageFont.truetype(FONT_SEMI, size)


def _fr(size):
    try:
        return ImageFont.truetype(FONT_REG, size, index=2)
    except Exception:
        return ImageFont.truetype(FONT_REG, size)


# 苹果系配色
INK = (29, 29, 31)
GRAY = (110, 110, 115)
MUTED = (150, 150, 156)
YELLOW = (245, 197, 24)
YELLOW_D = (150, 110, 5)
BROWN = (70, 50, 5)
WHITE = (255, 255, 255)


def _bg():
    """浅色渐变 + 柔光色块背景"""
    img = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(img)
    top, bot = (252, 251, 247), (240, 235, 226)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    # 柔光色块
    blob = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    bd.ellipse([-220, -160, 620, 560], fill=(255, 214, 140, 90))     # 右上暖黄
    bd.ellipse([560, 900, 1300, 1600], fill=(255, 200, 190, 70))     # 左下柔粉
    bd.ellipse([-260, 780, 420, 1380], fill=(200, 225, 255, 55))     # 左中淡蓝
    blob = blob.filter(ImageFilter.GaussianBlur(130))
    img = Image.alpha_composite(img.convert('RGBA'), blob).convert('RGB')
    return img


def _frosted(img, box, radius=36, blur=24, tint=(255, 255, 255, 110),
             edge=True):
    """在 img 的 box 区域做毛玻璃面板"""
    x0, y0, x1, y1 = [int(v) for v in box]
    crop = img.crop((x0, y0, x1, y1))
    glass = crop.filter(ImageFilter.GaussianBlur(blur)).convert('RGBA')
    glass = Image.alpha_composite(
        glass, Image.new('RGBA', glass.size, tint))
    mask = Image.new('L', glass.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, glass.size[0], glass.size[1]], radius=radius, fill=255)
    img.paste(glass, (x0, y0), mask)
    if edge:
        ImageDraw.Draw(img, 'RGBA').rounded_rectangle(
            [x0, y0, x1, y1], radius=radius,
            outline=(255, 255, 255, 100), width=2)
    return img


def _pill(d, x, y, text):
    f = _fs(32)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 52, y + 54], radius=27, fill=YELLOW)
    d.text((x + 26, y + 11), text, font=f, fill=BROWN)


def _header(img):
    d = ImageDraw.Draw(img)
    _pill(d, 70, 56, '开源项目介绍')
    f = _fr(34)
    t = 'GitHub 今日趋势'
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 68), t, font=f, fill=MUTED)
    return d


def draw_cover(title, subtitle, stats, points, path):
    img = _bg()
    d = _header(img)
    # 中央毛玻璃面板
    f_t, f_s, f_st = _fs(92), _fr(42), _fr(36)
    tl = _wrap(d, _clean(title), f_t, W - 280)[:2]
    sl = _wrap(d, _clean(subtitle), f_s, W - 280)[:2]
    f_p = _fr(38)
    pl = [_wrap(d, _clean(p), f_p, W - 280 - 90)[:2] for p in points]
    ch = (len(tl) * 118 + 14 + len(sl) * 62 + 44
          + 96 + sum(len(x) * 62 + 40 for x in pl) + 20)
    px0, px1 = 70, W - 70
    py = (H - ch) / 2
    img = _frosted(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + 56
    for ln in tl:
        d.text((140, y), ln, font=f_t, fill=INK)
        y += 118
    y += 14
    for ln in sl:
        d.text((142, y), ln, font=f_s, fill=YELLOW_D)
        y += 62
    y += 44
    d.text((142, y), stats, font=f_st, fill=MUTED)
    y += 96
    f_n = _fs(40)
    for i, lines in enumerate(pl):
        for j, ln in enumerate(lines):
            if j == 0:
                cy = y + 28
                d.ellipse([142, cy - 26, 194, cy + 26], fill=YELLOW)
                n = str(i + 1)
                nw = d.textlength(n, font=f_n)
                d.text((168 - nw / 2, cy - 29), n, font=f_n, fill=BROWN)
            d.text((222, y), ln, font=f_p, fill=INK)
            y += 62
        y += 40
    img.save(path)


def draw_card(title, bullets, code, idx, total, path):
    img = _bg()
    d = _header(img)
    f = _fr(34)
    t = f'{idx + 1:02d} / {total:02d}'
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 112), t, font=f, fill=MUTED)
    f_title, f_b = _fs(60), _fr(37)
    tl = _wrap(d, _clean(title), f_title, W - 280)[:2]
    bl = [_wrap(d, _clean(b), f_b, W - 280 - 60)[:3] for b in bullets]
    chh = 0
    cl = []
    if code:
        f_c = _fr(36)
        cl = _wrap(d, _clean(code), f_c, W - 280 - 80)
        chh = 30 + 40 + len(cl) * 56 + 34
    ch = (len(tl) * 88 + 44 + sum(len(x) * 66 + 26 for x in bl)
          + (chh + 30 if code else 0) + 40)
    px0, px1 = 70, W - 70
    py = (H - ch) / 2 + 20
    img = _frosted(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + 52
    for ln in tl:
        d.text((140, y), ln, font=f_title, fill=INK)
        y += 88
    y += 44
    for lines in bl:
        for j, ln in enumerate(lines):
            if j == 0:
                d.ellipse([142, y + 16, 164, y + 38], fill=YELLOW)
            d.text((188, y), ln, font=f_b, fill=(58, 58, 62))
            y += 66
        y += 26
    if code:
        y += 4
        img = _frosted(img, (140, y, px1 - 70, y + chh), radius=24, blur=18,
                       tint=(24, 24, 28, 165), edge=False)
        d = ImageDraw.Draw(img)
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([170 + k * 32, y + 26, 190 + k * 32, y + 46], fill=c)
        ty = y + 70
        for ln in cl:
            d.text((170, ty), '$ ' + ln, font=_fr(36), fill=(245, 197, 24))
            ty += 56
    img.save(path)


def draw_end(jinju, question, path):
    img = _bg()
    d = _header(img)
    f_j, f_q = _fs(52), _fr(40)
    jl = _wrap(d, _clean(jinju), f_j, W - 280)[:3]
    ql = _wrap(d, _clean(question), f_q, W - 280)[:3]
    t = '收藏这篇，下次让 AI 做页面时翻出来'
    f_btn = _fs(38)
    ch = len(jl) * 80 + 70 + len(ql) * 62 + 48 + 88
    px0, px1 = 70, W - 70
    py = (H - ch) / 2 + 20
    img = _frosted(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + 56
    for ln in jl:
        d.text((140, y), ln, font=f_j, fill=INK)
        y += 80
    y += 70
    for ln in ql:
        d.text((140, y), ln, font=f_q, fill=GRAY)
        y += 62
    y += 48
    tw = d.textlength(t, font=f_btn)
    d.rounded_rectangle([(W - tw) / 2 - 34, y, (W + tw) / 2 + 34, y + 88],
                        radius=44, fill=YELLOW)
    d.text(((W - tw) / 2, y + 24), t, font=f_btn, fill=BROWN)
    img.save(path)


if __name__ == '__main__':
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
    print('苹果风+毛玻璃卡片已生成')
