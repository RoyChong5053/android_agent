"""巨人地下城 B9 刷本 skill（基于游戏内置「连续战斗」，状态驱动）。

核心：内置连续战斗一次开 10 局并自动领奖，Agent 只需在结束后按「再来一次」。
流程：
  lobby --战斗--> [battle_map --卡伊洛斯] --> cairos_select --B9战斗-->
  team_select --连续战斗--> cont_running(自动 10 局) --> cont_result
        --再来一次--> cont_running ... 直到体力不足/达到局数
"""
import time

from core.action.adb_wrapper import tap
from core.perception.capture import capture_frame
from core.utils.logger import Journal
from core.perception.popups import find_close_x
from core.perception.screens import detect_state

COORD = {
    "lobby_battle":      (780, 655),
    "map_cairos":        (720, 670),
    "cairos_b9_battle":  (1180, 250),
    "team_cont_battle":  (1222, 565),
    "result_again":      (760, 616),
    "result_select":     (250, 616),
    "menu_cairos":       (1080, 360),
    "rune_close":        (968, 196),
}

SETTLE = 1.5
RUN_TIMEOUT = 2200       # 一次连续战斗(最多30局)最长等待
RUN_POLL = 8.0


def _tap(frame, xy, j, note=""):
    x, y = xy
    tap(x, y)
    time.sleep(SETTLE)
    j.log(action=f"tap {note}".strip(), x=x, y=y)
    return capture_frame()


def _wait_running(frame, j, timeout=RUN_TIMEOUT):
    """等待连续战斗结束，返回最新的 result 帧。期间顺手关弹窗。"""
    t0 = time.time()
    while time.time() - t0 < timeout:
        st, sc, _ = detect_state(frame)
        if st == "cont_result":
            j.log(state=st, note=f"连续战斗结束，用时 {time.time()-t0:.0f}s")
            return frame
        if st not in ("cont_running",):
            j.log(state=st, note="连续战斗中出现非预期画面")
            if st == "timeout":
                break
        cx = find_close_x(frame)
        if cx:
            frame = _tap(frame, cx[0], j, "close popup")
            continue
        time.sleep(RUN_POLL)
        frame = capture_frame()
    return frame


def run_cycle(j: Journal) -> str:
    """一直推进到「连续战斗结果」，返回 done|timeout|stuck。"""
    frame = capture_frame()
    for _ in range(30):
        state, score, _ = detect_state(frame)

        if state == "lobby":
            frame = _tap(frame, COORD["lobby_battle"], j, "战斗")
        elif state == "battle_map":
            frame = _tap(frame, COORD["map_cairos"], j, "卡伊洛斯")
        elif state == "cairos_select":
            frame = _tap(frame, COORD["cairos_b9_battle"], j, "B9战斗")
        elif state == "team_select":
            frame = _tap(frame, COORD["team_cont_battle"], j, "连续战斗x10")
            frame = _wait_running(frame, j)
        elif state == "continuous_menu":
            frame = _tap(frame, COORD["menu_cairos"], j, "菜单选卡伊洛斯")
        elif state == "cont_running":
            j.log(state=state, note="已在连续战斗中")
            frame = _wait_running(frame, j)
        elif state == "cont_result":
            return "done"
        elif state in ("rune_popup", "victory", "victory_actions"):
            # 单局兜底路径（万一进了普通战斗）
            if state == "rune_popup":
                cx = find_close_x(frame)
                frame = _tap(frame, cx[0] if cx else COORD["rune_close"], j, "关闭符文")
            elif state == "victory":
                frame = _tap(frame, (720, 390), j, "开箱")
            else:
                return "done"
        else:  # battle 或未知
            cx = find_close_x(frame)
            if cx:
                frame = _tap(frame, cx[0], j, "close popup")
            else:
                j.log(state=state, note="未知画面，等待")
                time.sleep(RUN_POLL)
                frame = capture_frame()
    return "stuck"


def run(j: Journal, cycles: int = 1, repeat: bool = True) -> dict:
    """跑 cycles 轮，每轮=一次连续战斗(10局)。"""
    done = 0
    for i in range(cycles):
        res = run_cycle(j)
        j.log(action="cycle", note=f"{i+1}/{cycles} -> {res}")
        if res != "done":
            return {"result": res, "cycles": done}
        done += 1
        if repeat and i < cycles - 1:
            frame = capture_frame()
            st, _, _ = detect_state(frame)
            if st == "cont_result":
                frame = _tap(frame, COORD["result_again"], j, "再来一次")
    return {"result": "done", "cycles": done}
