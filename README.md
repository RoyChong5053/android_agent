# Android Agent

ADB + OpenCV 的游戏辅助脚本集。**痛点驱动，脚本优先。**

## 开发大方向（最重要，先读这段）

> 一句话：**用简单的小脚本，逐个解决游戏里烦人的重复操作；全自动化以后再说。**

1. **脚本优先，痛点驱动**
   每遇到一个具体痛点（例如「拉莫遗址每局都要手点再来一次」），就写一个**独立的傻瓜脚本**：
   模板匹配 + 定时点击，能跑通、够用就行。不追求通用，不追求优雅。
2. **全自动化后置**
   等这些针对性小脚本成熟、稳定后，再考虑把它们串成端到端自动流程。
   `giant_b9.py` + `screens.py` 那套 anchor 状态机是**旧的探索方向**，保留作参考，但不再是当前重点。
3. **能模板就模板**
   固定 UI 一律 OpenCV 模板匹配（毫秒级、免训练），阈值 0.85。
   OCR / YOLO / 本地 VL 只在模板确实搞不定时再上（VL 只用来「读数/分类」，不用来定位）。
4. **一个脚本一个文件**
   放 `core/skills/`，配一份同名 `.md` 记录：痛点、流程、坐标、模板、踩过的坑。

## 现有脚本

| 脚本 | 解决的痛点 | 状态 |
| :--- | :--- | :--- |
| `core/skills/lamo_ruins.py` | 拉莫遗址(次元·哈勒普 5阶段)刷经验，每局手点「再来一次」 | ✅ 实跑验证（2 局全自动） |
| `core/skills/arena.py` | 竞技场刷翅膀（对手选最弱 + 单局循环 + 自愈） | ✅ |
| `core/skills/giant_b9.py` | 巨人地下城 B9（靠游戏内置「连续战斗」×10） | 旧状态机方案 |

## 目录结构

- `core/perception/`：视觉输入。截图（`capture.py`）、模板/颜色/Hough 原语（`detectors.py`）、状态机（`screens.py`）、关弹窗（`popups.py`）。
- `core/action/`：设备动作。`adb_wrapper.py` 的 `tap` / `swipe` / `tap_verified`。
- `core/skills/`：**各痛点脚本**（主要产出物）。
- `core/utils/logger.py`：`Journal` JSONL 逐步落盘。
- `data/templates/<脚本名>/`：该脚本用的模板。`data/journal/`：运行日志。
- `data/screens/`、`training/`、`models/`：旧探索（截图素材 / YOLO 管线），暂搁置。

## 运行

```bash
# 拉莫遗址刷经验（脚本自动定位项目根，任意目录可跑）
python3 core/skills/lamo_ruins.py --rounds 0     # 无限刷
python3 core/skills/lamo_ruins.py --rounds 20    # 刷 20 局
python3 core/skills/lamo_ruins.py --dry-run      # 只识别不点击
```

> 前置：先手动打完第一轮，处理掉一次性 popup（领袖技能 / 探索战斗等）；脚本从胜利结算接管。

## 设备（详见 COLLECTED.md）

- 设备 id `LGV35fd728cd2`；横屏 `screencap` 输出 **1440x720**。
- **截图像素坐标 == `adb shell input tap` 坐标**，可直接用。

## 远期参考（非当前重点）

- Phase A：脚本成熟后做编排器（体力耗尽自动切换、定时任务）。
- Phase B：OCR 读取动态文本（价格/次数）。
- Phase C：YOLO 处理形状多变的元素。
- Phase D：本地 VL 常驻 watcher（只做分类/读数）。
