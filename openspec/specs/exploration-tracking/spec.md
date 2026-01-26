# exploration-tracking Specification

## Purpose
TBD - created by archiving change add-auto-map-farming. Update Purpose after archive.
## Requirements
### Requirement: 探索度文本识别能力
系统 SHALL 能够识别界面上的探索度文本信息。系统 SHALL 在识别失败时，先检查是否在战斗中，仅在确认不在战斗状态下才输出警告日志。系统 SHALL 将边界检查和正常失败情况的日志从 WARNING 降级为 DEBUG。

#### Scenario: 识别探索度
- **WHEN** 分析地图界面
- **THEN** 使用OCR识别并返回探索度文本（如"探索度 36%"）

#### Scenario: 探索度识别失败（非战斗状态）
- **WHEN** 分析地图界面
- **AND** OCR无法识别探索度文本
- **AND** 确认不在战斗状态
- **THEN** 输出警告日志
- **AND** 返回识别失败，使用上次识别的值或默认值

#### Scenario: 探索度识别失败（战斗状态）
- **WHEN** 分析地图界面
- **AND** OCR无法识别探索度文本
- **AND** 检测到在战斗状态
- **THEN** 不输出警告日志（战斗界面遮挡探索度文本是正常现象）
- **AND** 返回识别失败，使用上次识别的值或默认值

#### Scenario: 边界检查日志
- **WHEN** 探索度检测区域超出截图范围
- **THEN** 自动调整边界
- **AND** 使用 DEBUG 级别记录调整信息（而非 WARNING）

### Requirement: 探索度数值解析能力
系统 SHALL 能够从探索度文本中提取数值。

#### Scenario: 解析探索度百分比
- **WHEN** 识别到探索度文本"探索度 36%"
- **THEN** 提取并返回数值36

#### Scenario: 解析100%探索度
- **WHEN** 识别到探索度文本"探索度 100%"
- **THEN** 提取并返回数值100

### Requirement: 探索度目标设置能力
系统 SHALL 允许用户设置探索度目标（如100%探索）。

#### Scenario: 设置探索目标
- **WHEN** 用户配置探索目标为100%
- **THEN** 系统记录该目标并在达到时触发相应操作

### Requirement: 探索度完成判断能力
系统 SHALL 能够判断当前探索度是否达到目标。

#### Scenario: 达到探索目标
- **WHEN** 当前探索度为100%
- **AND** 目标探索度为100%
- **THEN** 返回探索完成状态

#### Scenario: 未达到探索目标
- **WHEN** 当前探索度为36%
- **AND** 目标探索度为100%
- **THEN** 返回探索未完成状态，继续探索

