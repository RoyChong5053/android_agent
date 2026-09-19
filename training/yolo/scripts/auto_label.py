"""自动生成YOLO标注（整图bounding box），并支持手动精修。"""
import os
import cv2

BASE_DIR = "/home/roychong/workspace/mycode/android_agent"
RAW_DIR = os.path.join(BASE_DIR, "yolo", "data", "raw")
LABELS_DIR = os.path.join(BASE_DIR, "yolo", "data", "labels")

# YOLO 类别 → ID
CLASS_TO_ID = {"lobby": 0, "energy_bar": 1, "popup": 2, "result": 3, "victory": 4}


def auto_label(category: str):
    """为指定类别的所有图片生成整图标注。"""
    img_dir = os.path.join(RAW_DIR, category)
    label_dir = os.path.join(LABELS_DIR, category)
    os.makedirs(label_dir, exist_ok=True)

    cls_id = CLASS_TO_ID[category]
    for fname in sorted(os.listdir(img_dir)):
        if not fname.endswith(".png"):
            continue
        img_path = os.path.join(img_dir, fname)
        img = cv2.imread(img_path)
        if img is None:
            print(f"  SKIP {fname} (decode failed)")
            continue
        h, w = img.shape[:2]
        # 整图 bounding box (归一化: x_center=0.5, y_center=0.5, w=1.0, h=1.0)
        label_txt = f"{cls_id} 0.500000 0.500000 1.000000 1.000000\n"
        label_path = os.path.join(label_dir, fname.replace(".png", ".txt"))
        with open(label_path, "w") as f:
            f.write(label_txt)
        print(f"  {fname} {w}x{h} → {label_path}")


if __name__ == "__main__":
    for cat in ["lobby", "energy_bar", "popup", "result", "victory"]:
        d = os.path.join(RAW_DIR, cat)
        if os.path.isdir(d):
            print(f"=== {cat} ===")
            auto_label(cat)
