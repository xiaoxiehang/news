#!/usr/bin/env python3
"""把 data/briefing.json 转成竖屏短视频（1080x1920，带字幕）。

流程：
  1. 口播稿按「开场 + 每条新闻 + 结尾」分段
  2. 每段单独 edge-tts 合成（带词级时间戳）
  3. 每段用 PIL 生成一张内容卡片（编号/标题/摘要/来源），音频多长卡片播多长
  4. 分段拼成完整视频，再烧录全局字幕

输出：
  data/video/YYYY-MM-DD.mp4   当期视频
  data/video/index.json        视频列表（倒序，只保留最近 7 期）

没有 briefing.json 或任一步骤失败时静默跳过，不影响流水线。
需要 ffmpeg（含 libass）、edge-tts、Pillow，中文字体用仓库自带的
scripts/fonts/NotoSansSC-SemiBold.ttf。
"""
import asyncio
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

SITE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(SITE_DIR, 'data')
VIDEO_DIR = os.path.join(DATA_DIR, 'video')
FONT_PATH = os.path.join(SITE_DIR, 'scripts', 'fonts', 'NotoSansSC-SemiBold.ttf')
COVER_PATH = os.path.join(SITE_DIR, 'podcast-cover.png')

VOICE = 'zh-CN-XiaoxiaoNeural'
HOST_NAME = '鸡仔'
KEEP_VIDEOS = 7
WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']

# ---- 卡片配色 ----
W, H = 1080, 1920
C_BG_TOP = (15, 23, 42)
C_BG_BOTTOM = (30, 45, 80)
C_YELLOW = (255, 209, 102)
C_WHITE = (255, 255, 255)
C_GRAY = (203, 213, 225)
C_DIM = (100, 116, 139)
C_LINE = (51, 65, 85)


def ensure_edge_tts():
    try:
        import edge_tts  # noqa
        return True
    except ImportError:
        print('  正在安装 edge-tts...')
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'edge-tts'])
            return True
        except Exception as e:
            print(f'  ❌ edge-tts 安装失败: {e}')
            return False


def ensure_pillow():
    try:
        import PIL  # noqa
        return True
    except ImportError:
        print('  正在安装 Pillow...')
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'Pillow'])
            return True
        except Exception as e:
            print(f'  ❌ Pillow 安装失败: {e}')
            return False


def build_parts(briefing):
    """把早报拆成口播分段：intro / pickN / outro，每段带卡片信息。"""
    today = briefing.get('date', datetime.now().strftime('%Y-%m-%d'))
    dt = datetime.strptime(today, '%Y-%m-%d')
    date_str = briefing.get('date_str') or dt.strftime('%Y年%m月%d日')
    weekday = WEEKDAYS[dt.weekday()]
    picks = briefing.get('picks', [])
    cn = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

    parts = []
    intro = f'大家好，我是{HOST_NAME}，欢迎收听今日科技早报。今天是{date_str}，星期{weekday}。'
    if briefing.get('overview'):
        intro += f'先来听听今天的大局：{briefing["overview"]}'
    intro += f'接下来是今天的{len(picks)}条必读。'
    parts.append({'key': 'intro', 'narr': intro, 'kind': 'intro',
                  'date_str': date_str, 'weekday': weekday, 'count': len(picks)})

    for i, p in enumerate(picks, 1):
        num = cn[i - 1] if i <= 10 else str(i)
        narr = f'第{num}条，{p.get("title", "")}。'
        if p.get('summary'):
            narr += p['summary']
        parts.append({'key': f'pick{i}', 'narr': narr, 'kind': 'pick',
                      'index': i, 'total': len(picks),
                      'title': p.get('title', ''), 'summary': p.get('summary', ''),
                      'source': p.get('source') or '科技早报',
                      'date_str': date_str})

    outro = f'以上就是今天的科技早报，我是{HOST_NAME}，我们明天早上八点再见。'
    parts.append({'key': 'outro', 'narr': outro, 'kind': 'outro'})
    return parts


async def synthesize_part(text, mp3_path):
    """合成一段音频，返回词级字幕 [(start_ms, end_ms, text)]（相对本段）"""
    import edge_tts
    try:
        communicate = edge_tts.Communicate(text, VOICE, boundary='WordBoundary')
    except TypeError:
        communicate = edge_tts.Communicate(text, VOICE)
    subs = []
    with open(mp3_path, 'wb') as f:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                f.write(chunk['data'])
            elif chunk['type'] in ('WordBoundary', 'SentenceBoundary'):
                subs.append((chunk['offset'] // 10000,
                             (chunk['offset'] + chunk['duration']) // 10000,
                             chunk['text']))
    return subs


