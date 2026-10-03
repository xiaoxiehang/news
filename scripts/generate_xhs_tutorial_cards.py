#!/usr/bin/env python3
"""小红书教程类卡片生成器 v2：对话实录风。

设计语言：暖纸白底 + 聊天界面 mockup。
每张卡讲一个 mini 故事：你发出什么 → AI 回复什么 → 避坑一句。
与深色 AI 早报模板彻底区分。
"""
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
USER_BUBBLE = (255, 243, 196)
AI_BUBBLE = (255, 255, 255)
AI_BORDER = (228, 224, 214)
WARN_BG = (253, 236, 234)
WARN_INK = (170, 44, 38)
PANEL = (244, 240, 232)


def _new():
    img = Image.new('RGB', (W, H), BG)
    return img, ImageDraw.Draw(img)


def _pill(d, x, y, text):
    f = _font(34)
    tw = d.textlength(text, font=f)
    d.rounded_rectangle([x, y, x + tw + 56, y + 58], radius=29, fill=YELLOW)
    d.text((x + 28, y + 12), text, font=f, fill=BROWN)


def _header(d, idx, total):
    _pill(d, 70, 56, '鸡仔AI实战')
    f = _font(36)
    t = f'{idx + 1:02d} / {total:02d}'
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 68), t, font=f, fill=DIM)


def _avatar(d, cx, cy, r, text, fill, ink):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    f = _font(30)
    tw = d.textlength(text, font=f)
    d.text((cx - tw / 2, cy - 23), text, font=f, fill=ink)


def _measure(d, max_w, text):
    """纯测量，不绘制。返回 (气泡宽, 气泡高, 行列表)。"""
    f = _font(36)
    lines = _wrap(d, _clean(text), f, max_w - 52)
    lw = max(d.textlength(ln, font=f) for ln in lines) if lines else 0
    bw = min(max_w, lw + 52)
    bh = 30 + len(lines) * 54 + 26
    return bw, bh, lines


def _bubble(d, x, y, max_w, text, fill, ink, border=None):
    """画一个聊天气泡，返回实际高度。"""
    f = _font(36)
    bw, bh, lines = _measure(d, max_w, text)
    if border:
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=26,
                            fill=fill, outline=border, width=2)
    else:
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=26, fill=fill)
    ty = y + 26
    for ln in lines:
        d.text((x + 26, ty), ln, font=f, fill=ink)
        ty += 54
    return bw, bh


def draw_cover_tutorial(kicker, title_lines, tips, path):
    img, d = _new()
    _pill(d, 70, 56, '鸡仔AI实战')
    y = 290
    f_kick = _font(46)
    d.text((72, y), kicker, font=f_kick, fill=YELLOW_D)
    y += 100
    f_big = _font(100)
    for ln in title_lines:
        d.text((66, y), ln, font=f_big, fill=INK)
        y += 128
    y += 60
    d.rectangle([72, y, 200, y + 10], fill=YELLOW)
    y += 70
    f_n, f_t = _font(44), _font(42)
    for i, tip in enumerate(tips):
        cy = y + 32
        d.ellipse([78, cy - 32, 142, cy + 32], fill=YELLOW)
        n = str(i + 1)
        nw = d.textlength(n, font=f_n)
        d.text((110 - nw / 2, cy - 32), n, font=f_n, fill=BROWN)
        for ln in _wrap(d, _clean(tip), f_t, W - 300)[:2]:
            d.text((172, y), ln, font=f_t, fill=INK)
            y += 62
        y += 48
    img.save(path)


def draw_tip_card(tip, idx, total, path):
    """tip: {title, scene, user, ai, warn}"""
    img, d = _new()
    _header(d, idx, total)
    y = 180
    f_title = _font(68)
    for ln in _wrap(d, _clean(tip['title']), f_title, W - 140)[:2]:
        d.text((70, y), ln, font=f_title, fill=INK)
        y += 92
    y += 10
    # 场景（小灰字）
    f_scene = _font(34)
    for ln in _wrap(d, _clean(tip['scene']), f_scene, W - 140)[:2]:
        d.text((70, y), ln, font=f_scene, fill=GRAY)
        y += 52
    y += 26
    # 聊天面板：先预量高度，画面板，再画内容
    px0, px1 = 70, W - 70
    max_w = px1 - px0 - 190
    panel_top = y
    # 预量两行高度
    _, uh, _ = _measure(d, max_w, tip['user'])
    _, ah, _ = _measure(d, max_w, tip['ai'])
    panel_h = 36 + uh + 30 + ah + 36
    d.rounded_rectangle([px0, panel_top, px1, panel_top + panel_h],
                        radius=28, fill=PANEL)
    y = panel_top + 36
    bw, _, _ = _measure(d, max_w, tip['user'])
    bx = px1 - bw - 96
    _bubble(d, bx, y, max_w, tip['user'], USER_BUBBLE, INK)
    _avatar(d, px1 - 42, y + 42, 34, '你', YELLOW, BROWN)
    y += uh + 30
    _avatar(d, px0 + 42, y + 42, 34, 'AI', INK, WHITE)
    _bubble(d, px0 + 96, y, max_w, tip['ai'], AI_BUBBLE, INK, border=AI_BORDER)
    y = panel_top + panel_h + 30
    # 避坑条
    f_w = _font(36)
    wt = '避坑：' + tip['warn']
    wl = _wrap(d, _clean(wt), f_w, W - 140 - 52)
    wh = 28 + len(wl) * 54 + 24
    d.rounded_rectangle([70, y, W - 70, y + wh], radius=20, fill=WARN_BG)
    ty = y + 24
    for i, ln in enumerate(wl):
        d.text((104, ty), ln, font=f_w,
               fill=WARN_INK if i == 0 else INK)
        ty += 54
    img.save(path)


def draw_end_tutorial(jinju, question, path):
    img, d = _new()
    _pill(d, 70, 56, '鸡仔AI实战')
    y = 420
    f_j = _font(56)
    for ln in _wrap(d, _clean(jinju), f_j, W - 140)[:3]:
        d.text((70, y), ln, font=f_j, fill=INK)
        y += 84
    y += 60
    d.rectangle([72, y, 200, y + 10], fill=YELLOW)
    y += 70
    f_q = _font(42)
    for ln in _wrap(d, _clean(question), f_q, W - 140)[:3]:
        d.text((70, y), ln, font=f_q, fill=GRAY)
        y += 66
    y += 40
    f_fav = _font(40)
    t = '收藏这篇，下周做报表时翻出来对照着用'
    tw = d.textlength(t, font=f_fav)
    d.rounded_rectangle([(W - tw) / 2 - 30, y, (W + tw) / 2 + 30, y + 84],
                        radius=42, fill=YELLOW)
    d.text(((W - tw) / 2, y + 20), t, font=f_fav, fill=BROWN)
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


if __name__ == '__main__':
    d = 'data/xhs-drafts/2026-10-04'
    draw_cover_tutorial('打工人必看', ['3个AI技巧', '报表1小时变10分钟'],
                        [t['title'] for t in TIPS], f'{d}/cover.png')
    for i, t in enumerate(TIPS):
        draw_tip_card(t, i, len(TIPS), f'{d}/card_{i + 1:02d}.png')
    draw_end_tutorial('AI 搭架子，你填里子，这个分工最稳。',
                      '这 3 招里，你最想先试哪一个？评论区扣 1，提示词原文发你。',
                      f'{d}/end.png')
    print('对话实录风卡片已生成')
