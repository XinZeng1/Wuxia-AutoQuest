# ui-interaction Specification

## Purpose
TBD - created by archiving change add-auto-map-farming. Update Purpose after archive.
## Requirements
### Requirement: 屏幕截图能力
系统 SHALL 能够捕获游戏界面的屏幕截图，用于后续的图像识别和分析。

#### Scenario: 成功截图
- **WHEN** 调用截图功能
- **THEN** 返回当前游戏界面的完整截图图像

### Requirement: 坐标点击能力
系统 SHALL 能够在指定坐标位置执行点击操作，模拟用户触摸屏幕。

#### Scenario: 成功点击
- **WHEN** 提供屏幕坐标 (x, y)
- **THEN** 在该位置执行点击操作

#### Scenario: 点击按钮
- **WHEN** 识别到UI按钮元素并获取其坐标
- **THEN** 在该按钮位置执行点击操作

### Requirement: 图像模板匹配能力
系统 SHALL 能够在屏幕截图中查找匹配的模板图像，用于识别UI元素。

#### Scenario: 找到匹配元素
- **WHEN** 提供模板图像和屏幕截图
- **THEN** 返回匹配位置和置信度

#### Scenario: 未找到匹配元素
- **WHEN** 提供模板图像但屏幕中不存在该元素
- **THEN** 返回未匹配结果

### Requirement: UI元素等待能力
系统 SHALL 能够等待特定UI元素出现，用于处理异步加载的界面。

#### Scenario: 元素出现
- **WHEN** 等待某个UI元素出现
- **AND** 元素在超时时间内出现
- **THEN** 返回元素位置并继续执行

#### Scenario: 元素超时
- **WHEN** 等待某个UI元素出现
- **AND** 元素在超时时间内未出现
- **THEN** 返回超时错误

