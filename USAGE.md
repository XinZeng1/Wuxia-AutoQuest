# 使用指南

## 快速开始

### 步骤1：安装依赖

```bash
pip install -r requirements.txt
```

**注意**：如果使用 `pytesseract`，还需要安装 Tesseract OCR：
- Windows: 下载安装 [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
- Mac: `brew install tesseract tesseract-lang`
- Linux: `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim`

### 步骤2：配置窗口区域

1. 启动屏幕镜像软件（如 Scrcpy、AirDroid 等）
2. 将游戏窗口投射到电脑屏幕
3. 记录游戏窗口的位置和大小
4. 编辑 `config/config.yaml`，设置 `window` 配置项

### 步骤3：准备模板图像

从游戏中截图以下元素，保存到 `templates/` 目录：

1. **怪物图标** (`monster.png`)
   - 截取一个典型的怪物图标
   - 建议大小：50x50 到 100x100 像素
   - 确保图标清晰，背景尽量简单

2. **角色图标** (`character.png`) - 可选
   - 用于检测角色位置
   - 如果不需要精确位置检测，可以跳过

3. **战斗界面特征** (`combat_ui.png`) - 可选
   - 截取战斗界面的特征元素（如六边形网格、战斗UI等）
   - 用于判断是否进入战斗

4. **地图界面特征** (`map_ui.png`) - 可选
   - 截取地图界面的特征元素
   - 用于判断是否在地图界面

### 步骤4：配置探索度文本区域

**方法1：使用可视化定位工具（推荐）**

1. 确保游戏已经通过屏幕镜像投射到电脑
2. 运行定位工具：

```bash
python tools/locate_exploration_text.py
```

3. 在工具窗口中：
   - 工具会自动截取配置的窗口区域
   - **按住鼠标左键并拖拽**，选择包含"探索度 XX%"文本的区域
   - 释放鼠标，确认选择
   - 点击"确认选择"按钮
   - 点击"保存到配置文件"将坐标保存

**方法2：手动配置**

编辑 `config/config.yaml`，添加或修改：

```yaml
exploration:
  text_region:
    left: 100    # 文本区域左边界（相对于窗口，单位：像素）
    top: 50     # 文本区域上边界（相对于窗口，单位：像素）
    width: 200  # 文本区域宽度（单位：像素）
    height: 50  # 文本区域高度（单位：像素）
```

**方法3：通过代码设置**

```python
from src.exploration_tracking.exploration_tracker import ExplorationTracker

tracker = ExplorationTracker()
tracker.set_exploration_text_region(left=100, top=50, width=200, height=50)
```

**如何找到文本位置？**

1. 打开游戏，找到显示"探索度 XX%"的位置
2. 使用截图工具（如Windows的Snipping Tool、Mac的截图工具）截图
3. 在截图上查看文本的像素坐标
4. 或者使用定位工具自动选择区域

### 步骤5：运行程序

```bash
python main.py
```

## 配置说明

### 窗口配置

```yaml
window:
  x: 0          # 游戏窗口左上角的屏幕x坐标
  y: 0          # 游戏窗口左上角的屏幕y坐标
  width: 1920   # 游戏窗口宽度
  height: 1080  # 游戏窗口高度
```

### 游戏配置

```yaml
game:
  exploration_target: 100  # 探索度目标（0-100）
  battle_timeout: 300      # 战斗超时时间（秒）
  move_click_delay: 0.5    # 移动点击后的延迟（秒）
```

### 识别配置

```yaml
recognition:
  template_match_threshold: 0.8  # 模板匹配置信度阈值（0-1）
  ocr:
    engine: "pytesseract"  # OCR引擎：pytesseract 或 easyocr
    lang: "chi_sim"       # OCR语言：chi_sim（中文简体）
```

## 故障排除

### 1. 无法识别怪物

- 检查 `templates/monster.png` 是否存在且清晰
- 调整 `template_match_threshold` 降低阈值（如 0.7）
- 确保游戏窗口区域配置正确

### 2. OCR识别失败

- 检查 Tesseract OCR 是否安装
- 确认 `lang` 配置正确（中文用 "chi_sim"）
- 调整探索度文本区域配置
- 尝试使用 `easyocr` 引擎

### 3. 点击位置不准确

- 检查窗口区域配置是否正确
- 确认游戏窗口位置没有移动
- 检查屏幕缩放设置

### 4. 战斗检测失败

- 添加战斗界面和地图界面模板
- 调整模板匹配阈值
- 检查战斗超时时间设置

## 高级用法

### 自定义怪物选择策略

```python
from src.monster_detection.monster_detector import MonsterDetector

detector = MonsterDetector()
# 选择最近的怪物（默认）
monster = detector.select_monster_by_strategy("nearest", current_pos=(100, 200))

# 选择第一个检测到的怪物
monster = detector.select_monster_by_strategy("first")

# 选择置信度最高的怪物
monster = detector.select_monster_by_strategy("highest_confidence")
```

### 手动设置探索度文本区域

```python
from src.exploration_tracking.exploration_tracker import ExplorationTracker

tracker = ExplorationTracker()
tracker.set_exploration_text_region(left=100, top=50, width=200, height=50)
exploration = tracker.get_current_exploration()
```

## 注意事项

1. **安全设置**：程序使用 `pyautogui`，默认启用了安全模式（鼠标移到屏幕左上角会触发异常停止）

2. **窗口位置**：确保游戏窗口位置固定，不要移动窗口

3. **屏幕分辨率**：不同分辨率可能需要调整模板和配置

4. **游戏更新**：游戏UI更新后，可能需要更新模板图像

5. **性能**：识别过程会消耗CPU，建议关闭不必要的程序
