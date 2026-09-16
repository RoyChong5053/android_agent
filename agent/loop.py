"""主循环原型：静止检测 -> 快速规则 -> VL兜底"""
import time

from agent.actions import tap
from agent.capture import capture_png_bytes
from agent.detectors import find_close_button
from agent.state import is_still, to_gray
from agent.vl_client import classify_screen


def main(poll: float = 2.0, vl_every: int = 5):
    prev = None
    n = 0
    while True:
        png = capture_png_bytes()
        gray = to_gray(png)
        still = is_still(prev, gray)
        prev = gray
        n += 1
        print(f"[{n}] still={still} size={len(png)}")

        if not still:
            time.sleep(poll)
            continue

        # 规则1：右下关闭按钮（毫秒级）
        pt = find_close_button(png)
        if pt:
            print(f"  -> close button at {pt}, tapping")
            tap(*pt)
            time.sleep(poll)
            continue

        # 规则2：低频VL分类
        if n % vl_every == 0:
            content, dt = classify_screen(png)
            print(f"  -> VL({dt:.1f}s): {content[:200]}")

        time.sleep(poll)


if __name__ == "__main__":
    main()
