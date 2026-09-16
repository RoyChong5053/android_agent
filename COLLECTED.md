# 实测讯息收集（2026-09-16）

## 设备
- LGV35（adb id `LGV35fd728cd2`），USB 已连
- `wm size`：override 720x1440，物理 1440x2880
- 横屏游戏时 `screencap` 输出 **1440x720**
- **坐标映射已验证**：截图像素坐标 == `adb shell input tap` 坐标，可直接用
- scrcpy server 4.1 运行中

## 本地模型（llama.cpp :12888，可选，默认不进主循环）
- 模型：Gemma4-26B-A4B-QAT Q4_K_M，multimodal
- 接口：OpenAI 兼容 `/v1/chat/completions`
- 图片预处理：最长边 768 + JPEG70（b64 约 87KB）
- 实测延迟：分类 ~13s，grounding ~17s → 只适合每局 0-2 次低频调用
- prompt 必须加“直接回答不要推理过程”+ max_tokens=1024 + temperature 0.1，
  否则推理占满 tokens 导致 content 为空
- grounding 只能粗定位（偏差 ~60px）；固定 UI 用模板/Hough 更准更快

## 关键坑
- **勿把原图喂 LLM**：1440x720 PNG 单张 0.5~2.2MB，连读十几张触发 API 413
  并引发上下文压缩。统一用 `Frame.small_jpeg()`（~50KB）。
- **帧差验证不可靠**：大厅有动画，`changed()` 恒真 → 假成功。关键转移用 `detect_state` 复核。
- **Hough 找 X 按钮会误报**：正常画面也检测到圆。改用 X 按钮模板匹配 + 阈值 0.85。
- **模板要裁“固定文本”**：按钮上的价格/次数会变，别把数字裁进模板。
- **检测顺序=优先级**：结果页也含“进行次数”，`cont_result` 必须排在 `cont_running` 前。

## 内置「连续战斗」（MVP 核心）
- 队伍选择(连续战斗版) 按钮为 `8 ×10 连续战斗`，一次开 **10 局**，自动领奖
- 运行中画面：`进行次数 x/10` + 小窗预览 + `结束连续战斗`
- 结束画面：`连续战斗结果 10/10次` + `选择地区` / `再来一次`
- 一轮 ×10 实测约 13~14 分钟；期间可挂机关屏（PC 不必参与）

## 关键坐标（1440x720 实测）
| 元素 | 坐标 |
|---|---|
| 大厅·战斗 | (780, 655) |
| 冒险地图·卡伊洛斯地下城 | (720, 670) |
| 卡伊洛斯·巨人B9 战斗 | (1180, 250) |
| 队伍选择·连续战斗 | (1222, 565) |
| 连续战斗结果·再来一次 | (760, 616) |
| 连续战斗结果·选择地区 | (250, 616) |
| 连续战斗菜单·卡伊洛斯 | (1080, 360) |
| 符文弹窗·X（单局兜底） | (968, 196) |

## 代码
- `capture.py` Frame 采集/解码一次/小图 · `state.py` 帧差
- `actions.py` tap/swipe/换算 · `detectors.py` 模板/颜色/Hough 原语
- `screens.py` detect_state + 模板定义 · `popups.py` 通用关弹窗
- `journal.py` JSONL 日志 · `probe.py` 受控探查
- `run.py` CLI · `skills/giant_b9.py` 连续战斗刷本
- 旧原型：`loop.py` / `wait_static.py`（已弃用）
