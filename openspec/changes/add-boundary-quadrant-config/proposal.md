# Change: 按墙所在象限分设边界巡航配置与单象限测试

## Why
全地图自动寻路逻辑有问题：地图由两个方向的边构成，因角色站位，墙相对角色有四种情况（左上、右上、左下、右下）。且观察发现左上/右上与左下/右下行为不同——左下、右下可贴着墙移动，左上、右上无法贴墙、需保持一定距离（疑似游戏设计）。现有单一配置无法同时兼顾四种墙，导致部分方向点击路线不准或点到墙内。

## What Changes
- 在边界巡航中识别「墙所在象限」（左上/右上/左下/右下），并向下游传递。
- 为各象限提供可覆盖的配置（先简化为 **upper**（左上+右上）与 **lower**（左下+右下）两档），如 `close_boundary_max_step`、`min_yellow_dist_px` 等；lower 可贴墙，upper 保持距离。
- `vector_to_click` 及巡航逻辑根据当前象限选用对应配置。
- 新增单象限测试工具 `tools/test_boundary_quadrant.py`，支持 `--quadrant tl|tr|bl|br`，便于逐象限调参、确保每种墙都能正确点击路线。
- 整合到 `cruise_tick` / 主流程，最终四种墙均能正确沿墙移动。

## Impact
- Affected specs: `map-navigation`
- Affected code: `src/map_navigation/boundary_cruise.py`, `config/config.yaml`, 新增 `tools/test_boundary_quadrant.py`
