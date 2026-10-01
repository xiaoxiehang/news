#!/usr/bin/env python3
"""小红书发布包质检脚本。

用法:
    python scripts/qc_xhs_package.py [--date YYYY-MM-DD]

检查 data/xhs/<date>/ 发布包的完整性与规范，全部通过才算 PASS。
只用标准库 + Pillow，输出纯文本（无 emoji）。

退出码:
    0 - PASS，或该日期无 post.json 时 SKIP
    1 - 有检查项未通过
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 发布包根目录：仓库 data/xhs/<date>/（本脚本位于 scripts/，站点根在其上级）
SITE_ROOT = Path(__file__).resolve().parent.parent
XHS_ROOT = SITE_ROOT / "data" / "xhs"

# 卡片标准尺寸
CARD_SIZE = (1080, 1440)


def fail_lines():
    return []


def check_package(date):
    """返回 (exit_code, lines)。"""
    pkg = XHS_ROOT / date
    post_path = pkg / "post.json"

    # 特殊情况：该日期没有 post.json -> SKIP
    if not post_path.is_file():
        return 0, [f"SKIP: {date} 当天未生成发布包（{post_path} 不存在），无需质检"]

    fails = []

    # a. post.json 存在且是合法 JSON
    try:
        post = json.loads(post_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return 1, [f"FAIL: post.json 合法性 - 文件存在但 JSON 解析失败: {e}"]
    except OSError as e:
        return 1, [f"FAIL: post.json 合法性 - 读取失败: {e}"]

    # b. title 存在且字符数 <= 20
    title = post.get("title")
    if not title:
        fails.append("FAIL: title 长度 - title 字段缺失或为空")
    elif len(title) > 20:
        fails.append(f"FAIL: title 长度 - {len(title)} 字超过 20 字上限: {title}")

    # c. tags 非空且 tags[0] == '鸡仔AI早报'
    tags = post.get("tags")
    if not tags:
        fails.append("FAIL: tags 规范 - tags 字段缺失或为空")
    elif tags[0] != "鸡仔AI早报":
        fails.append(f"FAIL: tags 规范 - 首位应为'鸡仔AI早报'，实际为: {tags[0]}")

    # d. picks.json 存在；len(items) == len(picks)；每条 item 的 usage 非空
    picks_path = pkg / "picks.json"
    items = post.get("items") or []
    if not picks_path.is_file():
        fails.append(f"FAIL: picks.json 存在性 - {picks_path} 不存在")
    else:
        try:
            picks_data = json.loads(picks_path.read_text(encoding="utf-8"))
            picks = picks_data.get("picks")
            if picks is None:
                fails.append("FAIL: picks 字段 - picks.json 缺少 picks 字段")
            elif len(items) != len(picks):
                fails.append(
                    f"FAIL: 条数一致性 - items 共 {len(items)} 条，picks 共 {len(picks)} 条"
                )
        except (json.JSONDecodeError, OSError) as e:
            fails.append(f"FAIL: picks.json 合法性 - 读取/解析失败: {e}")

    for i, item in enumerate(items):
        usage = (item or {}).get("usage")
        if not (usage and str(usage).strip()):
            fails.append(f"FAIL: usage 非空 - 第 {i + 1} 条 item 的 usage 为空")

    # e. 卡片文件：cover.png、end.png、card_01..NN.png；PIL 可打开；尺寸恰为 (1080, 1440)
    try:
        from PIL import Image
    except ImportError:
        return 1, ["FAIL: 环境依赖 - 未安装 Pillow，无法质检卡片图片"]

    expected_cards = (
        ["cover.png"]
        + [f"card_{i:02d}.png" for i in range(1, len(items) + 1)]
        + ["end.png"]
    )
    for name in expected_cards:
        path = pkg / name
        if not path.is_file():
            fails.append(f"FAIL: 卡片存在性 - {name} 不存在")
            continue
        try:
            with Image.open(path) as img:
                img.load()
                if img.size != CARD_SIZE:
                    fails.append(
                        f"FAIL: 卡片尺寸 - {name} 尺寸为 {img.size}，应为 {CARD_SIZE}"
                    )
        except Exception as e:
            fails.append(f"FAIL: 卡片可读性 - {name} 无法用 PIL 正常打开: {e}")

    if fails:
        return 1, fails
    return 0, [f"PASS: {date} 发布包质检通过"]


def main():
    parser = argparse.ArgumentParser(description="小红书发布包质检脚本")
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="质检日期，格式 YYYY-MM-DD，默认当天",
    )
    args = parser.parse_args()

    code, lines = check_package(args.date)
    for line in lines:
        print(line)
    sys.exit(code)


if __name__ == "__main__":
    main()
