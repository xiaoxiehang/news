#!/usr/bin/env python3
"""小红书卡片共享视觉：深色苹果风 + 毛玻璃（与此前已发布的开源项目卡一模一样）。

深色渐变底 + 柔光色块 + 深色毛玻璃面板（模糊背景 + 半透明白 + 白描边）
+ 黄色点缀。2026-10-11 用户拍板：退回深色原版，三类卡片全部统一。
各内容类型（开源项目 / AI 实战教程 / 每周盘点）共用这套视觉语言，
只换 kicker 文案与内容结构。
"""
import os

from generate_xhs_cards import _wrap, _clean, W, H
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE = os.path.dirname(os.path.abspath(__file__))
FONT_SEMI = os.path.join(BASE, 'fonts', 'NotoSansSC-SemiBold.ttf')
FONT_REG = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'


def fs(size):
    return ImageFont.truetype(FONT_SEMI, size)


def fr(size):
    # 常规字重：优先系统 NotoSansCJK（本机），CI 等无系统字体的环境
    # 回退到仓库自带的 SemiBold，保证任何机器都能跑
    for _p, _kw in ((FONT_REG, {'index': 2}), (FONT_REG, {}),
                    (FONT_SEMI, {})):
        try:
            return ImageFont.truetype(_p, size, **_kw)
        except Exception:
            continue
    return ImageFont.truetype(FONT_SEMI, size)


PUNCT = set('，。！？；：、）】”’')

# 统一字阶（全类型共用，一卡内不超过 4 档）
T_DISPLAY = 92   # 封面主标题（与原版项目卡一致）
T_TITLE = 72     # 内容卡标题 / 大数字
T_LEAD = 48      # 封面副标题 / 引言
T_BODY = 40      # 正文 / 气泡 / 注解正文
T_SMALL = 32     # 标签 / 场景 / 次要说明
T_META = 28      # 页眉页脚 / 计数

# 深色苹果风配色（与原版项目卡逐参数一致）
INK = (245, 245, 247)
BODY = (214, 214, 218)
GRAY = (161, 161, 166)
MUTED = (120, 120, 128)
YELLOW = (245, 197, 24)
YELLOW_D = (150, 110, 5)
BROWN = (70, 50, 5)
WHITE = (255, 255, 255)
CODE_BG = (30, 30, 40)
CODE_INK = (255, 214, 120)


def wrap2(d, text, font, max_w, min_last=4):
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


def bg():
    """深色渐变底 + 柔光色块（与原版项目卡一致）"""
    img = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(img)
    top, bot = (14, 14, 18), (30, 30, 38)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))
    blob = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob)
    bd.ellipse([-220, -160, 620, 560], fill=(90, 90, 200, 55))       # 靛蓝
    bd.ellipse([560, 900, 1300, 1600], fill=(200, 150, 60, 40))      # 暗金
    bd.ellipse([-260, 780, 420, 1380], fill=(60, 120, 200, 40))      # 深蓝
    blob = blob.filter(ImageFilter.GaussianBlur(130))
    img = Image.alpha_composite(img.convert('RGBA'), blob).convert('RGB')
    return img


def glass(img, box, radius=36, shadow=True, blur=24,
            tint=(255, 255, 255, 22), edge=True):
    """深色毛玻璃面板：模糊背景 + 半透明白 + 白描边（与原版 _frosted 一致）。"""
    x0, y0, x1, y1 = [int(v) for v in box]
    crop = img.crop((x0, y0, x1, y1))
    pane = crop.filter(ImageFilter.GaussianBlur(blur)).convert('RGBA')
    pane = Image.alpha_composite(
        pane, Image.new('RGBA', pane.size, tint))
    mask = Image.new('L', pane.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, pane.size[0], pane.size[1]], radius=radius, fill=255)
    img.paste(pane, (x0, y0), mask)
    if edge:
        ImageDraw.Draw(img, 'RGBA').rounded_rectangle(
            [x0, y0, x1, y1], radius=radius,
            outline=(255, 255, 255, 45), width=2)
    return img


def _isword(ch):
    return ch.isascii() and (ch.isalnum() or ch in '-_')


def wrap_first(d, text, font, w1, w_rest):
    """首行宽 w1、其余行宽 w_rest 的按字换行（用于行内标签条目）。
    英文单词（含连字符）不拆半。"""
    lines, cur, first = [], '', True
    for ch in text:
        w = w1 if first else w_rest
        t = cur + ch
        if d.textlength(t, font=font) <= w:
            cur = t
            continue
        if cur and _isword(ch):
            i = len(cur)
            while i > 0 and _isword(cur[i - 1]):
                i -= 1
            if 0 < i < len(cur):
                lines.append(cur[:i])
                cur, first = cur[i:] + ch, False
                continue
        if cur:
            lines.append(cur)
        cur, first = ch, False
    if cur:
        lines.append(cur)
    return lines


def ctext(d, cx, cy, text, font, fill):
    """以文字墨迹中心为锚点绘制（真正的视觉居中）"""
    b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2),
           text, font=font, fill=fill)


def pill(d, x, y, text):
    """黄色 kicker 胶囊"""
    f = fs(32)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 52, y + 54], radius=27, fill=YELLOW)
    ctext(d, x + 26 + tw / 2, y + 27, text, f, BROWN)


def header(img, kicker, right_text=''):
    """顶部：左 kicker 胶囊 + 右说明文字。返回 ImageDraw。"""
    d = ImageDraw.Draw(img)
    pill(d, 70, 56, kicker)
    if right_text:
        f = fr(34)
        tw = d.textlength(right_text, font=f)
        d.text((W - 70 - tw, 68), right_text, font=f, fill=MUTED)
    return d


def footer(d, text):
    """底部居中浅灰文字。"""
    f = fr(32)
    t = _clean(text)
    tw = d.textlength(t, font=f)
    d.text(((W - tw) / 2, H - 110), t, font=f, fill=MUTED)


def avatar(d, cx, cy, text, fill, ink, r=34):
    """圆形头像徽章"""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    f = fs(30 if len(text) <= 1 else 28)
    ctext(d, cx, cy, text, f, ink)
