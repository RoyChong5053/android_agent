"""动作执行：tap / tap_verified / swipe（带人类化抖动）。"""
import random
import subprocess
import time

from core.perception.capture import DEVICE, Frame, capture_frame
from core.brain.state import changed

TAP_THRESH = 2.0


def norm_to_pixel(nx: int, ny: int, w: int, h: int) -> tuple[int, int]:
    """VL归一化0-1000 -> 截图像素坐标"""
    return int(nx / 1000 * w), int(ny / 1000 * h)


def tap(x: int, y: int, jitter: int = 3, dry_run: bool = False) -> tuple[int, int]:
    jx = x + random.randint(-jitter, jitter)
    jy = y + random.randint(-jitter, jitter)
    if dry_run:
        return jx, jy
    subprocess.run(
        ["adb", "-s", DEVICE, "shell", "input", "tap", str(jx), str(jy)],
        check=True,
    )
    time.sleep(random.uniform(0.15, 0.4))
    return jx, jy


def swipe(x0: int, y0: int, x1: int, y1: int, ms: int = 300,
          dry_run: bool = False) -> None:
    if dry_run:
        return
    subprocess.run(
        ["adb", "-s", DEVICE, "shell", "input", "swipe",
         str(x0), str(y0), str(x1), str(y1), str(ms)],
        check=True,
    )
    time.sleep(random.uniform(0.15, 0.4))


def tap_verified(x: int, y: int, before: Frame, *, jitter: int = 3,
                 thresh: float = TAP_THRESH, retries: int = 1,
                 polls: int = 6, poll: float = 0.3, dry_run: bool = False
                 ) -> tuple[Frame, bool, tuple[int, int]]:
    """点完做帧差验证；画面没变得够多就重试。

    返回 (最新帧, 是否确认变化, 实际点击坐标)。
    """
    xy = (x, y)
    frame = before
    for _ in range(retries + 1):
        xy = tap(x, y, jitter=jitter, dry_run=dry_run)
        if dry_run:
            return frame, True, xy
        for _ in range(polls):
            time.sleep(poll)
            after = capture_frame()
            if changed(before.gray, after.gray, thresh):
                return after, True, xy
        frame = after
        before = after
    return frame, False, xy


def tap_norm(nx: int, ny: int, w: int, h: int, **kw) -> tuple[int, int]:
    return tap(*norm_to_pixel(nx, ny, w, h), **kw)
