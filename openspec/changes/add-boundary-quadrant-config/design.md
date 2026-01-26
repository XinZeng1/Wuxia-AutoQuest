# Design: 分象限边界巡航

## Context
- 小地图中心为玩家，最近黄点为边界；`get_tangent_move_vector` 返回切线方向与 `D_mm`。
- 图像坐标系：x 向右、y 向下。中心 `(cx,cy)`，黄点 `(yx,yy)`，则 `dx = yx - cx`，`dy = yy - cy`。
- 象限定义：`dx < 0` 左，`dx > 0` 右；`dy < 0` 上，`dy > 0` 下 → `tl`(左上)、`tr`(右上)、`bl`(左下)、`br`(右下)。

## Goals / Non-Goals
- Goals: 按象限区分贴墙策略；分象限可配置；单象限可单独测试；整合后四种墙均正确。
- Non-Goals: 不引入复杂路径规划；不改变回溯/防卡死主流程。

## Decisions
- **象限 → 配置档位**：先用 **upper**（tl+tr）与 **lower**（bl+br）两档。upper 对应「无法贴墙、需保持距离」，lower 对应「可贴墙」。配置键 `minimap.quadrants.upper` / `minimap.quadrants.lower`，每档可覆盖 `close_boundary_max_step`、`min_yellow_dist_px` 等；未覆盖则回退全局 `minimap.*`。
- **返回值扩展**：`get_tangent_move_vector` 增加返回象限，即 `(tx, ty, D_mm, quadrant)`，`quadrant in ('tl','tr','bl','br')`。`vector_to_click` 增加可选参数 `quadrant`，据此解析 `quadrants.upper` / `quadrants.lower` 覆盖。
- **单象限测试**：`test_boundary_quadrant.py` 仅当检测到指定 `--quadrant` 时才执行移动并统计，否则跳过并提示「当前墙象限与指定不符」；便于用户把角色摆到对应墙再跑测试。

## Risks / Trade-offs
- 两档粒度若不足：后续可扩展为四象限独立配置，当前先验证 upper/lower 是否解决主要问题。

## Migration Plan
- 无 Breaking 变更；未配置 `quadrants` 时行为与现有一致（全用全局 minimap 配置）。
