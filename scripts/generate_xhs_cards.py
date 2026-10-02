#!/usr/bin/env python3
"""小红书图文卡片：把当天早报渲染成 1080x1440（3:4）竖版图片。

读取 data/xhs/<YYYY-MM-DD>/picks.json（新闻数据）与 post.json（文案/点评），
输出到同一目录：
  cover.png        封面：今日AI早报 + 3 条头条（不放日期，做长尾流量）
  card_01..08.png  每条新闻一张卡片：编号 / 标题 / 摘要 / 一句话点评 / 来源
  end.png          末页：今日金句 + 互动提问 + 引导收藏

配色与网站视频卡片保持一致（深蓝底 + 黄色点缀）。
"""
import json
import os
from datetime import datetime

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SITE_DIR, 'data')
FONT_PATH = os.path.join(SITE_DIR, 'scripts', 'fonts', 'NotoSansSC-SemiBold.ttf')

W, H = 1080, 1440
C_BG_TOP = (15, 23, 42)
C_BG_BOTTOM = (30, 45, 80)
C_YELLOW = (255, 209, 102)
C_WHITE = (255, 255, 255)
C_GRAY = (203, 213, 225)
C_DIM = (100, 116, 139)
C_LINE = (51, 65, 85)
C_CARD = (24, 36, 66)

WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']
NUMERALS = ['01', '02', '03', '04', '05', '06', '07', '08']


def _font(size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT_PATH, size)


def _wrap(draw, text, font, max_w):
    """按像素宽度换行（中文逐字切分，英文单词不拆半，标点不单独成行）。"""
    # 行首禁则：这些标点不能出现在行首，收到上一行末尾
    NO_START = set('，。！？；：、」』）】”’%·…—')
    lines, cur = [], ''
    for ch in text:
        t = cur + ch
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                # 英文单词不拆半：把整个单词挪到下一行
                if ch.isascii() and ch.isalnum():
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
    # 标点挤回上一行
    fixed = []
    for ln in lines:
        if fixed and ln and ln[0] in NO_START:
            fixed[-1] += ln[0]
            ln = ln[1:]
        if ln:
            fixed.append(ln)
    return fixed or ['']


def _bg():
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(C_BG_TOP[i] + (C_BG_BOTTOM[i] - C_BG_TOP[i]) * t) for i in range(3)))
    d.rectangle([0, 0, W, 10], fill=C_YELLOW)
    return img, d


def _header(d, date_str):
    f1, f2 = _font(44), _font(36)
    d.text((70, 60), '鸡仔AI早报', font=f1, fill=C_YELLOW)
    d.text((70, 125), date_str, font=f2, fill=C_DIM)


def _footer(d, text='🐤 鸡仔 · 每天更新的AI早报'):
    # PIL 字体无 emoji，用文字替代
    f = _font(32)
    label = text.replace('🐤 ', '')
    tw = d.textlength(label, font=f)
    d.text(((W - tw) / 2, H - 110), label, font=f, fill=C_DIM)


def _clean(text):
    """去掉卡片字体不支持的 emoji / 特殊符号，避免渲染成方框。"""
    out = []
    for ch in text:
        o = ord(ch)
        if o > 0xFFFF:  # emoji 及其他增补平面字符
            continue
        if 0xFE00 <= o <= 0xFE0F or 0x1F000 <= o <= 0x1FAFF:
            continue
        out.append(ch)
    return ''.join(out).replace('👇', '').replace('📌', '').replace('💬', '')


def _centered(d, y, text, font, fill):
    tw = d.textlength(text, font=font)
    d.text(((W - tw) / 2, y), text, font=font, fill=fill)
    return y


def draw_cover(picks, path, big_title='今日AI早报', footer_text=None,
             tip_text='每天 3 分钟，跟上 AI 圈动态'):
    img, d = _bg()
    _header(d, '')  # 封面不放日期：去日期化有利于搜索长尾流量
    f_title = _font(110)
    _centered(d, 330, big_title, f_title, C_WHITE)
    # 黄色分隔线
    d.rectangle([(W - 120) / 2, 500, (W + 120) / 2, 510], fill=C_YELLOW)
    # 3 条头条
    f_num, f_head = _font(52), _font(46)
    y = 620
    for i, p in enumerate(picks[:3]):
        d.text((90, y), f'{i + 1}', font=f_num, fill=C_YELLOW)
        for ln in _wrap(d, _clean(p['title']), f_head, W - 260)[:2]:
            d.text((170, y), ln, font=f_head, fill=C_GRAY)
            y += 72
        y += 50
    f_tip = _font(38)
    _centered(d, y + 40, tip_text, f_tip, C_DIM)
    _footer(d, footer_text or '🐤 鸡仔 · 每天更新的AI早报')
    img.save(path)


