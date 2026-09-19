"""VL批量探查：截图 -> 本地llama.cpp(:12888) -> 结构化UI map JSON。

实测约束(2026-09-17)：
- server单slot串行，~25s/次，并行无加速，只能后台串行跑
- grounding偏差~60px：只让VL做「读数/分类/选行」，精确定位靠模板匹配
- prompt必须加“直接回答不要推理过程”，temperature 0.1

用法：
  python3 -m agent.vl_sweep data/screens/arena_list.png ... -o /tmp/uimap.json
  python3 -m agent.vl_sweep --watch   # 后台常驻：每N秒截图分类记journal(另起进程跑)
"""
import argparse
import base64
import io
import json
import sys
import time

from PIL import Image

from core.perception import vl_client

LIST_PROMPT = (
    "这张是魔灵召唤竞技场对手名单。从上到下逐行列出每个对手："
    "等级数字、名字、有无可点的[战斗]按钮（有=available，显示正在准备=unavailable）。"
    "再读左下角翅膀数（形如x/10）。"
    '只输出JSON：{"wings":"<如7/10>","opponents":'
    '[{"row":1,"level":50,"name":"<名字>","available":true}]}，row从上到下=1,2,3…'
)

DESCRIBE_PROMPT = (
    "这是什么游戏界面？列出所有可点击按钮（文字+大概位置，坐标0-1000），"
    "再读出关键数字（体力/翅膀/分数）。"
    '只输出JSON：{"screen":"<英文ID>","buttons":'
    '[{"text":"<按钮文字>","x":<0-1000>,"y":<0-1000>}],"readings":{}}'
)


def _strip_json(raw: str) -> dict:
    try:
        s, e = raw.index("{"), raw.rindex("}") + 1
        return json.loads(raw[s:e])
    except Exception:
        return {"raw": raw}


def parse_list(png_bytes: bytes) -> tuple[dict, float]:
    content, dt = vl_client.ask(LIST_PROMPT, png_bytes, max_tokens=1536)
    return _strip_json(content), dt


def describe(png_bytes: bytes) -> tuple[dict, float]:
    content, dt = vl_client.ask(DESCRIBE_PROMPT, png_bytes)
    return _strip_json(content), dt


def sweep(paths: list[str], mode: str = "describe") -> list[dict]:
    fn = parse_list if mode == "list" else describe
    out = []
    for p in paths:
        with open(p, "rb") as f:
            png = f.read()
        try:
            data, dt = fn(png)
            rec = {"file": p, "dt": round(dt, 1), **data}
        except Exception as e:  # noqa: BLE001  超时/解析失败都记下来继续
            rec = {"file": p, "error": str(e)}
        print(json.dumps(rec, ensure_ascii=False), flush=True)
        out.append(rec)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("-o", "--out", default="")
    ap.add_argument("--mode", choices=["describe", "list"], default="describe")
    args = ap.parse_args()
    if not args.files:
        print("用法: python3 -m agent.vl_sweep <png...> [--mode list] [-o out.json]")
        sys.exit(1)
    res = sweep(args.files, args.mode)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print(f"saved {args.out}")


if __name__ == "__main__":
    main()
