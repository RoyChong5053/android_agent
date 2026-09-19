"""弹窗处理：通用关闭。

策略：优先用已知 state 的专用处理（符文/结算等），
其余用 X 按钮模板匹配关闭；模板匹配比 Hough 稳（Hough 在正常画面会误报）。
关闭后必须由调用方验证画面确实变了，避免误点死循环。
"""
from core.perception.detectors import find_template, template_center
from core.perception.screens import X_TEMPLATES, get_template


def find_close_x(frame):
    """全图找关闭X按钮，返回 (中心(x,y), score) 或 None。"""
    best = None
    for name, thresh in X_TEMPLATES:
        tpl = get_template(name)
        score, loc = find_template(frame.bgr, tpl)
        if score >= thresh and (best is None or score > best[1]):
            best = (template_center(loc, tpl), score)
    return best
