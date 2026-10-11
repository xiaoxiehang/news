#!/usr/bin/env python3
"""小红书卡片共享浅色视觉：参考风轻盈玻璃拟态（2026-10-11 用户定稿，全类型统一）。

平涂浅灰底 #F0F0F0（无彩色光斑）+ 卡片自带极淡冷色渐变 tint
+ 克制阴影 + 白描边 + 黄色品牌点缀。
参考：Grey黎《原创-Figma玻璃质感人物卡片教程》（笔记ID 6ac64e6d000000001203bac2）。
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
    try:
        return ImageFont.truetype(FONT_REG, size, index=2)
    except Exception:
        return ImageFont.truetype(FONT_REG, size)


PUNCT = set('，。！？；：、）】”’')

# 统一字阶（全类型共用，一卡内不超过 4 档）
T_HERO = 132     # 封面超大标题（对标教程：占画面上三分之一）
T_DISPLAY = 96   # 封面主标题
T_TITLE = 72     # 内容卡标题 / 大数字
T_LEAD = 48      # 封面副标题 / 引言
T_BODY = 40      # 正文 / 气泡 / 注解正文
T_SMALL = 32     # 标签 / 场景 / 次要说明
T_META = 28      # 页眉页脚 / 计数

# 浅色玻璃拟态配色
INK = (28, 28, 34)
BODY = (62, 62, 72)
GRAY = (110, 112, 125)
MUTED = (152, 154, 170)
YELLOW = (245, 197, 24)
BROWN = (70, 50, 5)
AMBER_D = (170, 115, 0)      # 浅底上的深金色小字
WHITE = (255, 255, 255)
USER_BUBBLE = (255, 243, 196)
USER_EDGE = (235, 220, 170)
AI_BUBBLE = (255, 255, 255)
AI_EDGE = (226, 230, 242)
WARN_BG = (255, 244, 232)
WARN_EDGE = (238, 214, 178)
WARN_TITLE = (170, 60, 30)
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
    """参考风：平涂浅灰 #F0F0F0，无彩色光斑（Grey黎教程原做法）"""
    return Image.new('RGB', (W, H), (240, 240, 240))


def glass(img, box, radius=36, shadow=True):
    """悬浮玻璃面板：克制阴影 + 卡片自带极淡冷色渐变 tint + 白描边 + 顶部高光
    （参考 Grey黎教程：阴影 X0/Y20/模糊40/透明度~5%，卡片 #E6E6E6→#A7E9F0 的轻量版）"""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    if shadow:
        sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [x0, y0 + 20, x1, y1 + 20], radius=radius, fill=(31, 104, 126, 28))
        sh = sh.filter(ImageFilter.GaussianBlur(42))
        img = Image.alpha_composite(img.convert('RGBA'), sh).convert('RGB')
    crop = img.crop((x0, y0, x1, y1))
    pane = crop.filter(ImageFilter.GaussianBlur(26)).convert('RGBA')
    tint = Image.new('RGBA', pane.size)
    td = ImageDraw.Draw(tint)
    for yy in range(h):
        t = yy / max(1, h - 1)
        td.line([(0, yy), (w, yy)],
                fill=(int(238 - 6 * t), int(241 - 5 * t), int(252 - 3 * t), 120))
    pane = Image.alpha_composite(pane, tint)
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    img.paste(pane, (x0, y0), mask)
    ImageDraw.Draw(img, 'RGBA').rounded_rectangle(
        [x0, y0, x1, y1], radius=radius, outline=(255, 255, 255, 130), width=2)
    ImageDraw.Draw(img, 'RGBA').line(
        [(x0 + 60, y0 + 2), (x1 - 60, y0 + 2)],
        fill=(255, 255, 255, 90), width=3)
    return img


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
