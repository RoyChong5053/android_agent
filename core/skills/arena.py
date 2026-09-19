"""竞技场刷翅膀 skill（单局循环）。

与地下城核心差异：没有「连续战斗」，每局手动：
  名单 -> 选对手(手动给坐标，挑最弱) -> 队伍选择(固定阵容直接开)
  -> 开始战斗 -> 开x3+自动 -> 等胜利 -> 点确认 -> 回名单

经验坐标(1440x720, 实测有效，勿改)：
  SPEED_TAP=(222,668)  速度档(点3下必到x3，用模板确认)
  AUTO_TAP =(285,668)  自动开关(▶开/⏸关，用模板确认)
  START    =(1180,460) 队伍选择→开始战斗
  CONFIRM  =(720,360)  胜利页点确认
教训：
  - 中途切后台=判负(-11分)+扣1翅膀，循环中严禁乱点系统键
  - 齿轮=暂停菜单，误触后按 BACK 关闭再继续
  - 胜利页与地下城共用 victory_title 模板(0.984)，detect_state 直接复用
"""
import subprocess
import time

import cv2
import numpy as np

from core.action.adb_wrapper import tap
from core.perception.capture import capture_frame
from core.perception.detectors import find_template
from core.utils.logger import Journal
from core.perception.screens import ANCHORS, detect_state, get_template
from core.perception.vl_sweep import parse_list

DEVICE_ARG = ["adb", "-s", "LGV35fd728cd2"]

SPEED_TAP = (222, 668)
AUTO_TAP = (285, 668)
START = (1180, 460)
CONFIRM = (720, 360)

SPEED_ROI = (140, 625, 230, 710)
AUTO_ROI = (225, 625, 315, 710)
PAUSE_ROI = (600, 270, 840, 360)

SPD_X1 = "battle_speed_x1"
SPD_X3 = "battle_speed_x3"
AUTO_OFF = "battle_auto_off"
AUTO_ON = "battle_auto_on"
PAUSE = "arena_pause"

VICTORY_POLL = 10.0
VICTORY_TIMEOUT = 300


def _score(frame, name, roi=None):
    tpl = get_template(name)
    s, _ = find_template(frame.bgr, tpl, roi=roi)
    return s


def _back():
    subprocess.run(DEVICE_ARG + ["shell", "input", "keyevent", "4"], check=True)
    time.sleep(1.5)


def _read_settings(frame):
    sx1 = _score(frame, SPD_X1, SPEED_ROI)
    sx3 = _score(frame, SPD_X3, SPEED_ROI)
    son = _score(frame, AUTO_ON, AUTO_ROI)
    soff = _score(frame, AUTO_OFF, AUTO_ROI)
    return sx1, sx3, son, soff


def _is_x3(sx1, sx3) -> bool:
    return sx3 > 0.96 and sx3 > sx1


def _is_auto(son, soff) -> bool:
    return son > 0.96 and son > soff


def _progressing(secs: float = 15) -> bool:
    """行为验证：战斗画面是否在推进(自动进行中)。
    手动卡技能选择时画面基本静止，只有待机动画小抖动。
    """
    from core.brain.state import frame_diff
    f0 = capture_frame()
    hits = 0
    n = max(2, int(secs / 3))
    for _ in range(n):
        time.sleep(3)
        f1 = capture_frame()
        if frame_diff(f0.gray, f1.gray) > 12.0:
            hits += 1
        f0 = f1
    return hits >= 2


def ensure_settings(j: Journal, tries: int = 4) -> bool:
    """保证 x3 + 自动已开：图标投票 + 行为验证双保险。"""
    for _ in range(tries):
        f = capture_frame()
        if _score(f, PAUSE, PAUSE_ROI) > 0.8:
            j.log(state="arena_pause", note="误触暂停，BACK关闭")
            _back()
            continue
        sx1, sx3, son, soff = _read_settings(f)
        ok_icon = _is_x3(sx1, sx3) and _is_auto(son, soff)
        j.log(state="arena_battle",
              note=f"x1={sx1:.2f} x3={sx3:.2f} on={son:.2f} off={soff:.2f}")
        if ok_icon and _progressing():
            return True
        if not _is_x3(sx1, sx3):
            tap(*SPEED_TAP)  # x1->x2->x3循环，最多3下必中
            time.sleep(1.0)
        else:
            tap(*AUTO_TAP)  # 图标说开但没推进/图标说没开：切一下再验证
            time.sleep(1.0)
    f = capture_frame()
    sx1, sx3, son, soff = _read_settings(f)
    ok = _is_x3(sx1, sx3) and _is_auto(son, soff) and _progressing(9)
    j.log(state="arena_battle", note=f"ensure_settings -> {ok}")
    return ok


