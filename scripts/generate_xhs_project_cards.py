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


PUNCT = set('，。！？；：、）】”’')

def _wrap2(d, text, font, max_w, min_last=4):
    """换行 + 防末行孤字：末行不足 min_last 个字时，从上一行匀字下来。"""
    lines = _wrap(d, _clean(text), font, max_w)
    lines = list(lines)
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
            if combo[i] in PUNCT:
                cut = i + 1
                break
        if cut < 0:
            for i in range(target, 1, -1):
                if combo[i] in PUNCT:
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

# 深色苹果风配色
INK = (245, 245, 247)
GRAY = (161, 161, 166)
MUTED = (120, 120, 128)
YELLOW = (245, 197, 24)
YELLOW_D = (150, 110, 5)
BROWN = (70, 50, 5)
WHITE = (255, 255, 255)


def _bg():
    """浅色渐变 + 柔光色块背景"""
    img = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(img)
    top, bot = (14, 14, 18), (30, 30, 38)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    # 柔光色块
    blob = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    bd.ellipse([-220, -160, 620, 560], fill=(90, 90, 200, 55))       # 右上靛蓝
    bd.ellipse([560, 900, 1300, 1600], fill=(200, 150, 60, 40))      # 左下暗金
    bd.ellipse([-260, 780, 420, 1380], fill=(60, 120, 200, 40))      # 左中深蓝
    blob = blob.filter(ImageFilter.GaussianBlur(130))
    img = Image.alpha_composite(img.convert('RGBA'), blob).convert('RGB')
    return img


def _frosted(img, box, radius=36, blur=24, tint=(255, 255, 255, 22),
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
            outline=(255, 255, 255, 45), width=2)
    return img


def _ctext(d, cx, cy, text, font, fill):
    """以文字墨迹中心为锚点绘制（真正的视觉居中）"""
    b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2),
           text, font=font, fill=fill)


def _pill(d, x, y, text):
    f = _fs(32)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 52, y + 54], radius=27, fill=YELLOW)
    _ctext(d, x + 26 + tw / 2, y + 27, text, f, BROWN)


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
    tl = _wrap2(d, _clean(title), f_t, W - 280)[:2]
    sl = _wrap2(d, _clean(subtitle), f_s, W - 280)[:2]
    f_p = _fr(38)
    pl = [_wrap2(d, _clean(p), f_p, W - 280 - 90)[:2] for p in points]
    _top_pad, _bot_pad = 72, 72
    ch = (_top_pad + len(tl) * 118 + 14 + len(sl) * 62 + 44
          + 96 + sum(len(x) * 62 + 40 for x in pl) + _bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    py1 = py + ch
    img = _frosted(img, (px0, py, px1, py1), radius=40)
    d = ImageDraw.Draw(img)
    y = py + _top_pad
    for ln in tl:
        d.text((118, y), ln, font=f_t, fill=INK)
        y += 118
    y += 14
    for ln in sl:
        d.text((120, y), ln, font=f_s, fill=YELLOW)
        y += 62
    y += 44
    d.text((120, y), stats, font=f_st, fill=MUTED)
    y += 110
    f_n = _fs(40)
    for i, lines in enumerate(pl):
        for j, ln in enumerate(lines):
            if j == 0:
                cy = y + 28
                d.ellipse([120, cy - 26, 172, cy + 26], fill=YELLOW)
                _ctext(d, 146, cy, str(i + 1), f_n, BROWN)
            d.text((200, y), ln, font=f_p, fill=(214, 214, 218))
            y += 62
        y += 48
    img.save(path)


def draw_card(title, bullets, code, idx, total, path):
    img = _bg()
    d = _header(img)
    f = _fr(34)
    t = f'{idx + 1:02d} / {total:02d}'
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 112), t, font=f, fill=MUTED)
    f_title, f_b = _fs(60), _fr(37)
    tl = _wrap2(d, _clean(title), f_title, W - 280)[:2]
    bl = [_wrap2(d, _clean(b), f_b, W - 280 - 60)[:3] for b in bullets]
    chh = 0
    cl = []
    if code:
        f_c = _fr(36)
        cl = _wrap2(d, _clean(code), f_c, W - 280 - 80)
        chh = 30 + 40 + len(cl) * 56 + 34
    _top_pad, _bot_pad = 68, 68
    ch = (_top_pad + len(tl) * 88 + 44 + sum(len(x) * 66 + 26 for x in bl)
          + (chh + 30 if code else 0) + _bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    py1 = py + ch
    img = _frosted(img, (px0, py, px1, py1), radius=40)
    d = ImageDraw.Draw(img)
    y = py + _top_pad
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=INK)
        y += 88
    y += 44
    for lines in bl:
        for j, ln in enumerate(lines):
            if j == 0:
                d.ellipse([120, y + 16, 142, y + 38], fill=YELLOW)
            d.text((166, y), ln, font=f_b, fill=(214, 214, 218))
            y += 66
        y += 26
    if code:
        y += 4
        img = _frosted(img, (118, y, px1 - 70, y + chh), radius=24, blur=18,
                       tint=(0, 0, 0, 120), edge=True)
        d = ImageDraw.Draw(img)
        for k, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            d.ellipse([148 + k * 32, y + 26, 168 + k * 32, y + 46], fill=c)
        ty = y + 70
        for ln in cl:
            d.text((148, ty), '$ ' + ln, font=_fr(36), fill=(245, 197, 24))
            ty += 56
    img.save(path)


def draw_end(jinju, question, path):
    img = _bg()
    d = _header(img)
    f_j, f_q = _fs(52), _fr(40)
    jl = _wrap2(d, _clean(jinju), f_j, W - 280)[:3]
    ql = _wrap2(d, _clean(question), f_q, W - 280)[:3]
    t = '收藏这篇，下次让 AI 做页面时翻出来'
    f_btn = _fs(38)
    _top_pad, _bot_pad = 120, 72
    ch = (_top_pad + len(jl) * 80 + 70 + len(ql) * 62 + 48 + 88 + _bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    py1 = py + ch
    img = _frosted(img, (px0, py, px1, py1), radius=40)
    d = ImageDraw.Draw(img)
    y = py + _top_pad
    for ln in jl:
        d.text((118, y), ln, font=f_j, fill=INK)
        y += 80
    y += 70
    for ln in ql:
        d.text((118, y), ln, font=f_q, fill=GRAY)
        y += 62
    y += 48
    tw = d.textlength(t, font=f_btn)
    d.rounded_rectangle([(W - tw) / 2 - 34, y, (W + tw) / 2 + 34, y + 88],
                        radius=44, fill=YELLOW)
    _ctext(d, W / 2, y + 44, t, f_btn, BROWN)
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
        print('苹果风+毛玻璃卡片已生成')
