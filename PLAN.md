# Android Agent 挂机自动化 - 计划大纲

> 目标：以半弃坑游戏（魔灵召唤）为试验场，练手通用 GUI Agent 框架。
> 心态：不追求极品符文，追求感知-决策-执行闭环 + 可复用架构。
> 日期：2026-09-16

## 1. 整体架构

```
[安卓手机] --adb--> [scrcpy Server] --视频流--> [PC 本地层]
                                                  |
                                         [YOLO 高频哨兵 10-30fps]
                                                  |
                                         [本地VL 低频参谋 7B量化]
                                                  |
                                         [MCP Server 语义接口]
                                                  |
                                         [云端主模型 慢决策]
                                                  |
                                         [触屏模拟层 -> scrcpy control]
```

原则：
- 本地快循环（毫秒级）：看到 / 点到
- 云端慢循环（分钟级）：怎么玩
- YOLO 负责“看到”，VL 负责“看懂”，规则负责“动手”

## 2. 感知层

### 2.1 画面获取（3选1，推荐1）
1. scrcpy raw video stream / --v4l2：低延迟，推荐锁定版本
2. minicap（STF拆出）：灵活但需集成
3. adb exec-out screencap -p：延迟100-300ms，调试够用，生产不够跟手

坑：scrcpy画面坐标 != 设备真实坐标，需按 max_size / DPI 换算。

### 2.2 静止检测（零成本过滤器）
- OpenCV 帧差：`absdiff(prev, gray).mean() < 2.0` 判静止
- 战斗中画面在动，直接跳过VL，过滤80%无效调用
- MVP阶段可替代YOLO，先跑通链路

### 2.3 YOLO 哨兵（高频事件检测）
- 模型：yolov8n / yolov8s 即可，游戏UI固定，300-500张可用，1000张很稳
- 职责：回答“现在是不是某个特定状态”，不做语义理解
- 延迟预算：<50ms/帧，CPU ONNX 15-30ms
- 检测目标示例：battle_end, victory/defeat, replay_button, energy_low, rune_drop, confirm_dialog
- 大部分固定按钮：YOLO命中直接点，不经VL

### 2.4 本地VL 参谋（低频语义）
- 模型：Qwen2.5-VL-3B / InternVL2-2B 起步，7B为上限，量化部署
- 职责：符文词条值不值得留、非常见弹窗内容、异常卡住判断、商店价值
- 频率：每局0-2次，异步线程，不阻塞主循环
- 优化：ROI裁剪（只给符文区）、降分辨率448、prompt极简（是/否）、相同画面hash缓存、超时规则兜底

### 2.5 备选：logcat 状态判断
- 命令：`adb logcat -c && adb logcat | grep -i "com2us\|summoners"`
- 商业游戏大概率不吐战斗事件，只能做辅助信号（Activity切换、网络断开）
- 定位：主力仍是视觉，logs做兜底

## 3. 执行层（触屏模拟）

1. 最隐蔽：scrcpy control socket，`INJECT_TOUCH_EVENT`，等价真实MotionEvent
2. 备选：minitouch，直接写 /dev/input/eventX，支持多指/滑动，文档较全
3. 最差：adb shell input tap，一眼假，仅调试用

要点：
- VL只输出归一化坐标 `{"x":0-1000,"y":0-1000}`，执行层做换算：
  `device_x = vl_x/1000*device_w`
- 必须加噪声：坐标±3px，点击间隔150-400ms高斯分布
- 加疲劳模拟：每N局停几分钟
- 多指/滑动需读scrcpy源码或用minitouch
- 点完截图验证，未变化则重试

反检测认知：物理点击仍算第三方自动化，行为模式（24h在线、毫秒级规律）仍可被抓。小号+随机化是必须。

## 4. 中间层：MCP Server（核心）

### 4.1 设计原则
- 不要暴露 `click(x,y)/screenshot()` 原子操作给云端，会导致几十个tool call + context爆炸
- 暴露语义级Skill：本地折叠100步点击，云端只看1条总结
- 本地VL无长记忆，每次单图问答，问完即忘
- 返回差分+摘要JSON，不是全量状态

### 4.2 状态ID表（先定4个MVP，再扩到20个）
MVP（龙B10单循环）：
- battle / end / replay / popup_generic

扩展：
- lobby, dungeon_select, dragon_b10_battle/end, tower_battle/end, weekly_battle/end
- rune_storage, rune_detail, energy_empty, network_error

判别技巧：每个画面1-2个绝不重复的UI锚点（龙头图标、层数数字），YOLO见锚点即知画面。

### 4.3 MCP 工具草案（6-8个）
1. `get_state()` -> `{"screen":"dragon_b10_end","energy":88,"can_replay":true}`
2. `run_dungeon(id, times, filter)` -> 本地闭环刷N局，一次汇报
3. `analyze_runes(limit)` -> 仓库扫描压缩表
4. `powerup_rune(id)` -> 强化+汇报歪没歪
5. `handle_popup()` -> 清弹窗
6. `analyze_account()` -> 等级/体力/胜率/建议

返回示例：
```json
{
  "event": "dungeon_done",
  "delta": {"energy": -8, "rune_kept": 1},
  "rune": {"slot": 2, "main": "速度", "subs": ["暴击","攻击%"], "score": 8.5},
  "need_decision": false
}
```
仅 `need_decision=true` 才上升云端（极品符文赌不赌、体力吃不吃石头）。

### 4.4 Token预算
- 差做法：3000 tokens/图 x 50步 = 150k/局
- 好做法：本地100步折叠 -> 云端300 tokens/次，一晚几十行搞定

## 5. 云端大脑

