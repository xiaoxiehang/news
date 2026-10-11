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
                # 英文单词不拆半：把整个单词挪到下一行（连字符视为单词内字符）
                if ch.isascii() and (ch.isalnum() or ch in '-_'):
                    i = len(cur)
                    while i > 0 and cur[i - 1].isascii() and (cur[i - 1].isalnum() or cur[i - 1] in '-_'):
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
    f_title, f_num, f_head, f_tip = xl.fs(xl.T_HERO), xl.fs(48), xl.fr(48), xl.fr(32)
    tl = xl.wrap2(d, big_title, f_title, W - 280)[:2]
    heads = [xl.wrap2(d, p['title'], f_head, W - 280 - 100)[:2] for p in picks[:3]]
    tip_ls = xl.wrap2(d, tip_text, f_tip, W - 280)[:2]
    top_pad, bot_pad = 90, 80
    ch = (top_pad + len(tl) * 170 + 40 + 10 + 60
          + sum(len(h) * 64 + 30 for h in heads)
          + 20 + len(tip_ls) * 44 + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=xl.INK)
        y += 170
    y += 40
    d.rectangle([118, y, 118 + 128, y + 10], fill=xl.YELLOW)
    y += 70
    for i, h in enumerate(heads):
        for j, ln in enumerate(h):
            if j == 0:
                d.text((118, y), str(i + 1), font=f_num, fill=xl.AMBER_D)
            d.text((198, y), ln, font=f_head, fill=xl.BODY)
            y += 64
        y += 30
    y += 20
    for ln in tip_ls:
        d.text((118, y), ln, font=f_tip, fill=xl.GRAY)
        y += 44
    xl.footer(ImageDraw.Draw(img), footer_text or '鸡仔 · AI早报')
    img.save(path)


def draw_card(pick, item, idx, total, path, footer_text=None):
    """v6: 项目卡样式 —— 标题 + 黄色圆点条目（摘要/你能怎么用/鸡仔点评）。"""
    from PIL import ImageDraw
    import xhs_light as xl
    img = xl.bg()
    d = xl.header(img, '鸡仔AI周报', '每周 AI 大事')
    f = xl.fr(34)
    t = '%02d / %02d' % (idx + 1, total)
    tw = d.textlength(t, font=f)
    d.text((W - 70 - tw, 112), t, font=f, fill=xl.MUTED)

    point = (item or {}).get('point', '').strip() or pick.get('summary', '')
    usage = (item or {}).get('usage', '').strip()
    comment = (item or {}).get('comment', '').strip()
    items = [(None, None, point)]
    if usage:
        items.append(('你能怎么用', xl.AMBER_D, usage))
    if comment:
        items.append(('鸡仔点评', xl.AMBER_D, comment))

    for tsize, bsize in [(60, 37), (56, 35), (52, 32)]:
        f_title, f_b, f_lab = xl.fs(tsize), xl.fr(bsize), xl.fs(32)
        tl = xl.wrap2(d, pick['title'], f_title, W - 280)[:2]
        bl = []
        for n, (label, lfill, text) in enumerate(items):
            lab_w = d.textlength(label + ' ', font=f_lab) if label else 0
            cap = 4 if n == 0 else 3
            lines = xl.wrap_first(d, text, f_b,
                                  W - 280 - 46 - lab_w, W - 280 - 46)[:cap]
            bl.append((label, lfill, lab_w, lines))
        tstep, bstep = tsize + 28, bsize + 29
        ch = (68 + len(tl) * tstep + 44
              + sum(len(x[3]) * bstep + 26 for x in bl) - 26 + 68)
        py = 150 + max(0, (H - 250 - ch) / 2)
        if py + ch <= H - 40:
            break

    img = xl.glass(img, (48, py, W - 48, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + 68
    for ln in tl:
        d.text((118, y), ln, font=f_title, fill=xl.INK)
        y += tstep
    y += 44
    for label, lfill, lab_w, lines in bl:
        for j, ln in enumerate(lines):
            if j == 0:
                d.ellipse([120, y + 16, 142, y + 38], fill=xl.YELLOW)
                if label:
                    d.text((166, y), label + ' ', font=f_lab, fill=lfill)
                d.text((166 + lab_w, y), ln, font=f_b, fill=xl.BODY)
            else:
                d.text((166, y), ln, font=f_b, fill=xl.BODY)
            y += bstep
        y += 26
    img.save(path)


def draw_end(jinju, question, path, fav_text='收藏这篇，持续更新', footer_text=None):
    """周报末页：浅色轻盈玻璃拟态（2026-10-11 全类型统一）。"""
    from PIL import ImageDraw
    import xhs_light as xl
    img = xl.bg()
    d = xl.header(img, '鸡仔AI早报', '')
    f_lab, f_j, f_q, f_btn = xl.fs(32), xl.fs(48), xl.fr(40), xl.fs(40)
    jl = xl.wrap2(d, jinju or '保持好奇，下周见。', f_j, W - 280)[:3]
    ql = xl.wrap2(d, question or '这周哪条 AI 新动态最让你意外？评论区聊聊。',
                  f_q, W - 280)[:3]
    top_pad, bot_pad = 100, 72
    ch = (top_pad + 52 + 30 + len(jl) * 64 + 50 + 10 + 60
          + len(ql) * 56 + 48 + 88 + bot_pad)
    px0, px1 = 48, W - 48
    py = 150 + max(0, (H - 250 - ch) / 2)
    img = xl.glass(img, (px0, py, px1, py + ch), radius=40)
    d = ImageDraw.Draw(img)
    y = py + top_pad
    d.text((118, y), '本周金句', font=f_lab, fill=xl.AMBER_D)
    y += 80
    for ln in jl:
        d.text((118, y), ln, font=f_j, fill=xl.INK)
        y += 64
    y += 50
    d.rectangle([118, y, 118 + 128, y + 10], fill=xl.YELLOW)
    y += 70
    for ln in ql:
        d.text((118, y), ln, font=f_q, fill=xl.GRAY)
        y += 56
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
