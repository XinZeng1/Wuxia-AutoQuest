# 游戏自动刷图工具

通过屏幕镜像在电脑上自动控制游戏进行地图探索的工具。

## 功能特性

- 自动识别地图路径并控制角色移动
- 自动检测怪物并导航到怪物位置触发战斗
- 监控地图探索进度
- 等待战斗自动完成并继续探索

## 技术栈

- Python 3.8+
- OpenCV - 图像识别
- PIL/Pillow - 图像处理
- pytesseract/easyocr - OCR文本识别
- mss - 屏幕截图
- pyautogui - 鼠标控制

## 安装

```bash
pip install -r requirements.txt
```

## 配置

1. 将游戏通过屏幕镜像软件（如Scrcpy、AirDroid等）投射到电脑
2. 配置 `config.yaml` 中的窗口区域和游戏参数
3. 运行主程序

## 使用

### 1. 配置

编辑 `config/config.yaml` 文件：

```yaml
# 屏幕镜像窗口配置（根据你的镜像窗口位置调整）
window:
  x: 0          # 窗口左上角x坐标
  y: 0          # 窗口左上角y坐标
  width: 1920   # 窗口宽度
  height: 1080  # 窗口高度

# 游戏配置
game:
  exploration_target: 100  # 探索度目标（百分比）
  battle_timeout: 300      # 战斗等待超时时间（秒）
  move_click_delay: 0.5    # 移动点击延迟（秒）
```

### 2. 准备模板图像

在 `templates/` 目录下放置以下模板图像（需要从游戏中截图）：

- `monster.png` - 怪物图标模板
- `character.png` - 角色图标模板（可选）
- `combat_ui.png` - 战斗界面特征模板（可选）
- `map_ui.png` - 地图界面特征模板（可选）

### 3. 配置探索度文本区域

运行程序前，需要配置探索度文本的屏幕区域。可以通过修改代码或添加配置项来设置。

### 4. 运行

```bash
python main.py
```

程序会自动：
1. 检测地图上的怪物
2. 控制角色移动到怪物位置
3. 等待战斗自动完成
4. 监控探索进度
5. 重复上述流程直到达到探索目标

### 5. 停止

按 `Ctrl+C` 停止程序。

## 项目结构

```
.
├── src/
│   ├── ui_interaction/    # UI交互模块
│   ├── map_navigation/    # 地图导航模块
│   ├── monster_detection/ # 怪物检测模块
│   ├── exploration_tracking/ # 探索度跟踪模块
│   └── core/              # 核心控制流程
├── config/                # 配置文件
├── templates/             # 图像模板
├── logs/                  # 日志文件
├── main.py               # 主程序入口
└── requirements.txt      # 依赖列表
```
