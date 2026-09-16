"""截图模块：adb screencap 封装。

一次采集 -> 解码一次 -> 共享 Frame，避免多个检测器重复 imdecode，
也避免把全分辨率原图喂给 LLM（会撑爆请求体触发 413）。
"""
import io
import subprocess
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image

DEVICE = "LGV35fd728cd2"
PREVIEW_W = 720
PREVIEW_Q = 60


@dataclass
class Frame:
    png: bytes
    bgr: np.ndarray
    gray: np.ndarray

    @property
    def w(self) -> int:
        return self.bgr.shape[1]

    @property
    def h(self) -> int:
        return self.bgr.shape[0]

    @property
    def size(self) -> tuple[int, int]:
        return self.w, self.h

    def crop(self, x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
        """裁剪，坐标超出边界自动截断。"""
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.w, x1), min(self.h, y1)
        return self.bgr[y0:y1, x0:x1]

    def small_jpeg(self, max_w: int = PREVIEW_W, quality: int = PREVIEW_Q) -> bytes:
        """降采样小图（~50KB），唯一允许给 LLM 的形式。"""
        im = Image.fromarray(cv2.cvtColor(self.bgr, cv2.COLOR_BGR2RGB))
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=quality, optimize=True)
        return buf.getvalue()

    def save(self, path: str) -> str:
        with open(path, "wb") as f:
            f.write(self.png)
        return path


def decode(png_bytes: bytes) -> Frame:
    arr = np.frombuffer(png_bytes, np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError("screencap 解码失败（空帧？）")
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    return Frame(png=png_bytes, bgr=bgr, gray=gray)


def capture_png_bytes() -> bytes:
    p = subprocess.run(
        ["adb", "-s", DEVICE, "exec-out", "screencap", "-p"],
        capture_output=True, check=True,
    )
    return p.stdout


def capture_frame() -> Frame:
    return decode(capture_png_bytes())


def capture_to_file(path: str) -> str:
    data = capture_png_bytes()
    with open(path, "wb") as f:
        f.write(data)
    return path
