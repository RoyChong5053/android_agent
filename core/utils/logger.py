"""运行日志：JSONL 逐步落盘。

用途：
- 回放调试（哪一步、什么状态、点了哪里、成没成）
- 未来 YOLO 训练集来源（把关键帧另存到 data/journal/frames/）
"""
import json
import os
import time
from datetime import datetime


class Journal:
    def __init__(self, root: str = "data/journal", frames: bool = True):
        self.dir = root
        self.frames_dir = os.path.join(root, "frames")
        self.frames = frames
        os.makedirs(self.frames_dir, exist_ok=True)
        self.path = os.path.join(root, f"run_{datetime.now():%Y%m%d_%H%M%S}.jsonl")
        self._fh = open(self.path, "a", encoding="utf-8")
        self.t0 = time.time()

    def save_frame(self, frame, tag: str) -> str | None:
        if not self.frames:
            return None
        name = f"{time.time():.3f}_{tag}.png".replace(".", "_", 1)
        return frame.save(os.path.join(self.frames_dir, name))

    def log(self, *, state: str = "", action: str = "", x=None, y=None,
            ok=None, note: str = "", frame_path: str | None = None, **extra):
        rec = {
            "t": round(time.time() - self.t0, 3),
            "wall": datetime.now().isoformat(timespec="seconds"),
            "state": state,
            "action": action,
            "x": x,
            "y": y,
            "ok": ok,
            "note": note,
        }
        if frame_path:
            rec["frame"] = frame_path
        if extra:
            rec.update(extra)
        self._fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self):
        self._fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