def get_audio_duration_ms(mp3_path):
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', mp3_path],
            capture_output=True, text=True, timeout=30)
        return int(float(r.stdout.strip()) * 1000)
    except Exception:
        return 0


def proportional_subs(script, duration_ms):
    import re
    sentences = [s for s in re.split(r'(?<=[，。！？；：])', script) if s.strip()]
    if not sentences or not duration_ms:
        return []
    total_chars = sum(len(s) for s in sentences)
    subs, cursor = [], 0
    for s in sentences:
        end = cursor + int(duration_ms * len(s) / total_chars)
        subs.append((cursor, end, s.strip()))
        cursor = end
    return subs


# ================= 卡片绘制 =================

def _font(size):
    from PIL import ImageFont
    return ImageFont.truetype(FONT_PATH, size)


def _wrap(draw, text, font, max_w):
    """按像素宽度贪心换行（中文按字切）"""
    lines, line = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(line)
            line = ''
            continue
        t = line + ch
        if draw.textlength(t, font=font) <= max_w:
            line = t
        else:
            if line:
                lines.append(line)
            line = ch
    if line:
        lines.append(line)
    return lines


def _bg():
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)],
               fill=tuple(int(C_BG_TOP[i] + (C_BG_BOTTOM[i] - C_BG_TOP[i]) * t) for i in range(3)))
    # 顶部品牌黄线
    d.rectangle([0, 0, W, 10], fill=C_YELLOW)
    return img, d


def _header(d, date_str):
    f1, f2 = _font(44), _font(36)
    d.text((70, 80), '鸡仔科技早报', font=f1, fill=C_YELLOW)
    d.text((70, 145), date_str, font=f2, fill=C_DIM)


def _footer(d, text):
    f = _font(34)
    tw = d.textlength(text, font=f)
    d.text(((W - tw) / 2, H - 130), text, font=f, fill=C_DIM)


def draw_intro(part, path):
    from PIL import ImageDraw
    img, d = _bg()
    _header(d, f'{part["date_str"]} 星期{part["weekday"]}')
    f_title, f_sub = _font(120), _font(52)
    t = '今日科技早报'
    tw = d.textlength(t, font=f_title)
    d.text(((W - tw) / 2, 640), t, font=f_title, fill=C_WHITE)
    s = f'每天 {part["count"]} 条 · AI 为你策展'
    sw = d.textlength(s, font=f_sub)
    d.text(((W - sw) / 2, 830), s, font=f_sub, fill=C_GRAY)
    # 黄色装饰条
    d.rectangle([(W - 120) / 2, 980, (W + 120) / 2, 992], fill=C_YELLOW)
    _footer(d, 'xiaojj.pro')
    img.save(path)


def draw_pick(part, path):
    from PIL import ImageDraw
    img, d = _bg()
    _header(d, part['date_str'])

    # 编号 01 / 08
    f_idx, f_tot = _font(200), _font(72)
    idx = f'{part["index"]:02d}'
    d.text((70, 230), idx, font=f_idx, fill=C_YELLOW)
    tot = f'/ {part["total"]:02d}'
    d.text((70 + d.textlength(idx, font=f_idx) + 20, 360), tot, font=f_tot, fill=C_DIM)

    # 标题
    y = 520
    f_title = _font(66)
    lines = _wrap(d, part['title'], f_title, W - 140)
    if len(lines) > 4:
        lines = lines[:4]
        lines[-1] = lines[-1][:-1] + '…'
    for ln in lines:
        d.text((70, y), ln, font=f_title, fill=C_WHITE)
        y += 92

    # 分隔线
    y += 20
    d.rectangle([70, y, W - 70, y + 3], fill=C_LINE)
    y += 45

    # 摘要
    f_sum = _font(42)
    slines = _wrap(d, part['summary'], f_sum, W - 140)
    if len(slines) > 9:
        slines = slines[:9]
        slines[-1] = slines[-1][:-1] + '…'
    for ln in slines:
        d.text((70, y), ln, font=f_sum, fill=C_GRAY)
        y += 66

    # 来源（跟在摘要后面，避免和底部字幕重叠）
    f_src = _font(36)
    d.text((70, y + 30), f'来源 · {part["source"]}', font=f_src, fill=C_DIM)
    _footer(d, 'xiaojj.pro')
    img.save(path)