def draw_card(pick, item, idx, total, path):
    img, d = _bg()
    from PIL import ImageDraw  # noqa
    _header(d, '')
    # 大编号
    f_idx, f_tot = _font(170), _font(60)
    num = NUMERALS[idx] if idx < len(NUMERALS) else f'{idx + 1:02d}'
    d.text((70, 200), num, font=f_idx, fill=C_YELLOW)
    tw = d.textlength(f'/ {total}', font=f_tot)
    d.text((70 + d.textlength(num, font=f_idx) + 20, 320), f'/ {total}', font=f_tot, fill=C_DIM)
    # 标题
    f_title = _font(62)
    y = 460
    for ln in _wrap(d, _clean(pick['title']), f_title, W - 140)[:3]:
        d.text((70, y), ln, font=f_title, fill=C_WHITE)
        y += 92
    d.rectangle([70, y + 10, W - 70, y + 13], fill=C_LINE)
    y += 70
    # 口语化介绍（代替公文腔摘要）
    point = (item or {}).get('point', '').strip() or pick.get('summary', '')
    f_sum = _font(40)
    for ln in _wrap(d, _clean(point), f_sum, W - 140)[:4]:
        if y > H - 560:
            break
        d.text((70, y), ln, font=f_sum, fill=C_GRAY)
        y += 66
    # "你能怎么用"高亮行
    usage = (item or {}).get('usage', '').strip()
    if usage and y < H - 460:
        f_use = _font(38)
        ulines = _wrap(d, _clean('你能怎么用：' + usage), f_use, W - 140)[:2]
        box_h = 36 + len(ulines) * 58
        if y + box_h < H - 330:
            d.rounded_rectangle([70, y + 10, W - 70, y + 10 + box_h], radius=16, fill=(58, 48, 12))
            d.rectangle([70, y + 10, 82, y + 10 + box_h], fill=C_YELLOW)
            uy = y + 28
            for ln in ulines:
                d.text((104, uy), ln, font=f_use, fill=C_YELLOW)
                uy += 58
            y += 10 + box_h + 10
    # 一句话点评（引用块，有空间才画）
    comment = (item or {}).get('comment', '').strip()
    if comment:
        f_cmt = _font(38)
        lines = _wrap(d, _clean(comment), f_cmt, W - 220)
        box_h = 40 + len(lines[:3]) * 62
        if y + box_h < H - 220:
            d.rounded_rectangle([70, y + 20, W - 70, y + 20 + box_h], radius=18, fill=C_CARD)
            d.rectangle([70, y + 20, 82, y + 20 + box_h], fill=C_YELLOW)
            cy = y + 42
            d.text((110, cy - 6), '鸡仔点评', font=_font(34), fill=C_YELLOW)
            cy += 52
            for ln in lines[:3]:
                d.text((110, cy), ln, font=f_cmt, fill=C_WHITE)
                cy += 62
            y += 20 + box_h
    _footer(d)
    img.save(path)


def draw_end(jinju, question, path, fav_text='收藏这篇，明早接着看', footer_text=None):
    img, d = _bg()
    f1 = _font(64)
    _centered(d, 420, '今日金句', f1, C_YELLOW)
    f_j = _font(52)
    y = 560
    for ln in _wrap(d, _clean(jinju) or '保持好奇，明天见。', f_j, W - 200)[:3]:
        _centered(d, y, ln, f_j, C_WHITE)
        y += 84
    d.rectangle([(W - 120) / 2, y + 30, (W + 120) / 2, y + 40], fill=C_YELLOW)
    f_q = _font(44)
    y += 120
    for ln in _wrap(d, _clean(question) or '今天哪条新闻最让你意外？评论区聊聊', f_q, W - 200)[:3]:
        _centered(d, y, ln, f_q, C_GRAY)
        y += 76
    f_fav = _font(40)
    _centered(d, y + 40, fav_text, f_fav, C_DIM)
    _footer(d, footer_text or '🐤 鸡仔 · 每天更新的AI早报')
    img.save(path)


def main():
    today = datetime.now().strftime('%Y-%m-%d')
    out_dir = os.path.join(DATA_DIR, 'xhs', today)
    picks_path = os.path.join(out_dir, 'picks.json')
    post_path = os.path.join(out_dir, 'post.json')
    if not os.path.exists(picks_path):
        print('❌ 缺少 picks.json，先跑 generate_xhs_post.py')
        return
    with open(picks_path, encoding='utf-8') as f:
        snap = json.load(f)
    post = {}
    if os.path.exists(post_path):
        with open(post_path, encoding='utf-8') as f:
            post = json.load(f)
    picks = snap['picks']
    items = post.get('items', [{}] * len(picks))

    try:
        from PIL import Image, ImageDraw, ImageFont  # noqa
    except ImportError:
        print('❌ 缺少 Pillow，请 pip install pillow')
        return

    draw_cover(picks, os.path.join(out_dir, 'cover.png'))
    total = len(picks)
    for i, p in enumerate(picks):
        draw_card(p, items[i] if i < len(items) else {}, i, total,
                  os.path.join(out_dir, f'card_{i + 1:02d}.png'))
    draw_end(post.get('jinju', ''), post.get('question', ''),
             os.path.join(out_dir, 'end.png'))
    print(f'✅ 小红书卡片已生成 ({total + 2} 张) -> {out_dir}/')
    print('   cover.png + ' + ' '.join(f'card_{i + 1:02d}.png' for i in range(total)) + ' + end.png')

    # 更新发布包索引（供 xhs.html 日期切换）
    xhs_root = os.path.join(DATA_DIR, 'xhs')
    index = []
    for d in sorted(os.listdir(xhs_root), reverse=True):
        pp = os.path.join(xhs_root, d, 'post.json')
        if not os.path.isfile(pp):
            continue
        try:
            with open(pp, encoding='utf-8') as f:
                pj = json.load(f)
            index.append({'date': d, 'title': pj.get('title', ''),
                          'fallback': bool(pj.get('fallback'))})
        except Exception:
            continue
    with open(os.path.join(xhs_root, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f'✅ 发布包索引已更新: {len(index)} 期')


if __name__ == '__main__':
    main()
