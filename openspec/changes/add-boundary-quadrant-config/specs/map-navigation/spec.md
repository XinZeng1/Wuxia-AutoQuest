## ADDED Requirements

### Requirement: 分象限边界巡航配置与测试
系统 SHALL 按墙相对角色的象限（左上/右上/左下/右下）区分边界巡航参数，并为 upper（左上+右上）与 lower（左下+右下）提供独立配置；upper 对应与墙保持距离、lower 可贴墙。系统 SHALL 提供单象限测试工具，便于逐象限调参并确保每种墙都能正确沿墙点击。

#### Scenario: 象限识别与配置覆盖
- **WHEN** 边界巡航计算最近黄点并得到相对中心的 (dx,dy)
- **THEN** 判定象限 tl|tr|bl|br，并据此选用 quadrants.upper 或 quadrants.lower 的覆盖配置（若存在），否则使用全局 minimap 配置

#### Scenario: 单象限测试
- **WHEN** 用户运行 `test_boundary_quadrant.py --quadrant bl`
- **AND** 当前检测到的墙象限为 bl
- **THEN** 执行沿墙移动、feed_minimap 及卡死检测；否则跳过移动并提示当前象限与指定不符
