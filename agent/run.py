"""CLI 入口：连续战斗刷本。"""
import argparse
import time

from agent.journal import Journal
from agent.skills import giant_b9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycles", type=int, default=1, help="连续战斗轮数(每轮10局)")
    ap.add_argument("--no-repeat", action="store_true", help="只跑一轮，不按再来一次")
    args = ap.parse_args()

    with Journal() as j:
        print(f"journal: {j.path}")
        t0 = time.time()
        res = giant_b9.run(j, cycles=args.cycles, repeat=not args.no_repeat)
        print(f"结果 {res}  总用时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
