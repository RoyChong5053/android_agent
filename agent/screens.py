"""画面识别：锚点模板匹配 -> state。

设计：
- 分辨率固定 1440x720，UI 固定，模板匹配最稳且毫秒级。
- 叠加层优先：符文弹窗/结算按钮 在 胜利页 之上，必须先判。
- 每个锚点限定 ROI，既提速也防误匹配。
- 找不到任何锚点 -> battle（战斗中无稳定锚点，且画面在动）。
"""
import os

import cv2
import numpy as np

from agent.detectors import find_template, template_center

SCREENS_DIR = "data/screens"
TEMPLATES_DIR = "data/templates"

# name: (源截图, 裁剪框 x0,y0,x1,y1)
TEMPLATE_SPECS = {
    "rune_enhance":    ("rune_popup2.png",      (748, 552, 902, 612)),
    "actions_replay":  ("victory_actions.png",  (395, 368, 605, 418)),
    "victory_title":   ("victory.png",          (620, 100, 780, 160)),
    "team_start":      ("battle_team_select.png", (1120, 505, 1320, 580)),
    "cairos_tab":      ("cairos_giant.png",     (365, 230, 545, 278)),
    "map_reset":       ("battle_map.png",       (355, 458, 500, 522)),
    "lobby_nav":       ("lobby.png",            (730, 600, 1400, 710)),
    "x_button":        ("cairos_popup.png",     (1212, 44, 1264, 96)),
    "x_button_rune":   ("rune_popup2.png",      (952, 152, 1006, 206)),
    "team_cont":       ("team_select_cont.png", (1115, 546, 1330, 585)),
    "cont_menu_title": ("continuous_menu.png",  (140, 62, 330, 108)),
    "run_label":       ("cont_running.png",     (143, 153, 258, 190)),
    "result_title":    ("cont_result.png",      (400, 216, 650, 256)),
    "arena_title":     ("arena_list.png",       (580, 100, 660, 140)),
}

# 检测顺序（叠加层优先）。用“强化”按钮识别符文弹窗，比“出售”稳（无价格文本干扰）
ANCHORS = [
    ("rune_enhance",   "rune_popup",      (730, 540, 920, 625), 0.85),
    ("actions_replay", "victory_actions", (330, 345, 690, 445), 0.80),
    ("victory_title",  "victory",         (540, 75, 900, 190),  0.80),
    ("result_title",   "cont_result",     (390, 206, 660, 266), 0.80),
    ("run_label",      "cont_running",    (130, 145, 290, 200), 0.80),
    ("cont_menu_title", "continuous_menu", (120, 50, 360, 120), 0.80),    ("team_cont",      "team_select",     (1080, 530, 1360, 600), 0.80),
    ("team_start",     "team_select",     (1070, 480, 1370, 610), 0.80),
    ("cairos_tab",     "cairos_select",   (345, 210, 580, 310), 0.80),
    ("map_reset",      "battle_map",      (320, 435, 540, 545), 0.80),
    ("lobby_nav",      "lobby",           (700, 585, 1430, 718), 0.75),
    ("arena_title",    "arena_list",      (500, 80, 750, 160), 0.85),
]

# 关闭X模板（按顺序尝试），阈值较高避免正常画面误触发
X_TEMPLATES = [("x_button_rune", 0.85), ("x_button", 0.85)]


def build_templates(verbose: bool = True) -> None:
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    for name, (src, rect) in TEMPLATE_SPECS.items():
        img = cv2.imread(os.path.join(SCREENS_DIR, src), cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(os.path.join(SCREENS_DIR, src))
        x0, y0, x1, y1 = rect
        cv2.imwrite(os.path.join(TEMPLATES_DIR, name + ".png"), img[y0:y1, x0:x1])
        if verbose:
            print(f"  {name}.png {x1 - x0}x{y1 - y0}")


_CACHE: dict[str, np.ndarray] = {}


def get_template(name: str) -> np.ndarray:
    if name not in _CACHE:
        path = os.path.join(TEMPLATES_DIR, name + ".png")
        tpl = cv2.imread(path, cv2.IMREAD_COLOR)
        if tpl is None:
            raise FileNotFoundError(f"模板缺失 {path}，先跑 build_templates()")
        _CACHE[name] = tpl
    return _CACHE[name]


def detect_state(frame, debug: bool = False) -> tuple[str, float, tuple[int, int] | None]:
    """返回 (state, score, 命中中心坐标)。未识别 -> battle。

    按 ANCHORS 顺序取第一个过阈值的锚点（叠加层优先），
    不按分数排序——否则背景的“胜利”会盖过其上的符文弹窗。
    """
    scores = []
    hit = None
    for name, state, roi, thresh in ANCHORS:
        tpl = get_template(name)
        score, loc = find_template(frame.bgr, tpl, roi=roi)
        scores.append((state, score, loc, thresh, name))
        if hit is None and score >= thresh:
            hit = (state, score, loc, thresh, name)
    if debug:
        for state, score, loc, thresh, name in scores:
            mark = "OK" if score >= thresh else "  "
            print(f"  {mark} {state:16s} {score:.3f} ({name}) @ {loc}")
    if hit is None:
        return "battle", scores[0][1], None
    state, score, loc, thresh, name = hit
    return state, score, template_center(loc, get_template(name))


def anchor_center(frame, state: str) -> tuple[int, int] | None:
    """取指定 state 锚点的当前中心坐标（用于点击）。"""
    for name, s, roi, thresh in ANCHORS:
        if s != state:
            continue
        score, loc = find_template(frame.bgr, get_template(name), roi=roi)
        if score >= thresh:
            return template_center(loc, get_template(name))
        return None
    return None


if __name__ == "__main__":
    build_templates()
