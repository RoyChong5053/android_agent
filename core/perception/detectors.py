"""检测原语：模板匹配 / 颜色块 / Hough圆。全部毫秒级，无需训练。"""
import cv2
import numpy as np


def find_template(frame_bgr, tpl_bgr, roi=None, thresh: float = 0.8):
    """模板匹配。返回 (score, (x, y))，(x,y) 为模板左上角全图坐标。

    roi=(x0,y0,x1,y1) 限定搜索区域，可提速并避免误匹配。
    """
    ox, oy = 0, 0
    img = frame_bgr
    if roi:
        x0, y0, x1, y1 = roi
        img = frame_bgr[y0:y1, x0:x1]
        ox, oy = x0, y0
    res = cv2.matchTemplate(img, tpl_bgr, cv2.TM_CCOEFF_NORMED)
    _, maxv, _, maxloc = cv2.minMaxLoc(res)
    return float(maxv), (ox + maxloc[0], oy + maxloc[1])


def template_center(loc, tpl_bgr) -> tuple[int, int]:
    th, tw = tpl_bgr.shape[:2]
    return loc[0] + tw // 2, loc[1] + th // 2


def find_color(frame_bgr, lower, upper, roi=None, min_area: int = 50):
    """颜色块检测（HSV）。返回最大色块的质心 (x,y) 与面积。"""
    ox, oy = 0, 0
    img = frame_bgr
    if roi:
        x0, y0, x1, y1 = roi
        img = frame_bgr[y0:y1, x0:x1]
        ox, oy = x0, y0
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    best = None
    for c in cnts:
        a = cv2.contourArea(c)
        if a < min_area:
            continue
        if best is None or a > best[1]:
            m = cv2.moments(c)
            if m["m00"] == 0:
                continue
            best = ((int(ox + m["m10"] / m["m00"]), int(oy + m["m01"] / m["m00"])), a)
    return best


def find_close_button(frame_bgr, roi_frac=(0.66, 0.62, 1.0, 1.0)):
    """右下 ROI + Hough圆找关闭X，返回 (x,y) 全图坐标或 None。"""
    h, w = frame_bgr.shape[:2]
    x0, y0 = int(w * roi_frac[0]), int(h * roi_frac[1])
    roi = frame_bgr[y0:h, x0:w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, 1, 100,
        param1=100, param2=20, minRadius=15, maxRadius=50,
    )
    if circles is None:
        return None
    c = circles[0][0]
    return int(x0 + c[0]), int(y0 + c[1])
