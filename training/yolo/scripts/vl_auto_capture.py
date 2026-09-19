"""VL自动截图采集：利用本地VL模型(12888)解析截图，自动归档为YOLO训练数据。

ComfyUI式归档：每次运行生成一对文件：
  YYYYMMDD_HHMMSS.png  — 原始截图
  YYYYMMDD_HHMMSS.md   — VL结构化分析（按钮/状态/类别建议）

数据目录：yolo/data/vl_raw/

用法：
  python vl_auto_capture.py                  # 采集一次（适合边玩边采）
  python vl_auto_capture.py --loop --interval 30  # 持续采集，每30秒一次
  python vl_auto_capture.py --categories popup,result,victory  # 只记录特定类别
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_DIR, "yolo", "data")
VL_RAW_DIR = os.path.join(DATA_DIR, "vl_raw")
DEVICE = "LGV35fd728cd2"

PROMPT = """这是魔灵召唤(Summoners War)手游的截图，任务是收集YOLO模型训练数据。
请详细分析这张图片并输出JSON，包含以下字段：
1. screen: 当前游戏界面/状态的英文ID（如 lobby, battle_map, victory, result_page 等）
2. yolo_category: 最适合的YOLO训练类别，从以下5类选一个：lobby / energy_bar / popup / result / victory
3. buttons: 所有可交互按钮列表，每个元素包含 {text: 按钮文字, x: 0-1000, y: 0-1000, desc: 可选描述}
4. readings: 所有可见数字信息（如体力值、翅膀数、等级、进度等）
5. is_valid_for_yolo: 这个画面是否有足够独特的UI特征来训练YOLO（true/false）
6. notes: 简要描述画面内容和训练价值
只输出JSON，不要推理过程。"""


def capture_png_bytes():
    result = subprocess.run(
        ["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
        capture_output=True, timeout=30,
    )
    if result.returncode == 0 and len(result.stdout) > 100:
        return result.stdout
    return b""


def vl_analyze(png_bytes: bytes):
    sys.path.insert(0, PROJECT_DIR)
    from agent.vl_client import ask, MAX_W as VL_MAX_W  # 复用项目VL客户端

    content, dt = ask(PROMPT, png_bytes, max_tokens=1024)
    return content, dt


def strip_json(raw: str):
    try:
        s, e = raw.index("{"), raw.rindex("}") + 1
        return json.loads(raw[s:e])
    except Exception:
        return {"raw": raw}


def save_png(png_bytes: bytes, ts: str):
    os.makedirs(VL_RAW_DIR, exist_ok=True)
    path = os.path.join(VL_RAW_DIR, f"{ts}.png")
    with open(path, "wb") as f:
        f.write(png_bytes)
    return path


def save_md(ts: str, analysis: dict, raw_text: str, dt: float, png_name: str):
    yolo_cat = analysis.get("yolo_category", "unknown")
    screen = analysis.get("screen", "unknown")
    is_valid = analysis.get("is_valid_for_yolo", False)
    buttons = analysis.get("buttons", [])
    readings = analysis.get("readings", {})
    notes = analysis.get("notes", "")

    lines = [
        f"# VL Analysis — {ts}",
        "",
        f"**Timestamp**: {ts}",
        f"**Image**: {png_name}",
        f"**VL Latency**: {dt:.1f}s",
        "",
        "---",
        "",
        "## Game State",
        f"- Screen: {screen}",
        f"- YOLO Category: {yolo_cat}",
        f"- Valid for YOLO training: {is_valid}",
        "",
        "## Interactive Elements",
    ]
    if buttons:
        lines.append("| Element | Text | x | y |")
        lines.append("|---------|------|---|---|")
        for b in buttons:
            lines.append(f"| Button | {b.get('text','?')} | {b.get('x','?')} | {b.get('y','?')} |")
    else:
        lines.append("No buttons detected.")
    lines.append("")
    lines.append("## Readings")
    if readings:
        for k, v in readings.items():
            lines.append(f"- {k}: {v}")
    else:
        lines.append("No readings detected.")
    lines.append("")
    lines.append(f"## Notes\n{notes}")
    lines.append("")
    lines.append("---")
    lines.append("## Raw VL Output")
    lines.append("```json")
    lines.append(json.dumps(analysis, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")

    path = os.path.join(VL_RAW_DIR, f"{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def capture_one(categories=None):
    png_bytes = capture_png_bytes()
    if not png_bytes:
        print("截图失败", flush=True)
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"VL分析中...", flush=True)

    try:
        raw_text, dt = vl_analyze(png_bytes)
        analysis = strip_json(raw_text)
        cat = analysis.get("yolo_category", "unknown")
        valid = analysis.get("is_valid_for_yolo", False)

        if categories and cat not in categories:
            print(f"类别 {cat} 不在目标中，跳过保存", flush=True)
            return {"ts": ts, "category": cat, "valid": valid, "png": None, "md": None}

        png_path = save_png(png_bytes, ts)
        md_path = save_md(ts, analysis, raw_text, dt, f"{ts}.png")
        print(f"分析完成: yolo_category={cat} valid={valid} → {png_path} + {md_path}", flush=True)
        return {"ts": ts, "category": cat, "valid": valid, "png": png_path, "md": md_path}
    except Exception as e:
        print(f"VL分析失败: {e}", flush=True)
        return {"ts": ts, "category": "error", "valid": False, "png": None, "md": None}


def main():
    ap = argparse.ArgumentParser(description="VL自动截图采集（YOLO训练数据）")
    ap.add_argument("--loop", action="store_true", help="持续采集模式")
    ap.add_argument("--interval", type=int, default=30, help="持续模式下的间隔(秒)")
    ap.add_argument("--categories", "-c", default="all",
                    help="只保存特定类别，如 popup,result,victory")
    args = ap.parse_args()

    categories = None
    if args.categories != "all":
        allowed = {"lobby", "energy_bar", "popup", "result", "victory"}
        categories = [c.strip() for c in args.categories.split(",")]
        for c in categories:
            if c not in allowed:
                print(f"未知类别: {c}, 可用: {allowed}", flush=True)
                sys.exit(1)
        print(f"只保存类别: {categories}", flush=True)

    os.makedirs(VL_RAW_DIR, exist_ok=True)
    print(f"数据目录: {VL_RAW_DIR}", flush=True)
    print("按Ctrl+C停止\n", flush=True)

    count = 0
    saved = 0
    while True:
        print(f"\n=== 采集 #{count+1} [{datetime.now().strftime('%H:%M:%S')}] ===", flush=True)
        result = capture_one(categories)
        if result and result["png"]:
            saved += 1

        count += 1
        if not args.loop:
            break

        print(f"下次采集: {args.interval}秒后", flush=True)
        time.sleep(args.interval)

    print(f"\n采集 {count} 张, 保存 {saved} 张", flush=True)


if __name__ == "__main__":
    main()
