"""等待战斗结束：轮询截图，画面连续静止且非战斗UI则认为是结算画面"""
import sys
import time

sys.path.insert(0, "/home/roychong/workspace/mycode/android_agent")

from core.perception.capture import capture_png_bytes
from core.brain.state import is_still, to_gray


def wait_static(max_wait=300, poll=4.0, need=2, out="/tmp/opencode/end.png"):
    prev = None
    still_count = 0
    t0 = time.time()
    while time.time() - t0 < max_wait:
        png = capture_png_bytes()
        gray = to_gray(png)
        s = is_still(prev, gray)
        prev = gray
        still_count = still_count + 1 if s else 0
        print(f"t={int(time.time()-t0)}s still={s} streak={still_count}", flush=True)
        if still_count >= need:
            with open(out, "wb") as f:
                f.write(png)
            print("SAVED", out)
            return out
        time.sleep(poll)
    print("timeout")
    return None


if __name__ == "__main__":
    wait_static()
