# Agent Roles & Development Approach

## 开发方针（先读，最重要）

> **痛点驱动的小脚本优先，全自动化后置。**

- 遇到一个具体重复操作痛点 → 写一个**独立傻瓜脚本**（模板匹配 + 定时点击），跑通够用即可。
- 不追求通用/优雅；等小脚本成熟后再考虑整合成端到端自动流程。
- 固定 UI 一律 OpenCV 模板匹配，阈值 0.85；OCR/YOLO/VL 只在模板搞不定时再上。
- 每个脚本放 `core/skills/`，配同名 `.md`（痛点 / 流程 / 坐标 / 模板 / 坑）。
- 旧的 anchor 状态机（`screens.py` + `giant_b9.py`）保留作参考，不是当前重点。

## Agent Architecture（旧状态机方案，仍在用其感知/动作层）

| Role | Description | Current Implementation |
| :--- | :--- | :--- |
| **Perception** | Converts raw screen images into structured data (objects, text). | ADB screenshot capture + OpenCV template matching / color detection / Hough circles |
| **Brain** | Interprets perception to update game state and decide next action. | 傻瓜脚本用「优先级模板列表」代替；旧方案为 anchor 状态机 (`screens.py detect_state`) |
| **Action** | Translates decisions into physical ADB commands. | `tap`/`swipe` via ADB + frame-diff verification (`tap_verified`) |
| **Skills** | 解决具体痛点的独立脚本。 | `lamo_ruins.py`（拉莫刷经验）、`arena.py`（竞技场）、`giant_b9.py`（连续战斗，旧） |

## Development Principles

1. **Script First, Pain-Point Driven**: 一个痛点一个脚本，够用就好，全自动化后置。
2. **Template Matching First**: For fixed UI games, OpenCV template matching is more accurate and faster than YOLO, with zero training data required.
3. **Priority-Ordered Detection**: 弹窗 overlay 必须排在底层画面之前检测（`lamo_ruins.CHECKS` 即按优先级排列）。
4. **Dynamic ROI Extraction**: 模板只裁固定文本/背景，别把会变的数字裁进去（如价格/次数）。
5. **Coordinates Are Measured**: 坐标一律以实测为准，勿凭肉眼改（目测常偏 ~50px）。

## Future Integration Directions（远期，小脚本成熟后）

- **Phase A**: 编排器（体力耗尽切换、定时任务）。
- **Phase B**: OCR for text-based UI elements with variable positions.
- **Phase C**: YOLOv8n pipeline if shape-varied but category-fixed elements require detection.
- **Phase D**: 本地 VL 常驻 watcher（只做分类/读数，不做定位）。
