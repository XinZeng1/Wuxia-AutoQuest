#!/usr/bin/env python3
"""
最小测试：仅边界巡航走完全地图。
忽略怪物检测、战斗、回溯逻辑，只测试沿墙移动。
"""
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.core.logger import setup_logger, get_logger
from src.ui_interaction.screenshot import Screenshot
from src.map_navigation.map_navigator import MapNavigator
from src.map_navigation.boundary_cruise import BoundaryCruiseDriver, get_tangent_move_vector, vector_to_click
from src.exploration_tracking.exploration_tracker import ExplorationTracker

setup_logger(level='INFO', log_file=None, console=True)
logger = get_logger(__name__)


def main():
    cfg = get_config()
    shot = Screenshot()
    nav = MapNavigator()
    driver = BoundaryCruiseDriver(screenshot=shot, navigator=nav)
    tracker = ExplorationTracker()
    mm_cfg = cfg.get('minimap') or {}
    cruise_interval = float(mm_cfg.get('cruise_interval_sec', 1.2))

    logger.info("开始边界巡航测试（忽略怪物与回溯）")
    logger.info("按 Ctrl+C 停止")
    ratio = mm_cfg.get('minimap_to_game_ratio')
    use_ratio = ratio is not None and float(ratio) > 0
    logger.info(
        "move_scale=%s, ratio=%s, scale=[%s,%s], min_yellow_dist=%s, cruise_interval=%.1fs",
        mm_cfg.get('move_scale', 50),
        ratio if use_ratio else "off",
        mm_cfg.get('move_scale_min', 15),
        mm_cfg.get('move_scale_max', 120),
        mm_cfg.get('min_yellow_dist_px', 8),
        cruise_interval,
    )

    move_count = 0
    no_tangent_count = 0
    max_no_tangent = 10
    last_tangent = None

    try:
        while True:
            exp = tracker.get_current_exploration()
            if exp is not None:
                logger.info(f"探索度: {exp}%")
                if tracker.is_exploration_complete():
                    logger.info("探索度已达到100%，测试完成")
                    break

            if driver.is_stuck_cruise():
                logger.warning("检测到卡死，执行随机逃逸")
                driver.trigger_escape()
                last_tangent = None
                time.sleep(cruise_interval)
                continue

            full = shot.capture_full_window()
            mm = shot.capture_minimap(full)

            if mm is None:
                logger.warning("无法截取小地图，跳过")
                time.sleep(1)
                continue

            out = get_tangent_move_vector(mm, last_tangent=last_tangent)
            if out is None:
                no_tangent_count += 1
                logger.debug(f"未找到切线向量（连续 {no_tangent_count} 次）")
                if no_tangent_count >= max_no_tangent:
                    logger.warning("连续无法找到切线，可能无黄点边界，停止")
                    break
                time.sleep(0.5)
                continue

            no_tangent_count = 0
            tx, ty, d_mm, quadrant = out
            last_tangent = (tx, ty)
            gx, gy = vector_to_click(tx, ty, driver.window_size, minimap_distance=d_mm, quadrant=quadrant)

            nav.move_to(gx, gy)
            driver._record_move(gx, gy)
            driver.feed_minimap(mm)
            move_count += 1
            logger.info(
                f"边界巡航移动 #{move_count}: ({gx}, {gy}), 向量: ({tx:.2f}, {ty:.2f}), D_mm: {d_mm:.1f}, 象限: {quadrant}"
            )
            time.sleep(cruise_interval)
            
    except KeyboardInterrupt:
        logger.info("收到中断信号，停止测试")
    except Exception as e:
        logger.error(f"测试出错: {e}", exc_info=True)
    
    logger.info(f"测试结束，共执行 {move_count} 次移动")


if __name__ == "__main__":
    main()