def wait_victory(j: Journal, timeout: float = VICTORY_TIMEOUT):
    """等胜利页，返回 frame 或 None(超时)。附带卡死自愈：
    连续4轮(40s)画面几乎不动 → 当自动没开，点自动+重确保。
    """
    from core.brain.state import frame_diff
    t0 = time.time()
    f = capture_frame()
    stills = 0
    while time.time() - t0 < timeout:
        st, sc, _ = detect_state(f)
        if st == "victory":
            j.log(state=st, note=f"战斗结束，用时 {time.time()-t0:.0f}s")
            return f
        if st not in ("battle",):
            j.log(state=st, note="战斗中出现非预期画面")
        if _score(f, PAUSE, PAUSE_ROI) > 0.8:
            j.log(state="arena_pause", note="等待中出现暂停，BACK关闭")
            _back()
            f = capture_frame()
            stills = 0
            continue
        time.sleep(VICTORY_POLL)
        nf = capture_frame()
        if frame_diff(f.gray, nf.gray) < 5.0:
            stills += 1
        else:
            stills = 0
        f = nf
        if stills >= 4:
            j.log(state="battle", note="40s无推进，自愈：重开自动")
            tap(*AUTO_TAP)
            time.sleep(1.0)
            ensure_settings(j, tries=2)
            stills = 0
            f = capture_frame()
    j.log(state="timeout", note="等胜利超时，存图待查")
    f.save(f"/tmp/arena_timeout_{time.time():.0f}.png")
    return None


STARTBTN = "arena_startbtn"
STARTBTN_ROI = (1050, 400, 1320, 520)


def _wait_startbtn(j: Journal, opp_xy: tuple[int, int], timeout: float = 20) -> bool:
    """等队伍选择页出现(开始战斗按钮)。还停在名单就补点一次。"""
    t0 = time.time()
    retapped = False
    while time.time() - t0 < timeout:
        f = capture_frame()
        st, _, _ = detect_state(f)
        if st == "arena_list":
            if not retapped and time.time() - t0 > 6:
                tap(*opp_xy)
                j.log(action="tap 补点对手", x=opp_xy[0], y=opp_xy[1])
                retapped = True
            time.sleep(1.5)
            continue
        if _score(f, STARTBTN, STARTBTN_ROI) > 0.8:
            return True
        time.sleep(1.5)
    j.log(state="timeout", note="等队伍选择页超时")
    return False


