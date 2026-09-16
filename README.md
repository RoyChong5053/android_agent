# android_agent

以《魔灵召唤》(Summoners War) 为试验场的**安卓游戏挂机自动化 Agent**。

目标不是刷出极品装备，而是练手一套通用的 **感知 → 决策 → 执行** 闭环：
截屏识别画面 → 规则引擎决策 → adb 模拟点击 → 再验证，做成可复用的 GUI Agent 框架。

## 现状（2026-09-16）

- ✅ 全链路打通：截图 → 模板匹配识别 → 点击 → 状态验证
- ✅ 状态识别 **11/11** 离线用例通过（毫秒级，纯 OpenCV，无需训练）
- ✅ 基于游戏内置「**连续战斗**」实现全自动刷本：
  `战斗 → 卡伊洛斯地下城 → 巨人 B9 → 连续战斗 ×10`，
  游戏自动打 10 局并自动领奖，结束后 Agent 自动「再来一次」循环
- ✅ 运行日志落盘（JSONL），可回放、可作未来训练集
- ⏳ 待做：内容编排器（体力刷完转竞技场/工会→最后才充值）、符文评分

> 实测一轮「连续战斗 ×10」约 13~14 分钟，全程无需人工干预。

## 架构

```
[编排器 orchestrator]  按优先级轮转内容，管理资源(体力/券/剑)与充值   ← 待做
        │
   [各内容 skill]      giant_b9 / arena / guild ...（各自状态机）
        │
   [感知 screens+popups] detect_state（模板匹配）+ 通用弹窗关闭
        │
   [执行 capture/actions] Frame 采集(解码一次) + tap（带抖动）
        │
   [journal]            每步落盘 JSONL
```

关键设计决策：
- **模板匹配优先**，不引入 YOLO/VL 进主循环。分辨率固定(1440x720)、UI 固定，
  传统 CV 就够快够准；YOLO/VL 留给「未知画面兜底 / 符文估值」等低频语义场景。
- **叠加层优先**：检测顺序即优先级。例如符文弹窗盖在“胜利”页上，必须先判符文弹窗。
- **一次采集，解码一次**：`Frame` 共享 `bgr/gray`，多个检测器不重复 `imdecode`。
- **验证靠状态，不靠帧差**：大厅等画面有动画，帧差会误判；关键转移用 `detect_state` 复核。
- **感知/执行可替换**：`detectors.py` 是原语层，`skills/` 只依赖 `detect_state` 与 `tap`。

## 目录结构

```
agent/
  capture.py     Frame 采集：adb screencap → 解码一次，产出预览小图
  state.py       帧差：changed / is_still
  actions.py     tap / swipe / 坐标换算（带人类化抖动）
  detectors.py   检测原语：模板匹配 / 颜色块 / Hough圆
  screens.py     TEMPLATE_SPECS + ANCHORS -> detect_state()，可 build_templates()
  popups.py      通用弹窗关闭（X 按钮模板匹配）
  journal.py     JSONL 运行日志
  probe.py       受控探查（点一下→截图→打印状态），用于探索未知画面
  run.py         CLI 入口
  skills/
    giant_b9.py  巨人地下城 B9 连续战斗刷本
  vl_client.py   本地 VL 客户端（llama.cpp，可选，默认不进主循环）
  loop.py        早期原型（静止检测+VL兜底），已弃用
  wait_static.py 早期原型，已弃用
data/
  screens/       参考截图（裁剪模板的来源）
  templates/     识别用锚点模板（由 build_templates 生成）
  journal/       运行日志
```

## 环境要求

- Linux + `adb`（设备已连接并授权）
- Python 3，依赖见 `requirements.txt`（`opencv-python` / `Pillow` / `numpy`）
- 可选：`llama.cpp` 本地多模态模型（`vl_client.py`，仅在需要语义判断时使用）

```bash
pip install -r requirements.txt        # 若用系统 Python 受 PEP668 限制，加 --break-system-packages
```

设备常量在 `agent/capture.py` 的 `DEVICE`，改成你的 `adb devices` 序列号。

## 使用

```bash
# 生成/更新锚点模板（首次或改了 screens.py 的 TEMPLATE_SPECS 后）
python3 -m agent.screens

# 探查当前画面状态（附加坐标 = 先点一下再识别）
python3 -m agent.probe
python3 -m agent.probe 1180 250 2.5 b9_battle

# 连续战斗刷本：2 轮（每轮 10 局，自动再来一次）
python3 -m agent.run --cycles 2
python3 -m agent.run --cycles 1 --no-repeat    # 只跑一轮
```

## 画面状态（detect_state 输出）

| state | 含义 | 锚点 |
|---|---|---|
| `lobby` | 主界面 | 底部导航栏 |
| `battle_map` | 冒险地图 | 重置按钮 |
| `cairos_select` | 卡伊洛斯地下城选择 | 左侧“巨人地下城”页签 |
| `team_select` | 队伍选择（普通/连续战斗两种） | 开始战斗 / 连续战斗按钮 |
| `continuous_menu` | 连续战斗-选择地区面板 | 面板标题 |
| `cont_running` | 连续战斗中（自动 10 局） | “进行次数”标签 |
| `cont_result` | 连续战斗结果（含“再来一次”） | “连续战斗结果”标题 |
| `victory` | 单局胜利结算 | “胜利”标题 |
| `rune_popup` | 符文获得弹窗 | “强化”按钮 |
| `victory_actions` | 结算后操作（再来一次/下一层） | “再来一次”按钮 |
| `battle` | 兜底（战斗动画中/未识别） | 无 |

新增锚点：在 `screens.py` 的 `TEMPLATE_SPECS` 里用「参考截图 + 裁剪框」定义，
再在 `ANCHORS` 里按优先级登记即可，`build_templates()` 会自动裁剪生成模板。

## 踩过的坑

- **别把全分辨率截图喂给 LLM**：单张 1440x720 PNG 有 0.5~2.2MB，连续读十几张会把
  API 请求体撑爆（413 Payload Too Large）并触发上下文压缩。
  统一用 `Frame.small_jpeg()`（720 宽 JPEG，约 50KB）。
- **帧差验证不可靠**：大厅有动画，`changed()` 恒为真，会产生“点成功了”的假象。
  关键操作改用 `detect_state` 复核。
- **Hough 圆检测 X 按钮不稳**：在正常画面会误报。改用 X 按钮模板匹配 + 高阈值。
- **模板裁剪要挑“固定文本”**：按钮上的价格/次数会变，模板要裁不含变化数字的部分。
- **检测顺序=优先级**：结果页也含“进行次数”，必须把 `cont_result` 排在 `cont_running` 前。
- 设备横屏时 `screencap` 输出为 1440x720，且**截图像素坐标 == `input tap` 坐标**，无需换算。

## 后续开发

见 `PLAN.md` 的第 9 节「实施进展与后续」。要点：
1. 编排器：体力刷完自动转竞技场/工会，全部耗尽才用石头充值续刷
2. 符文评分器（保留/出售决策，可先规则后 VL）
3. 更多内容 skill（arena / guild）：需要先探查并登记各自画面锚点
4. 异常兜底：未知画面冻结上报、卡住告警
5. 执行层升级：scrcpy control socket 取代 `adb input tap`

## 免责声明

仅供个人学习 GUI Agent 技术使用。游戏自动化可能违反服务条款，请自行评估风险，
建议使用小号。
