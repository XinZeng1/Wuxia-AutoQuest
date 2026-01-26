## 1. 象限检测与传递
- [x] 1.1 在 `get_tangent_move_vector` 中根据最近黄点相对中心 `(dx,dy)` 计算象限 `tl|tr|bl|br`，并作为第四项返回 `(tx, ty, D_mm, quadrant)`。
- [x] 1.2 更新 `vector_to_click` 签名，增加可选参数 `quadrant`；调用处传入 quadrant。

## 2. 分象限配置
- [x] 2.1 在 `config.yaml` 的 `minimap` 下增加 `quadrants.upper` 与 `quadrants.lower`，每档可配置 `close_boundary_max_step`、`min_yellow_dist_px` 等；文档注释说明 upper 不贴墙、lower 可贴墙。
- [x] 2.2 在 `vector_to_click` 内根据 `quadrant` 解析 `quadrants.upper` / `quadrants.lower` 覆盖，未配置则回退全局 `minimap`。

## 3. 单象限测试工具
- [x] 3.1 新增 `tools/test_boundary_quadrant.py`，支持 `--quadrant tl|tr|bl|br`。
- [x] 3.2 仅当当前检测到的墙象限与 `--quadrant` 一致时才执行移动、记录并 `feed_minimap`；否则跳过并打印「当前墙象限 X，与指定 Y 不符，请调整站位」；循环中周期性检测探索度与卡死。

## 4. 整合
- [x] 4.1 `cruise_tick` 及 `test_boundary_cruise_only` 使用带 quadrant 的 `get_tangent_move_vector` 与 `vector_to_click`，确保四种墙均走分象限逻辑。
- [x] 4.2 更新 `tools/test_boundary_cruise_only.py` 若仍直接调用切线/点击，则改为传入 quadrant。