def _wait_battle_ui(j: Journal, timeout: float = 90) -> bool:
    """等战斗UI出现(底部按钮可读)，替代盲sleep。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        f = capture_frame()
        sx1, sx3, son, soff = _read_settings(f)
        if max(sx1, sx3, son, soff) > 0.5:
            return True
        time.sleep(3)
    j.log(state="timeout", note="等战斗UI超时(加载太久？)")
    return False


def fight_one(j: Journal, opp_xy: tuple[int, int]) -> str:
    """打一局。opp_xy=名单上某行「战斗」按钮坐标。返回 done|fail。

    每步转移都验证，不盲sleep：名单→队伍选择→战斗UI→胜利。
    """
    tap(*opp_xy)
    j.log(action="tap 选对手", x=opp_xy[0], y=opp_xy[1])
    if not _wait_startbtn(j, opp_xy):
        return "fail"
    tap(*START)
    j.log(action="tap 开始战斗", x=START[0], y=START[1])
    if not _wait_battle_ui(j):
        return "fail"
    if not ensure_settings(j):
        return "fail"
    f = wait_victory(j)
    if f is None:
        return "fail"
    tap(*CONFIRM)
    j.log(action="tap 胜利确认", x=CONFIRM[0], y=CONFIRM[1])
    time.sleep(4)
    return "done"


def run(j: Journal, opponents: list[tuple[int, int]]) -> dict:
    """按给定的对手坐标逐个打。打完一局由调用方(人)补下一局坐标。"""
    done = 0
    for i, xy in enumerate(opponents):
        res = fight_one(j, xy)
        j.log(action="fight", note=f"{i+1}/{len(opponents)} -> {res}")
        if res != "done":
            return {"result": res, "fights": done}
        done += 1
    return {"result": "done", "fights": done}


FIGHT_BTN_ROI = (1000, 150, 1180, 720)


def find_fight_buttons(frame) -> list[tuple[int, int]]:
    """多目标匹配名单上所有「战斗」按钮，按y从上到下返回中心坐标。"""
    tpl = get_template("arena_fight_btn")
    x0, y0, x1, y1 = FIGHT_BTN_ROI
    crop = frame.bgr[y0:y1, x0:x1]
    res = cv2.matchTemplate(crop, tpl, cv2.TM_CCOEFF_NORMED)
    ys, _ = np.where(res >= 0.9)
    rows: list[tuple[int, int]] = []
    cx = x0 + (x1 - x0) // 2  # 名单战斗按钮固定在右侧同一x列
    for y in sorted(ys):
        cy = y0 + int(y) + tpl.shape[0] // 2
        if not rows or cy - rows[-1][1] > 40:
            rows.append((cx, cy))
    return rows


def pick_weakest(j: Journal):
    """VL读名单 -> 最弱可打对手的按钮坐标 + 翅膀数。

    返回 (x, y, wings)；VL失败或按钮对不上行数时返回 None(转人工)。
    """
    frame = capture_frame()
    st, _, _ = detect_state(frame)
    if st != "arena_list":
        j.log(state=st, note="不在名单页，无法选对手")
        return None
    info, dt = {}, 0.0
    for attempt in range(3):  # VL偶发空回/超时，重试
        try:
            info, dt = parse_list(frame.png)
        except Exception as e:  # noqa: BLE001
            j.log(state="arena_list", note=f"VL读名单失败(try{attempt+1}): {e}")
            time.sleep(2)
            continue
        if info.get("opponents"):
            break
        j.log(state="arena_list", note=f"VL空回(try{attempt+1}): {str(info)[:120]}")
        time.sleep(2)
    avail = [o for o in info.get("opponents", []) if o.get("available")]
    if not avail:
        j.log(state="arena_list", note="VL: 无可打对手")
        return None
    btns = find_fight_buttons(frame)
    if len(btns) != len(avail):
        j.log(state="arena_list",
              note=f"VL可打{len(avail)}行但模板找到{len(btns)}个按钮，转人工")
        return None
    weak = min(avail, key=lambda o: o.get("level", 99))
    idx = avail.index(weak)
    x, y = btns[idx]
    wings = info.get("wings", "?")
    j.log(state="arena_list",
          note=f"VL({dt:.0f}s) 翅膀{wings} 最弱 row{weak['row']} "
               f"lv{weak.get('level')} {weak.get('name')} -> ({x},{y})")
    return x, y, wings


def grind(j: Journal, max_fights: int = 10) -> dict:
    """全自动刷翅膀：名单→VL选最弱→打→循环，直到翅膀耗尽或异常。"""
    done = 0
    for _ in range(max_fights):
        pick = pick_weakest(j)
        if pick is None:
            return {"result": "need_help", "fights": done}
        x, y, wings = pick
        if isinstance(wings, str) and wings.startswith("0"):
            j.log(action="grind", note=f"翅膀耗尽({wings})，收工")
            return {"result": "done", "fights": done}
        res = fight_one(j, (x, y))
        j.log(action="grind", note=f"第{done+1}局 -> {res} (打前翅膀{wings})")
        if res != "done":
            return {"result": res, "fights": done}
        done += 1
    return {"result": "done", "fights": done}
