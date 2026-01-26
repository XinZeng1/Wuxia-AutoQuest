# 工具说明

## 探索度文本测试工具（推荐）

`test_exploration_text.py` - 截图并测试探索度文字识别，用于验证配置是否正确

### 使用方法

1. 确保游戏已经通过屏幕镜像投射到电脑
2. 确保 `config/config.yaml` 中的窗口配置正确
3. 运行工具：

```bash
python tools/test_exploration_text.py
```

### 功能

- ✅ 根据配置自动截取探索度文本区域
- ✅ 显示截图结果（带红色边框）
- ✅ 实时测试OCR识别
- ✅ 显示识别结果和解析的数值
- ✅ 可以调整配置并保存
- ✅ 可以保存截图用于调试

### 操作步骤

1. 工具会自动根据配置截取文本区域
2. 查看截图是否正确包含"探索度 XX%"文本
3. 查看OCR识别结果
4. 如果识别失败，点击"调整配置"修改区域坐标
5. 点击"重新测试"验证新配置

---

## 怪物检测测试工具

### test_monster_detection.py

测试基于模板匹配的怪物检测功能，验证模板和配置是否正确

#### 使用方法

```bash
python tools/test_monster_detection.py
```

#### 功能

- 检查怪物模板文件是否存在
- 测试截图功能
- 使用模板匹配检测怪物
- 显示检测到的怪物位置和置信度
- 保存标记图像（在截图上标记检测到的怪物位置）

#### 输出

- `test_monster_detection.png` - 原始截图
- `test_monster_detection_marked.png` - 标记了怪物位置的图像

### test_monster_name_detection.py

测试基于OCR识别怪物名称的检测功能（推荐使用）

#### 使用方法

```bash
python tools/test_monster_name_detection.py
```

#### 功能

- 使用OCR识别屏幕上的怪物名称
- 根据名称关键词匹配检测怪物
- 在截图上标记检测到的怪物位置
- 保存标记后的图像

#### 输出

- `test_monster_name_screenshot.png` - 原始截图
- `test_monster_name_marked.png` - 标记了怪物位置的图像

#### 配置

在 `config/config.yaml` 中配置：

```yaml
monster:
  detection_method: "name"  # 使用名称检测（推荐）
  name_keywords:
    - "白虎"
    - "兖州"
    - "大盗"
    - "巡查"
    - "堂主"
    - "党"
```

#### 优势

- ✅ 不需要准备模板图像
- ✅ 更准确，直接识别游戏显示的怪物名称
- ✅ 可以识别所有显示名称的怪物
- ✅ 不受怪物外观变化影响

### debug_monster_ocr.py

OCR文本识别调试工具，帮助查看所有识别到的文本并调整关键词配置。

#### 使用方法

```bash
python tools/debug_monster_ocr.py
```

#### 功能

- 显示所有OCR识别到的文本及其位置和置信度
- 尝试多种OCR配置（PSM模式）
- 标记匹配关键词的文本
- 生成预处理后的图像用于调试
- 提供配置建议

#### 输出

- `debug_ocr_screenshot.png` - 原始截图
- `debug_ocr_preprocessed.png` - 预处理后的图像
- `debug_ocr_marked.png` - 标记了所有识别文本的图像（红色=匹配关键词，黄色=其他）

#### 使用场景

如果 `test_monster_name_detection.py` 检测不到怪物或检测错误：

1. 运行此工具查看OCR识别到了哪些文本
2. 检查哪些文本应该是怪物名称但没有匹配关键词
3. 将怪物名称中的关键词添加到 `config/config.yaml` 的 `monster.name_keywords` 中
4. 重新测试

---

## 探索度文本定位工具

`locate_exploration_text.py` - 帮助用户定位探索度文本在屏幕上的位置（可视化选择）

### 使用方法

1. 确保游戏已经通过屏幕镜像投射到电脑
2. 确保 `config/config.yaml` 中的窗口配置正确
3. 运行工具：

```bash
python tools/locate_exploration_text.py
```

### 操作步骤

1. 工具会自动截取配置的窗口区域
2. 在截图上**按住鼠标左键并拖拽**，选择包含"探索度 XX%"文本的区域
3. 释放鼠标，确认选择
4. 点击"确认选择"按钮
5. 工具会显示选择的区域坐标
6. 点击"保存到配置文件"将坐标保存到 `config/config.yaml`

### 手动设置

如果不想使用工具，也可以手动设置：

1. 打开游戏，找到探索度文本的位置（如"探索度 36%"）
2. 记录文本区域的坐标：
   - 左边界（left）：文本区域左边距离窗口左边的像素数
   - 上边界（top）：文本区域上边距离窗口上边的像素数
   - 宽度（width）：文本区域的宽度
   - 高度（height）：文本区域的高度

3. 编辑 `config/config.yaml`，添加：

```yaml
exploration:
  text_region:
    left: 100    # 根据实际位置修改
    top: 50     # 根据实际位置修改
    width: 200  # 根据实际大小修改
    height: 50  # 根据实际大小修改
```

4. 或者在代码中设置：

```python
from src.exploration_tracking.exploration_tracker import ExplorationTracker

tracker = ExplorationTracker()
tracker.set_exploration_text_region(
    left=100,
    top=50,
    width=200,
    height=50
)
```

### 注意事项

- 选择区域时，尽量包含完整的文本，但不要包含太多无关内容
- 如果文本区域太小，OCR可能识别失败
- 如果文本区域太大，可能包含干扰信息
- 建议选择区域比实际文本稍大一些（多留10-20像素边距）
