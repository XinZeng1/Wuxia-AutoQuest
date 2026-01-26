#!/usr/bin/env python3
"""
测算小地图「人物↔黄点」距离与游戏内点击距离的比例。

用法：游戏窗口可见、小地图有黄点时运行。会连续截数帧小地图，统计最近黄点距离 D_mm，
再根据 move_scale 建议 minimap_to_game_ratio = move_scale / D_mm，并给出配置示例。
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.ui_interaction.screenshot import Screenshot
from src.map_navigation.boundary_cruise import get_tangent_move_vector


def main():
    cfg = get_config()
    mm_cfg = cfg.get("minimap") or {}
    move_scale = float(mm_cfg.get("move_scale", 50))
    n_samples = 5
    interval = 0.8

    shot = Screenshot()
    full = shot.capture_full_window()
    mm = shot.capture_minimap(full)
    if mm is None:
        print("未配置 minimap.region 或截取失败")
        return 1

    min_dist = float(mm_cfg.get("min_yellow_dist_px", 8))
    print("测算小地图距离→游戏内步长比例")
    print("请确保游戏窗口可见、小地图有黄点。将采样多帧取平均。")
    print(f"忽略距中心 < {min_dist:.0f} px 的黄点（min_yellow_dist_px）。")
    print()

    d_mm_list = []
    for i in range(n_samples):
        full = shot.capture_full_window()
        mm = shot.capture_minimap(full)
        if mm is None:
            continue
        out = get_tangent_move_vector(mm)
        if out is None:
            print(f"  帧 {i + 1}: 未检测到黄点，跳过")
            continue
        _, _, d_mm, _ = out
        d_mm_list.append(d_mm)
        print(f"  帧 {i + 1}: 最近黄点距离 D_mm = {d_mm:.1f} 小地图像素")
        if i < n_samples - 1:
            time.sleep(interval)

    if not d_mm_list:
        print("未获取到有效采样，请确认小地图有黄点后重试")
        return 1

    avg = sum(d_mm_list) / len(d_mm_list)
    ratio = move_scale / avg if avg > 1e-6 else 0

    print()
    print("--- 测算结果 ---")
    print(f"  最近黄点距离（平均）: D_mm = {avg:.1f} 小地图像素")
    print(f"  当前 move_scale: {move_scale} 游戏像素")
    print(f"  建议 minimap_to_game_ratio: {ratio:.2f}  （即 1 小地图像素 ≈ {ratio:.1f} 游戏像素）")
    print()
    print("在 config/config.yaml 的 minimap 下添加或修改：")
    print("  minimap_to_game_ratio: {:.2f}".format(ratio))
    print("  move_scale_min: 15   # 步长下限（游戏像素）")
    print("  move_scale_max: 120  # 步长上限（游戏像素）")
    print()
    print("启用后，每次移动的点击距离 = ratio × D_mm，并限制在 [min, max] 内。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