- 只收文字状态，做长线规划：刷龙还是刷塔，先强化还是先刷体
- 事件流示例：`10:00 dragon x10开始 -> 10:32完成留1 -> 体力<10吃石头还是转塔？`
- 半自动先行（人定目标，云端调度+异常处理），全自动（记忆库+目标系统）后置

## 6. YOLO训练速查

- 采集：300-500张，覆盖分辨率/结算/弹窗/遮挡/卡顿
- 标注：labelImg / X-AnyLabeling，6-10类，输出 `class cx cy w h`
- 训练：`yolo detect train model=yolov8n.pt data=summoners.yaml epochs=100 imgsz=640 batch=16`
- 增强：默认hsv/flip/mosaic，防止过拟合到单机
- 评估：mAP50>0.9轻松，重点看小目标（X按钮、体力条），必要imgsz=960
- 部署：`yolo export model=best.pt format=onnx` + ONNX Runtime

VRAM（640/batch16/AMP）：
- n: 3-4G，s: 5-6G，m: 8-10G，l/x: 12-24G（不需要）
- 4G卡：n + batch8 + imgsz512 ≈2.5G可训
- 推理CPU即可，与7B VL（量化~5G）共存，8G卡刚好，12G舒服

进阶：挂机跑一周，VL判对的图自动存为YOLO训练集，越跑越准。

## 7. 路线图

- 阶段1 MVP：VL轮询 + 静止检测 + 规则引擎 + adb tap，跑通龙B10单循环
- 阶段2 补强：YOLO替换高频检测，VL只做符文/弹窗，切换scrcpy control
- 阶段3 生产级：行为随机化、多开、日志监控、录制回放、配置化换游戏

通用化目标：
- 游戏规则 -> 配置文件
- 视觉检测 -> 插件接口（模板/YOLO/VL可换）
- 动作执行 -> 驱动层（adb/scrcpy/minitouch可切）

## 8. 待确认

1. 本地显卡型号 -> 定YOLO batch/imgsz + VL 3B还是7B
2. 状态粒度 -> 先4个MVP还是直接20个全套
3. 未知画面策略 -> 本地VL兜底猜 vs 冻结上报人工处理
4. 半自动 vs 全自动 -> 建议先半自动验证 `get_state + run_dungeon`

---

## 9. 实施进展与修订（2026-09-16 实施）

### 9.1 重大修订：改用游戏内置「连续战斗」
原计划是「每局手动驱动」（lobby→选本→开打→等3分钟→结算→再来一次），
实施中发现游戏自带 **连续战斗**：一次开 **10 局**，自动打、自动领奖，
结束后出现「选择地区 / 再来一次」。于是 MVP 简化为：

```
战斗 → 卡伊洛斯地下城 → 巨人B9 → [连续战斗 x10] --自动10局--> 连续战斗结果
        --再来一次--> 队伍选择(连续) --> [连续战斗 x10] --> ... 循环
```

- 手机端一轮 ×10 实测约 **13~14 分钟**，全程无需 PC 参与（PC 只负责按两个按钮）。
- 符文/奖励由游戏自动入包，天然满足「先全部保留」。
- 「再来一次」会回到**队伍选择(连续战斗版)**再点一次「连续战斗」，不是直接开打——已处理。

### 9.2 技术选型落地
- **识别=模板匹配**（`cv2.matchTemplate` TM_CCOEFF_NORMED），固定分辨率 1440x720，
  毫秒级、无需训练。离线 11/11 用例全过。YOLO/VL 暂不进主循环。
- **检测顺序即优先级**：叠加层（符文弹窗）> 结果页 > 运行页 > 基础页。
  踩坑：结果页也含“进行次数”，必须排 `cont_result` 在 `cont_running` 之前。
- **验证用状态而非帧差**：大厅有动画，帧差恒真会误判成功。
- **采集一次解码一次**：`Frame` 共享 `bgr/gray`；给 LLM 一律用 `small_jpeg`（~50KB）。
- **X 按钮用模板匹配**，弃用 Hough 圆（正常画面会误报）。

### 9.3 已实现状态（11 个）
lobby / battle_map / cairos_select / team_select / continuous_menu /
cont_running / cont_result / victory / rune_popup / victory_actions / battle(兜底)

新增状态只需在 `agent/screens.py` 的 `TEMPLATE_SPECS`（截图+裁剪框）与 `ANCHORS`
（优先级+ROI+阈值）登记，再 `python3 -m agent.screens` 重建模板。

### 9.4 已知限制
- 体力不足时「再来一次」的行为未验证（可能弹充值框）→ 编排器需处理。
- 符文弹窗在连续战斗模式下不出现；单局模式才需要 `victory/rune_popup` 路径（已有兜底）。
- 坐标仍是硬编码；换分辨率/换设备需重做锚点。
- 未做行为随机化/反检测（当前用 `adb input tap`）。

## 10. 后续路线图（修订）

- **P0 编排器**：优先级队列 `巨人B9 → 竞技场 → 工会 → …`，逐一耗尽其资源；
  全部耗尽→用石头充值体力续刷；`--max-cycles/--dry-run`、卡住即停并告警。
  需要新增：资源(体力/券/剑)读数、arena/guild 的 skill 与锚点。
- **P1 符文评分器**：主属性+副属性打分 → keep/sell；先纯规则，未知再上 VL。
- **P2 内容 skill 扩充**：arena / guild / 试炼之塔 / 异界，逐个探查登记锚点。
- **P3 异常兜底**：未知画面冻结、存图、上报；重试上限。
- **P4 执行层**：scrcpy control socket（INJECT_TOUCH_EVENT）取代 `adb input tap`。
- **P5 低频语义**：VL 做符文估值/异常判断；YOLO 做小目标鲁棒性升级（暂不需要）。
- **P6 MCP**：暴露 `get_state` / `run_dungeon` 语义接口 + 云端大脑（只收文字状态）。

