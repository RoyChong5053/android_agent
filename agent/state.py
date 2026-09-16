"""状态：帧差检测（静止 / 变化）"""
import cv2
import numpy as np


def frame_diff(a_gray, b_gray) -> float:
    """平均逐像素差，越大变化越明显。"""
    return float(cv2.absdiff(a_gray, b_gray).mean())


def changed(a_gray, b_gray, thresh: float = 2.0) -> bool:
    return frame_diff(a_gray, b_gray) >= thresh


def is_still(prev_gray, gray, thresh: float = 2.0) -> bool:
    if prev_gray is None:
        return False
    return frame_diff(prev_gray, gray) < thresh


def to_gray(png_bytes: bytes):
    arr = np.frombuffer(png_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