def draw_outro(part, path):
    from PIL import ImageDraw
    img, d = _bg()
    f1, f2, f3 = _font(72), _font(50), _font(52)
    t1 = '以上就是今天的科技早报'
    tw = d.textlength(t1, font=f1)
    d.text(((W - tw) / 2, 700), t1, font=f1, fill=C_WHITE)
    t2 = f'我是{HOST_NAME}，我们明天早上八点再见'
    tw2 = d.textlength(t2, font=f2)
    d.text(((W - tw2) / 2, 830), t2, font=f2, fill=C_GRAY)
    d.rectangle([(W - 120) / 2, 950, (W + 120) / 2, 962], fill=C_YELLOW)
    t3 = 'xiaojj.pro'
    tw3 = d.textlength(t3, font=f3)
    d.text(((W - tw3) / 2, 1020), t3, font=f3, fill=C_YELLOW)
    img.save(path)


def build_slide(part, path):
    if part['kind'] == 'intro':
        draw_intro(part, path)
    elif part['kind'] == 'outro':
        draw_outro(part, path)
    else:
        draw_pick(part, path)


# ================= 字幕 =================

def merge_subs(subs):
    entries = []
    buf_text, buf_start, buf_end = '', None, None
    for start, end, text in subs:
        if buf_start is None:
            buf_start = start
        buf_text += text
        buf_end = end
        if any(p in text for p in '，。！？；：、') or len(buf_text) >= 14:
            entries.append((buf_start, max(buf_end, buf_start + 800), buf_text))
            buf_text, buf_start, buf_end = '', None, None
    if buf_text:
        entries.append((buf_start, max(buf_end, buf_start + 800), buf_text))
    return entries


