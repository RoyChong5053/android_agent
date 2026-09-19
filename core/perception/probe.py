"""受控探查：点一下 -> 截图 -> 打印状态/小图。用于人工探索未知画面。"""
import sys
import time

from core.action.adb_wrapper import tap
from core.perception.capture import capture_frame
from core.perception.screens import detect_state


def probe(x: int | None = None, y: int | None = None, wait: float = 2.0, tag: str = "probe"):
    if x is not None:
        tap(x, y)
        time.sleep(wait)
    f = capture_frame()
    st, sc, c = detect_state(f, debug=True)
    out = f"/tmp/opencode/{tag}.jpg"
    open(out, "wb").write(f.small_jpeg())
    print(f"state={st} {sc:.2f} @ {c}  saved {out}")
    return f


if __name__ == "__main__":
    a = sys.argv[1:]
    if a:
        probe(int(a[0]), int(a[1]), float(a[2]) if len(a) > 2 else 2.0,
              a[3] if len(a) > 3 else "probe")
    else:
        probe()
