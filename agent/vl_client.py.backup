"""VL客户端：llama.cpp OpenAI兼容接口"""
import base64
import io
import json
import time
import urllib.request

from PIL import Image

SERVER = "http://127.0.0.1:12888/v1/chat/completions"
MODEL = "Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"

# 实测：768宽 JPEG70 + max_tokens=1024 + 短JSON prompt ≈ 13s/次
# 必须带“直接回答不要推理过程”，否则光推理就占满tokens导致content为空
MAX_W = 768


def _img_to_b64(png_bytes: bytes) -> tuple[str, tuple[int, int]]:
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    orig = im.size
    im.thumbnail((MAX_W, MAX_W))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=70)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return b64, orig  # orig=(w,h) 用于坐标反算


def ask(prompt: str, png_bytes: bytes, max_tokens: int = 1024) -> tuple[str, float]:
    b64, _ = _img_to_b64(png_bytes)
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": 0.1,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": "直接回答不要推理过程。" + prompt},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
            ],
        }],
    }
    req = urllib.request.Request(
        SERVER, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    dt = time.time() - t0
    return data["choices"][0]["message"].get("content", ""), dt


def classify_screen(png_bytes: bytes) -> tuple[str, float]:
    content, dt = ask(
        '这是什么游戏界面？只输出JSON：{"screen":"<英文ID>","game":"summoners_war"}',
        png_bytes,
    )
    return content, dt


def ground(prompt_target: str, png_bytes: bytes) -> tuple[dict, tuple[int, int], float]:
    """返回归一化坐标 {"x":0-1000,"y":0-1000} + 原图尺寸"""
    b64, orig = _img_to_b64(png_bytes)
    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "temperature": 0.1,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text",
                 "text": f"直接回答不要推理过程。找到[{prompt_target}]的中心点，只输出JSON：{{\"x\":<0-1000整数>,\"y\":<0-1000整数>}}"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
            ],
        }],
    }
    req = urllib.request.Request(
        SERVER, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    import time as _t
    t0 = _t.time()
    with urllib.request.urlopen(req, timeout=300) as resp:
        data = json.loads(resp.read())
    dt = _t.time() - t0
    raw = data["choices"][0]["message"].get("content", "")
    try:
        # 容错：截取首个 {...}
        s, e = raw.index("{"), raw.rindex("}") + 1
        coord = json.loads(raw[s:e])
    except Exception:
        coord = {"raw": raw}
    return coord, orig, dt
