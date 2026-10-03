#!/usr/bin/env python3
"""小红书教程类卡片生成器：浅色实战风，与深色 AI 早报模板彻底区分。

设计语言：暖纸白底 + 黑色大标题 + 黄色品牌点缀。
结构：场景(灰盒) → 做法(白卡) → 提示词(可复制黄条) → 避坑(浅红盒)。
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
SCENE_BG = (238, 235, 228)
WARN_BG = (253, 236, 234)
WARN_INK = (170, 44, 38)
PROMPT_BG = (255, 248, 220)
BROWN = (70, 50, 5)


def _bg():
    return Image.new('RGB', (W, H), BG), None


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


def _footer(d):
    pass  # 2026-10-03 用户要求去掉底部品牌行，顶部徽章已足够


def _box(d, y, label, text, bg, ink, label_color, left_bar=None):
    """圆角内容盒，返回底部 y。"""
    f_lab, f_txt = _font(34), _font(38)
    lines = _wrap(d, _clean(text), f_txt, W - 140 - 64)
    box_h = 30 + 52 + len(lines) * 58 + 26
    d.rounded_rectangle([70, y, W - 70, y + box_h], radius=20, fill=bg)
    if left_bar:
        d.rectangle([70, y + 14, 80, y + box_h - 14], fill=left_bar)
    d.text((104, y + 26), label, font=f_lab, fill=label_color)
    ty = y + 26 + 56
    for ln in lines:
        d.text((104, ty), ln, font=f_txt, fill=ink)
        ty += 58
    return y + box_h + 26


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
        y += 148
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
    _footer(d)
    img.save(path)


def draw_tip_card(tip, idx, total, path):
    img, d = _new()
    _header(d, idx, total)
    y = 180
    f_title = _font(68)
    for ln in _wrap(d, _clean(tip['title']), f_title, W - 140)[:2]:
        d.text((70, y), ln, font=f_title, fill=INK)
        y += 92
    y += 18
    y = _box(d, y, '场景', tip['scene'], SCENE_BG, INK, GRAY)
    y = _box(d, y, '做法', tip['how'], WHITE, INK, YELLOW_D, left_bar=YELLOW)
    if tip.get('prompt'):
        y = _box(d, y, '提示词复制', tip['prompt'], PROMPT_BG, INK, YELLOW_D)
    y = _box(d, y, '避坑', tip['warn'], WARN_BG, WARN_INK, WARN_INK)
    _footer(d)
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
    _footer(d)
    img.save(path)


if __name__ == '__main__':
    import json
    d = 'data/xhs-drafts/2026-10-04'
    draft = json.load(open(f'{d}/draft.json', encoding='utf-8'))
    tips = [
        {"title": "把 Excel 丢给 AI 洗",
         "scene": "电商运营，每月初从后台导 3000 行订单明细，老板要各品类销售额+退货率汇总表。以前拉透视表，1 小时起步。",
         "how": "把数据复制进对话框，第一句说清列含义和想要的输出。现在 30 秒出表。",
         "prompt": "这是9月订单明细，A列下单日期、B列商品类目、C列金额、D列是否退货，按类目汇总销售额和退货率，输出一张表。",
         "warn": "关键数字自己抽查两行，公式它偶尔手滑。"},
        {"title": "周报 5 分钟交差",
         "scene": "周五下午 5 点，周报还没动笔。",
         "how": "先列 5 条大白话，越碎越好，再让 AI 扩写成正式周报。",
         "prompt": "周一跟进 3 个客户，A 公司签了 2 万的单；周三写完 Q4 推广方案初稿……扩写成正式周报，语气低调务实。",
         "warn": "数字结论自己填，别让它编业绩。"},
        {"title": "汇报 PPT 10 分钟出大纲",
         "scene": "下周给总监汇报 Q4 推广方案，只有 15 分钟。",
         "how": "告诉 AI 听众是谁、讲多久、想让对方记住哪句话，拿它给的大纲再填自己的案例。",
         "prompt": "听众是总监，关心投入产出；讲 15 分钟；想让他记住：Q4 主攻短视频，预算 20 万，目标 200 万 GMV。",
         "warn": "大纲是骨架，血肉必须是你的真实业务，套模板一问就穿帮。"},
    ]
    draw_cover_tutorial('打工人必看', ['3个AI技巧', '报表1小时变10分钟'],
                        [t['title'] for t in tips], f'{d}/cover.png')
    for i, t in enumerate(tips):
        draw_tip_card(t, i, len(tips), f'{d}/card_{i + 1:02d}.png')
    draw_end_tutorial('AI 搭架子，你填里子，这个分工最稳。',
                      '这 3 招里，你最想先试哪一个？评论区扣 1，提示词原文发你。',
                      f'{d}/end.png')
    print('实战风卡片已生成')
