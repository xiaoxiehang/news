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


def _footer(d, text='🐤 鸡仔 · AI早报'):
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
    """周报封面：浅色轻盈玻璃拟态（2026-10-11 全类型统一）。"""
    from PIL import ImageDraw
    import xhs_light as xl
    img = xl.bg()
    d = xl.header(img, '鸡仔AI早报', '')
    f_title, f_num, f_head, f_tip = xl.fs(110), xl.fs(52), xl.fr(46), xl.fr(38)
    tl = xl.wrap2(d, big_title, f_title, W - 280)[:2]
    heads = [xl.wrap2(d, p['title'], f_head, W - 280 - 100)[:2] for p in picks[:3]]
    tip_ls = xl.wrap2(d, tip_text, f_tip, W - 280)[:2]
    top_pad, bot_pad = 90, 80
    ch = (top_pad + len(tl) * 140 + 40 + 10 + 60
          + sum(len(h) * 72 + 30 for h in heads)
          + 20 + len(tip_ls) * 58 + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=xl.INK)
        y += 140
    y += 40
    d.rectangle([118, y, 118 + 128, y + 10], fill=xl.YELLOW)
    y += 70
    for i, h in enumerate(heads):
        for j, ln in enumerate(h):
            if j == 0:
                d.text((118, y), str(i + 1), font=f_num, fill=xl.AMBER_D)
            d.text((198, y), ln, font=f_head, fill=xl.BODY)
            y += 72
        y += 30
    y += 20
    for ln in tip_ls:
        d.text((118, y), ln, font=f_tip, fill=xl.GRAY)
        y += 58
    xl.footer(ImageDraw.Draw(img), footer_text or '鸡仔 · AI早报')
    img.save(path)


def draw_card(pick, item, idx, total, path):
    """周报内容卡：浅色轻盈玻璃拟态（2026-10-11 全类型统一）。"""
    from PIL import ImageDraw
    import xhs_light as xl
    img = xl.bg()
    d = xl.header(img, '鸡仔AI早报', '%02d / %02d' % (idx + 1, total))
    f_num, f_num2 = xl.fs(72), xl.fr(40)
    f_title, f_sum, f_use = xl.fs(60), xl.fr(40), xl.fr(38)
    tl = xl.wrap2(d, pick['title'], f_title, W - 280)[:3]
    point = (item or {}).get('point', '').strip() or pick.get('summary', '')
    pl = xl.wrap2(d, point, f_sum, W - 280)[:4]
    usage = (item or {}).get('usage', '').strip()
    ul = xl.wrap2(d, '你能怎么用：' + usage, f_use, W - 280 - 60)[:2] if usage else []
    comment = (item or {}).get('comment', '').strip()
    cl = xl.wrap2(d, comment, f_use, W - 280 - 100)[:3] if comment else []

    def _ch():
        uh = (36 + len(ul) * 58 + 32) if ul else 0
        chh = (36 + 52 + len(cl) * 60 + 32) if cl else 0
        return (64 + 100 + 24 + len(tl) * 88 + 30 + 8 + 30
                + len(pl) * 62 + 28
                + (uh + 22 if ul else 0) + (chh + 22 if cl else 0) + 64)

    while cl and _ch() > H - 320:
        cl = cl[:-1]
    while ul and _ch() > H - 320:
        ul = ul[:-1]
    while len(pl) > 2 and _ch() > H - 320:
        pl = pl[:-1]
    ch = _ch()
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + 64
    num = '%02d' % (idx + 1)
    d.text((118, y), num, font=f_num, fill=xl.AMBER_D)
    nw = d.textlength(num, font=f_num)
    d.text((118 + nw + 16, y + 34), '/ %02d' % total, font=f_num2, fill=xl.MUTED)
    y += 124
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=xl.INK)
        y += 88
    y += 30
    d.rectangle([118, y, px1 - 70, y + 8], fill=(214, 216, 228))
    y += 38
    for ln in pl:
        d.text((118, y), ln, font=f_sum, fill=xl.BODY)
        y += 62
    y += 28
    if ul:
        uh = 36 + len(ul) * 58 + 32
        d.rounded_rectangle([118, y, px1 - 70, y + uh], radius=18,
                            fill=xl.USER_BUBBLE, outline=xl.USER_EDGE, width=2)
        d.rectangle([118, y + 16, 128, y + uh - 16], fill=xl.YELLOW)
        uy = y + 36
        for ln in ul:
            d.text((152, uy), ln, font=f_use, fill=(120, 85, 0))
            uy += 58
        y += uh + 22
    if cl:
        chh = 36 + 52 + len(cl) * 60 + 32
        d.rounded_rectangle([118, y, px1 - 70, y + chh], radius=18,
                            fill=xl.AI_BUBBLE, outline=xl.AI_EDGE, width=2)
        d.rectangle([118, y + 16, 128, y + chh - 16], fill=xl.YELLOW)
        cy = y + 36
        d.text((152, cy), '鸡仔点评', font=xl.fs(34), fill=xl.AMBER_D)
        cy += 52
        for ln in cl:
            d.text((152, cy), ln, font=f_use, fill=xl.INK)
            cy += 60
        y += chh + 22
    xl.footer(ImageDraw.Draw(img), '鸡仔 · AI早报')
    img.save(path)


def draw_end(jinju, question, path, fav_text='收藏这篇，持续更新', footer_text=None):
    """周报末页：浅色轻盈玻璃拟态（2026-10-11 全类型统一）。"""
    from PIL import ImageDraw
    import xhs_light as xl
    img = xl.bg()
    d = xl.header(img, '鸡仔AI早报', '')
    f_lab, f_j, f_q, f_btn = xl.fs(40), xl.fs(56), xl.fr(42), xl.fs(38)
    jl = xl.wrap2(d, jinju or '保持好奇，下周见。', f_j, W - 280)[:3]
    ql = xl.wrap2(d, question or '这周哪条 AI 新动态最让你意外？评论区聊聊。',
                  f_q, W - 280)[:3]
    top_pad, bot_pad = 100, 72
    ch = (top_pad + 60 + 30 + len(jl) * 84 + 50 + 10 + 60
          + len(ql) * 66 + 48 + 88 + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    d.text((118, y), '本周金句', font=f_lab, fill=xl.AMBER_D)
    y += 90
    for ln in jl:
        d.text((118, y), ln, font=f_j, fill=xl.INK)
        y += 84
    y += 50
    d.rectangle([118, y, 118 + 128, y + 10], fill=xl.YELLOW)
    y += 70
    for ln in ql:
        d.text((118, y), ln, font=f_q, fill=xl.GRAY)
        y += 66
    y += 48
    tw = d.textlength(fav_text, font=f_btn)
    d.rounded_rectangle([(W - tw) / 2 - 34, y, (W + tw) / 2 + 34, y + 88],
                        radius=44, fill=xl.YELLOW)
    xl.ctext(d, W / 2, y + 44, fav_text, f_btn, xl.BROWN)
    xl.footer(ImageDraw.Draw(img), footer_text or '鸡仔 · AI早报')
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