def ass_time(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, cs = divmod(rem, 10)
    return f'{h:d}:{m:02d}:{s:02d}.{cs:02d}'


def write_ass(entries, path):
    header = (
        '[Script Info]\n'
        'ScriptType: v4.00+\n'
        'PlayResX: 1080\n'
        'PlayResY: 1920\n'
        'WrapStyle: 2\n'
        'ScaledBorderAndShadow: yes\n'
        '\n'
        '[V4+ Styles]\n'
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, '
        'OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, '
        'ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, '
        'Alignment, MarginL, MarginR, MarginV, Encoding\n'
        'Style: Sub,Noto Sans SC,64,&H00FFFFFF,&H000000FF,&H99000000,&H00000000,'
        '0,0,0,0,100,100,0,0,1,3,0,2,40,40,200,1\n'
        '\n'
        '[Events]\n'
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(header)
        for s, e, t in entries:
            safe = t.replace('{', '(').replace('}', ')')
            f.write(f'Dialogue: 0,{ass_time(s)},{ass_time(e)},Sub,,0,0,0,,{safe}\n')


def install_font():
    if not os.path.exists(FONT_PATH):
        print('  ⚠️ 字体文件不存在，字幕可能无法显示中文')
        return False
    font_dir = os.path.expanduser('~/.fonts')
    os.makedirs(font_dir, exist_ok=True)
    dest = os.path.join(font_dir, 'NotoSansSC-SemiBold.ttf')
    if not os.path.exists(dest):
        shutil.copy(FONT_PATH, dest)
    try:
        subprocess.run(['fc-cache', '-f', font_dir], capture_output=True, timeout=60)
    except Exception:
        pass
    return True


# ================= 合成 =================

def make_segment(slide_path, mp3_path, seg_path):
    """一张卡片 + 一段音频 -> 一个分段视频"""
    cmd = ['ffmpeg', '-y',
           '-loop', '1', '-framerate', '2', '-i', slide_path,
           '-i', mp3_path,
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
           '-pix_fmt', 'yuv420p', '-r', '30',
           '-c:a', 'aac', '-b:a', '96k',
           '-shortest', '-movflags', '+faststart', seg_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        print(f'  分段合成失败 {os.path.basename(slide_path)}: {r.stderr[-300:]}')
    return r.returncode == 0


def concat_segments(seg_paths, out_path):
    list_path = os.path.join(os.path.dirname(seg_paths[0]), 'concat.txt')
    with open(list_path, 'w', encoding='utf-8') as f:
        for p in seg_paths:
            f.write(f"file '{p}'\n")
    cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_path,
           '-c', 'copy', '-movflags', '+faststart', out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return r.returncode == 0


def burn_subs(video_path, ass_path, out_path):
    ass_esc = ass_path.replace("'", r"'\''").replace(':', r'\:')
    cmd = ['ffmpeg', '-y', '-i', video_path,
           '-vf', f"subtitles='{ass_esc}'",
           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
           '-pix_fmt', 'yuv420p', '-c:a', 'copy',
           '-movflags', '+faststart', out_path]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        print(f'  字幕烧录失败: {r.stderr[-300:]}')
    return r.returncode == 0


def main():
    briefing_path = os.path.join(DATA_DIR, 'briefing.json')
    if not os.path.exists(briefing_path):
        print('⏭️ 没有 briefing.json，跳过视频生成')
        return
    import json
    with open(briefing_path, encoding='utf-8') as f:
        briefing = json.load(f)
    if not briefing.get('picks'):
        print('⏭️ 早报为空，跳过视频生成')
        return
    if not shutil.which('ffmpeg'):
        print('⏭️ 没有 ffmpeg，跳过视频生成')
        return
    if not ensure_edge_tts():
        return

    today = briefing.get('date', datetime.now().strftime('%Y-%m-%d'))
    date_str = briefing.get('date_str', today)
    workdir = os.path.join(VIDEO_DIR, '_work')
    os.makedirs(workdir, exist_ok=True)
    out_path = os.path.join(VIDEO_DIR, f'{today}.mp4')

    # Pillow 不可用时降级：整段一个封面（旧行为）
    use_slides = ensure_pillow() and os.path.exists(FONT_PATH)
    if not use_slides:
        print('  ⚠️ Pillow/字体不可用，降级为单封面视频')

    parts = build_parts(briefing)
    print(f'🎬 共 {len(parts)} 段口播，正在合成音频...')
    seg_paths, all_entries, offset = [], [], 0
    for part in parts:
        mp3 = os.path.join(workdir, f'{part["key"]}.mp3')
        try:
            subs = asyncio.run(synthesize_part(part['narr'], mp3))
        except Exception as e:
            print(f'❌ TTS 合成失败 ({part["key"]}): {e}')
            return
        dur = get_audio_duration_ms(mp3)
        if not subs:
            subs = proportional_subs(part['narr'], dur)
        if not subs or not dur:
            print(f'❌ 分段无字幕/无时长 ({part["key"]})，跳过')
            return
        entries = merge_subs(subs)
        all_entries += [(s + offset, e + offset, t) for s, e, t in entries]
        offset += dur

        slide = os.path.join(workdir, f'{part["key"]}.png')
        try:
            if use_slides:
                build_slide(part, slide)
            else:
                shutil.copy(COVER_PATH, slide)
        except Exception as e:
            print(f'  ⚠️ 卡片绘制失败 ({part["key"]}): {e}，用封面代替')
            shutil.copy(COVER_PATH, slide)

        seg = os.path.join(workdir, f'{part["key"]}.mp4')
        if not make_segment(slide, mp3, seg):
            print('❌ 分段视频合成失败')
            return
        seg_paths.append(seg)
        print(f'  ✓ {part["key"]} ({dur/1000:.1f}s)')

    print(f'  拼接 {len(seg_paths)} 段...')
    full_path = os.path.join(workdir, 'full.mp4')
    if not concat_segments(seg_paths, full_path):
        print('❌ 视频拼接失败')
        return

    sub_path = os.path.join(workdir, 'subs.ass')
    write_ass(all_entries, sub_path)
    print(f'  字幕 {len(all_entries)} 条，正在烧录...')
    install_font()
    if not burn_subs(full_path, sub_path, out_path):
        print('  ⚠️ 字幕烧录失败，输出无字幕版本')
        shutil.copy(full_path, out_path)

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f'✅ 视频已生成: {out_path} ({size_mb:.1f} MB)')
    shutil.rmtree(workdir, ignore_errors=True)

    index_path = os.path.join(VIDEO_DIR, 'index.json')
    index = []
    if os.path.exists(index_path):
        try:
            with open(index_path, encoding='utf-8') as f:
                index = json.load(f)
        except Exception:
            index = []
    index = [e for e in index if e.get('date') != today]
    index.append({
        'date': today,
        'date_str': date_str,
        'title': f'{date_str} 科技早报',
        'file': f'data/video/{today}.mp4',
        'overview': briefing.get('overview', ''),
        'count': len(briefing.get('picks', [])),
        'size_mb': round(size_mb, 1),
    })
    index.sort(key=lambda e: e['date'], reverse=True)
    for old in index[KEEP_VIDEOS:]:
        old_mp4 = os.path.join(VIDEO_DIR, f'{old["date"]}.mp4')
        if os.path.exists(old_mp4):
            os.remove(old_mp4)
    index = index[:KEEP_VIDEOS]
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f'✅ 视频索引已更新（共 {len(index)} 期）')


if __name__ == '__main__':
    main()
