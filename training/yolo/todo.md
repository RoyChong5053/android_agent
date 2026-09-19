# YOLO 数据筹备 - 任务进度

> 目标：训练5类GUI元素检测模型，作为模板匹配的兜底增强。
> 日期：2026-09-17

## 数据现状

| 类别 | 图片数 | 标注数 | 状态 |
|---|---|---|---|
| lobby | 200 | 200 | ✅ 完成 |
| energy_bar | 150 | 150 | ✅ 完成 |
| popup | 3 | 3 | 🟡 种子数据 |
| result | 1 | 1 | 🟡 种子数据 |
| victory | 2 | 2 | 🟡 种子数据 |

**总计**: 356图片 + 356标注

## 进度

### 阶段一：基础设施 ✅
- [x] 创建yolo/目录结构
- [x] todo.md / auto_label.py
- [x] smart_capture.py（adb截图→detect_state分类）
- [x] auto_label.py（自动生成整图标注）
- [x] vl_auto_capture.py（adb截图→VL解析→ComfyUI式归档png+md）

### 阶段二：数据采集 🟡
- [x] lobby × 200
- [x] energy_bar × 150
- [x] 种子数据：popup×3, result×1, victory×2（来自data/screens/）
- [ ] 边玩边采：运行vl_auto_capture.py，VL自动解析并归档到yolo/data/vl_raw/

### 阶段三：数据准备
- [ ] 标注抽样校验
- [ ] train/val/test 分割 (70/15/15)
- [ ] yolo.yaml（已有基础版，待更新）

### 阶段四：训练
- [ ] 安装 ultralytics
- [ ] yolov8n 训练（100 epochs, imgsz=640）
- [ ] 评估 mAP@0.5

### 阶段五：集成
- [ ] YOLO 推理测试
- [ ] 集成到 detect_state 作为兜底增强
- [ ] 对比：纯模板匹配 vs 模板+YOLO

## 命令速查

```bash
# VL自动采集（边玩边采，主力方案）
python yolo/scripts/vl_auto_capture.py                     # 采集一次
python yolo/scripts/vl_auto_capture.py --loop --interval 30  # 每30秒采一次
python yolo/scripts/vl_auto_capture.py -c popup,result,victory  # 只采特定类别

# 智能采集（detect_state分类）
python yolo/scripts/smart_capture.py --categories popup --target 20

# 自动标注
python yolo/scripts/auto_label.py

# 标注校验（待创建）
python yolo/scripts/verify_labels.py --sample 5
```

---
*最后更新：2026-09-17*
