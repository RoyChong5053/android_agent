"""拉莫遗址(次元·哈勒普)5 阶段傻瓜刷经验脚本。

前置：玩家手动打完第一轮，处理掉一次性 popup（领袖技能 / 探索战斗等）。
之后脚本从胜利结算开始接管，纯模板匹配 + 定时点击，循环：

    奖励(胜利结算) --点两下推进开箱--> 再来一次 --点击--> 下一局

兜底识别：是(弹窗) / 确认(掉落) / 战斗开始(遗址详情) / 开始战斗(队伍选择)。

用法（任意目录均可，脚本会自动定位项目根）：
    python3 core/skills/lamo_ruins.py --rounds 0       # 无限刷
    python3 core/skills/lamo_ruins.py --rounds 20      # 刷 20 局
    python3 core/skills/lamo_ruins.py --dry-run        # 只识别不点击
"""
import argparse
import os
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.action.adb_wrapper import tap
from core.perception.capture import capture_frame
from core.utils.logger import Journal

TEMPLATE_DIR = str(ROOT / "data" / "templates" / "lamo")

# 优先级从上到下：弹窗 overlay 必须最先处理
CHECKS = [
    ("popup_yes", 0.85),      # 是：领袖技能 / 探索战斗等确认弹窗
    ("confirm", 0.85),        # 确认：掉落奖励弹窗
    ("again", 0.85),          # 再来一次
    ("battle_start", 0.85),   # 战斗开始：遗址详情弹窗
    ("start_battle", 0.85),   # 开始战斗：队伍选择
    ("reward_title", 0.85),   # 奖励：胜利结算画面（无按钮，点屏幕推进）
]

REWARD_ADVANCE_TAPS = [(720, 500), (720, 370)]

POLL = 1.5
SETTLE = 1.0


def load_templates() -> dict:
    tpls = {}
    for name, _ in CHECKS:
        path = os.path.join(TEMPLATE_DIR, name + ".png")
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            raise FileNotFoundError(f"缺少模板: {path}")
        tpls[name] = img
    return tpls


def locate(frame, tpls: dict):
    """返回 (模板名, 点击中心坐标, 相似度)，全不中返回 (None, None, 0)。"""
    for name, thresh in CHECKS:
        tpl = tpls[name]
        res = cv2.matchTemplate(frame.gray, tpl, cv2.TM_CCOEFF_NORMED)
        _, mx, _, loc = cv2.minMaxLoc(res)
        if mx >= thresh:
            h, w = tpl.shape[:2]
            return name, (loc[0] + w // 2, loc[1] + h // 2), float(mx)
    return None, None, 0.0


def run(j: Journal, rounds: int = 0, poll: float = POLL, dry_run: bool = False) -> int:
    tpls = load_templates()
    done = 0
    while rounds == 0 or done < rounds:
        frame = capture_frame()
        name, xy, score = locate(frame, tpls)

        if name is None:
            j.log(state="battle_or_unknown", note="无匹配，等待")
            time.sleep(poll)
            continue

        if name == "reward_title":
            if not dry_run:
                for x, y in REWARD_ADVANCE_TAPS:
                    tap(x, y)
                    time.sleep(SETTLE)
            j.log(action="推进胜利结算", ok=not dry_run, note=f"score={score:.2f}")
        else:
            if not dry_run:
                tap(*xy)
                time.sleep(SETTLE)
            j.log(action=f"点击 {name}", x=xy[0], y=xy[1], ok=not dry_run,
                  note=f"score={score:.2f}")
            if name == "again":
                done += 1
                j.log(action="完成一局", note=f"累计 {done}")

        time.sleep(poll)

    return done


def main():
    ap = argparse.ArgumentParser(description="拉莫遗址 5 阶段傻瓜刷经验")
    ap.add_argument("--rounds", type=int, default=0, help="刷多少局，0=无限")
    ap.add_argument("--poll", type=float, default=POLL, help="识别间隔秒")
    ap.add_argument("--dry-run", action="store_true", help="只识别不点击")
    args = ap.parse_args()

    with Journal(root=str(ROOT / "data" / "journal")) as j:
        print(f"journal: {j.path}")
        t0 = time.time()
        done = run(j, rounds=args.rounds, poll=args.poll, dry_run=args.dry_run)
        print(f"完成 {done} 局  总用时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
