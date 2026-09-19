"""批量截图脚本：adb截图按状态分类存储。

用法：
  python scripts/capture.py lobby       # 截1张大厅图（归入lobby目录）
  python scripts/capture.py lobby --count 5   # 连截5张
  python scripts/capture.py --watch     # 监控模式：每2秒截一次，手动分类
"""
import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

DEVICE = "LGV35fd728cd2"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

STATES = ["lobby", "energy_bar", "popup", "result", "victory"]


def capture(count: int = 1, state: str = None, output_dir: str = None):
    """截图并保存到指定目录。"""
    if output_dir is None:
        if state is None or state not in STATES:
            print(f"用法：python capture.py <state> [--count N]")
            print(f"可用状态：{STATES}")
            sys.exit(1)
        output_dir = os.path.join(RAW_DIR, state)

    os.makedirs(output_dir, exist_ok=True)

    for i in range(count):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if count > 1:
            name = f"{ts}_{i+1:03d}.png"
        else:
            name = f"{ts}.png"
        path = os.path.join(output_dir, name)

        result = subprocess.run(
            ["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
            capture_output=True, timeout=30,
        )
        if result.returncode == 0 and len(result.stdout) > 100:
            with open(path, "wb") as f:
                f.write(result.stdout)
            print(f"  [{state}] {name} ({len(result.stdout)} bytes)")
        else:
            print(f"  [ERROR] 截图失败: {result.stderr.decode()[:200]}")
            if os.path.exists(path):
                os.remove(path)


def watch(interval: int = 3):
    """监控模式：持续截图，按状态键保存。"""
    print(f"监控模式启动 (间隔{interval}s, Ctrl+C退出)")
    print("快捷键：l=lobby, e=energy_bar, p=popup, r=result, v=victory, q=退出")
    state_map = {"l": "lobby", "e": "energy_bar", "p": "popup", "r": "result", "v": "victory"}
    counters = {s: 0 for s in STATES}

    try:
        while True:
            print(f"\n等待截图... (状态: {state_map})", end="\r")
            result = subprocess.run(
                ["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
                capture_output=True, timeout=30,
            )
            if result.returncode == 0 and len(result.stdout) > 100:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 保存到临时目录，等用户确认分类
                tmp_dir = os.path.join(RAW_DIR, "_pending")
                os.makedirs(tmp_dir, exist_ok=True)
                path = os.path.join(tmp_dir, f"{ts}.png")
                with open(path, "wb") as f:
                    f.write(result.stdout)
                print(f"\n  截图: {os.path.basename(path)} -> 请用命令移动分类")
                print(f"  例如：mv {path} {RAW_DIR}/lobby/")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监控结束")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量截图工具")
    parser.add_argument("state", nargs="?", help="状态类别")
    parser.add_argument("--count", "-n", type=int, default=1, help="截图数量")
    parser.add_argument("--watch", "-w", action="store_true", help="监控模式")
    args = parser.parse_args()

    if args.watch:
        watch()
    else:
        capture(count=args.count, state=args.state)
