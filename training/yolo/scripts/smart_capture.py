"""智能采集：adb截图 → detect_state分类 → 按类别保存。

设计：
- detect_state() 做主要分类（毫秒级、可靠）
- 不依赖 VL（不可靠）
- 采集到的图实时保存

用法：
  python smart_capture.py --categories lobby,energy_bar,popup --target-per-class 30
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

import cv2

DEVICE = "LGV35fd728cd2"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_DIR = BASE_DIR
RAW_DIR = os.path.join(PROJECT_DIR, "yolo", "data", "raw")

# detect_state 返回值 → YOLO 训练类别映射
STATE_TO_YOLO = {
    "lobby": "lobby",
    "battle_map": "lobby",
    "cairos_select": "lobby",
    "team_select": "lobby",
    "continuous_menu": "lobby",
    "cont_running": "lobby",
    "cont_result": "result",
    "victory": "victory",
    "victory_actions": "victory",
    "rune_popup": "popup",
    "arena_list": "lobby",
    "arena_teamsel": "lobby",
    "arena_victory": "victory",
    "battle": "unknown",
    "energy_bar": "energy_bar",
}

YOLO_CLASSES = ["lobby", "energy_bar", "popup", "result", "victory"]


def capture_png_bytes():
    result = subprocess.run(
        ["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
        capture_output=True, timeout=30,
    )
    if result.returncode == 0 and len(result.stdout) > 100:
        return result.stdout
    return b""


def classify(state: str) -> str:
    return STATE_TO_YOLO.get(state, "unknown")


def save_png(png_bytes: bytes, category: str, index: int):
    os.makedirs(os.path.join(RAW_DIR, category), exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}_{index:04d}.png"
    path = os.path.join(RAW_DIR, category, name)
    with open(path, "wb") as f:
        f.write(png_bytes)
    return name


def collect(categories: list, target_per_class: int, do_swipe: bool = False):
    counts = {}
    for c in categories:
        d = os.path.join(RAW_DIR, c)
        counts[c] = len(os.listdir(d)) if os.path.isdir(d) else 0
    idx = 0
    print(f"采集目标: {categories} × {target_per_class}张", flush=True)
    print(f"当前已存在: " + ", ".join(
        f"{c}={len(os.listdir(os.path.join(RAW_DIR, c))) if os.path.isdir(os.path.join(RAW_DIR, c)) else 0}"
        for c in categories), flush=True)
    print(f"按Ctrl+C停止\n", flush=True)

    sys.path.insert(0, PROJECT_DIR)
    from agent.capture import decode
    from agent.screens import detect_state

    while True:
        done = all(counts[c] >= target_per_class for c in categories)
        if done:
            print("\n所有类别采集达标!")
            break

        png_bytes = capture_png_bytes()
        if not png_bytes:
            time.sleep(0.5)
            continue

        idx += 1

        frame = decode(png_bytes)
        state, conf, pos = detect_state(frame, debug=False)
        yolo_cls = classify(state)

        is_useful = yolo_cls in categories and conf >= 0.2

        if is_useful:
            counts[yolo_cls] += 1
            name = save_png(png_bytes, yolo_cls, counts[yolo_cls])
            print(f"[{idx}] {state} conf={conf:.2f} → {yolo_cls} ✓ ({counts[yolo_cls]}/{target_per_class}) {name}", flush=True)
        else:
            print(f"[{idx}] {state} conf={conf:.2f} → {yolo_cls} ✗ 跳过", flush=True)

        time.sleep(0.3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="智能采集")
    parser.add_argument("--categories", "-c", default="lobby,energy_bar,popup,result,victory")
    parser.add_argument("--target", "-t", type=int, default=30)
    args = parser.parse_args()

    categories = [c.strip() for c in args.categories.split(",")]
    for c in categories:
        if c not in YOLO_CLASSES:
            print(f"未知类别: {c}, 可用: {YOLO_CLASSES}")
            sys.exit(1)

    collect(categories, args.target)
