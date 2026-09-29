#!/usr/bin/env python3
"""把 data/briefing.json 转成竖屏短视频（1080x1920，带字幕）。

流程：edge-tts 合成音频 + 词级时间戳 -> 合并成字幕 -> ffmpeg 合成竖屏视频
输出：
  data/video/YYYY-MM-DD.mp4   当期视频
  data/video/index.json        视频列表（倒序，只保留最近 7 期）

没有 briefing.json 或任一步骤失败时静默跳过，不影响流水线。
需要 ffmpeg（含 libass）和中文字体（仓库自带 scripts/fonts/NotoSansSC-SemiBold.ttf）。
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


def build_script(briefing):
    today = briefing.get('date', datetime.now().strftime('%Y-%m-%d'))
    dt = datetime.strptime(today, '%Y-%m-%d')
    date_str = briefing.get('date_str') or dt.strftime('%Y年%m月%d日')
    weekday = WEEKDAYS[dt.weekday()]

    parts = [
        f'大家好，我是{HOST_NAME}，欢迎收听今日科技早报。',
        f'今天是{date_str}，星期{weekday}。',
    ]
    if briefing.get('overview'):
        parts.append(f'先来听听今天的大局：{briefing["overview"]}')
    picks = briefing.get('picks', [])
    if picks:
        parts.append(f'接下来是今天的{len(picks)}条必读。')
        cn = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']
        for i, p in enumerate(picks, 1):
            num = cn[i - 1] if i <= 10 else str(i)
            seg = f'第{num}条，{p.get("title", "")}。'
            if p.get('summary'):
                seg += p['summary']
            parts.append(seg)
    parts.append(f'以上就是今天的科技早报，我是{HOST_NAME}，我们明天早上八点再见。')
    return '\n'.join(parts)


async def synthesize_with_subs(script, workdir):
    """合成音频并返回词级字幕 [(start_ms, end_ms, text)]"""
    import edge_tts
    # edge-tts 7.x 默认只返回 SentenceBoundary，必须显式要求 WordBoundary
    try:
        communicate = edge_tts.Communicate(script, VOICE, boundary='WordBoundary')
    except TypeError:
        communicate = edge_tts.Communicate(script, VOICE)  # 兼容旧版本
    mp3_path = os.path.join(workdir, 'audio.mp3')
    subs = []
    with open(mp3_path, 'wb') as f:
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                f.write(chunk['data'])
            elif chunk['type'] in ('WordBoundary', 'SentenceBoundary'):
                subs.append((chunk['offset'] // 10000, (chunk['offset'] + chunk['duration']) // 10000, chunk['text']))
    return mp3_path, subs


def get_audio_duration_ms(mp3_path):
    """用 ffprobe 获取音频时长（毫秒）"""
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', mp3_path],
            capture_output=True, text=True, timeout=30)
        return int(float(r.stdout.strip()) * 1000)
    except Exception:
        return 0


def proportional_subs(script, duration_ms):
    """按字数把口播稿均分到音频时长上（拿不到词级时间戳时的兜底字幕）"""
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


def merge_subs(subs):
    """把词级字幕合并成短句字幕"""
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
    """生成 ASS 字幕文件（样式直接写在文件里，避免 force_style 解析问题）"""
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
    """把仓库字体装进 fontconfig，供 libass 字幕使用"""
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


def run_ffmpeg(mp3_path, sub_path, date_str, out_path, with_subs=True):
    workdir = os.path.dirname(mp3_path)
    title_file = os.path.join(workdir, 'title.txt')
    date_file = os.path.join(workdir, 'date.txt')
    with open(title_file, 'w', encoding='utf-8') as f:
        f.write('今日科技早报')
    with open(date_file, 'w', encoding='utf-8') as f:
        f.write(date_str)

    font_esc = FONT_PATH.replace("'", r"'\''")
    vf = (
        f"[0:v]split=2[bg_src][fg_src];"
        f"[bg_src]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"gblur=sigma=50,drawbox=x=0:y=0:w=1080:h=1920:c=black@0.45:t=fill[bg];"
        f"[fg_src]scale=620:620[fg];"
        f"[bg][fg]overlay=(W-w)/2:430,"
        f"drawtext=fontfile='{font_esc}':textfile='{title_file}':fontsize=76:fontcolor=white:x=(w-text_w)/2:y=200,"
        f"drawtext=fontfile='{font_esc}':textfile='{date_file}':fontsize=44:fontcolor=#FFD166:x=(w-text_w)/2:y=310"
    )
    if with_subs:
        ass_esc = sub_path.replace("'", r"'\''").replace(':', r'\:')
        vf += f",subtitles='{ass_esc}'"
    vf += '[v]'

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-framerate', '1', '-i', COVER_PATH,
        '-i', mp3_path,
        '-filter_complex', vf,
        '-map', '[v]', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '28',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '96k',
        '-shortest', '-movflags', '+faststart',
        out_path,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)
    if r.returncode != 0:
        print(f'  ffmpeg 失败: {r.stderr[-500:]}')
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

    script = build_script(briefing)
    print(f'🎬 口播稿 {len(script)} 字，正在合成音频+字幕...')
    try:
        mp3_path, subs = asyncio.run(synthesize_with_subs(script, workdir))
    except Exception as e:
        print(f'❌ TTS 合成失败: {e}')
        return
    if not subs:
        print('  ⚠️ 未获取到词级时间戳，改用按字数均分字幕...')
        subs = proportional_subs(script, get_audio_duration_ms(mp3_path))
    if not subs:
        print('❌ 字幕生成失败，跳过')
        return

    entries = merge_subs(subs)
    sub_path = os.path.join(workdir, 'subs.ass')
    write_ass(entries, sub_path)
    print(f'  字幕 {len(entries)} 条，正在合成视频...')
    install_font()

    ok = run_ffmpeg(mp3_path, sub_path, date_str, out_path, with_subs=True)
    if not ok:
        print('  ⚠️ 带字幕合成失败，尝试无字幕版本...')
        ok = run_ffmpeg(mp3_path, sub_path, date_str, out_path, with_subs=False)
    if not ok:
        print('❌ 视频合成失败')
        return

    size_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f'✅ 视频已生成: {out_path} ({size_mb:.1f} MB)')

    # 清理工作目录
    shutil.rmtree(workdir, ignore_errors=True)

    # 更新索引，只保留最近 KEEP_VIDEOS 期
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
