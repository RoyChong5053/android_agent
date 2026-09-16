"""预览图：把全分辨率截图降采样成小 JPEG，供 LLM 读图用。

坑：直接 read 1440x720 原始 PNG（0.5-2.2MB）会把请求体撑爆，
DeepSeek 返回 413 Payload Too Large 并触发上下文压缩。
小图 720宽 q60 ≈ 60KB，小 20-30 倍。
"""
import io
import sys

from PIL import Image

PREVIEW_W = 720
PREVIEW_Q = 60


def make_preview(png_bytes: bytes, outp: str,
                 max_w: int = PREVIEW_W, quality: int = PREVIEW_Q) -> str:
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(outp, format="JPEG", quality=quality, optimize=True)
    return outp


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, "rb") as f:
        make_preview(f.read(), dst)
    print(dst)
