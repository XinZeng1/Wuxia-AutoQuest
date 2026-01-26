#!/usr/bin/env python3
"""
单象限边界巡航测试：仅当墙在指定象限时执行移动，便于逐象限调参。
用法：python tools/test_boundary_quadrant.py --quadrant tl|tr|bl|br
请先将角色站到对应墙侧再运行（如 --quadrant bl 表示墙在左下）。
"""
import argparse
import sys
import time
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import get_config
from src.core.logger import setup_logger, get_logger
from src.ui_interaction.screenshot import Screenshot
from src.map_navigation.map_navigator import MapNavigator
from src.map_navigation.boundary_cruise import (
    BoundaryCruiseDriver,
    get_tangent_move_vector,
    vector_to_click,
)
from src.exploration_tracking.exploration_tracker import ExplorationTracker

setup_logger(level="DEBUG", log_file=None, console=True)
logger = get_logger(__name__)

QUADRANTS = ("tl", "tr", "bl", "br")


def main():
    ap = argparse.ArgumentParser(description="单象限边界巡航测试")
    ap.add_argument(
        "--quadrant",
        choices=QUADRANTS,
        required=True,
        help="只在该象限有墙时移动：tl=左上, tr=右上, bl=左下, br=右下",
    )
    args = ap.parse_args()
    want = args.quadrant

    cfg = get_config()
    shot = Screenshot()
    nav = MapNavigator()
    driver = BoundaryCruiseDriver(screenshot=shot, navigator=nav)
    tracker = ExplorationTracker()
    mm_cfg = cfg.get("minimap") or {}
    cruise_interval = float(mm_cfg.get("cruise_interval_sec", 1.2))

    logger.info("单象限边界巡航测试，仅象限 %s 时移动；按 Ctrl+C 停止", want)
    ratio = mm_cfg.get("minimap_to_game_ratio")
    use_ratio = ratio is not None and float(ratio) > 0
    logger.info(
        "move_scale=%s, ratio=%s, scale=[%s,%s], cruise_interval=%.1fs",
        mm_cfg.get("move_scale", 50),
        ratio if use_ratio else "off",
        mm_cfg.get("move_scale_min", 15),
        mm_cfg.get("move_scale_max", 120),
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
                logger.info("探索度: %s%%", exp)
                if tracker.is_exploration_complete():
                    logger.info("探索度已达到100%%，测试完成")
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

            out = get_tangent_move_vector(mm, last_tangent=last_tangent, filter_quadrant=want)
            if out is None:
                no_tangent_count += 1
                logger.debug("未找到切线向量（连续 %d 次）", no_tangent_count)
                if no_tangent_count >= max_no_tangent:
                    logger.warning("连续无法找到切线，可能无黄点边界，停止")
                    break
                time.sleep(0.5)
                continue

            no_tangent_count = 0
            tx, ty, d_mm, quadrant = out

            if quadrant != want:
                logger.info(
                    "当前墙象限 %s，与指定 %s 不符，请调整站位后再试",
                    quadrant,
                    want,
                )
                time.sleep(cruise_interval)
                continue

            last_tangent = (tx, ty)
            gx, gy = vector_to_click(
                tx, ty, driver.window_size, minimap_distance=d_mm, quadrant=quadrant
            )
            nav.move_to(gx, gy)
            driver._record_move(gx, gy)
            driver.feed_minimap(mm)
            move_count += 1
            logger.info(
                "边界巡航移动 #%d: (%d, %d), 向量: (%.2f, %.2f), D_mm: %.1f, 象限: %s",
                move_count, gx, gy, tx, ty, d_mm, quadrant,
            )
            time.sleep(cruise_interval)

    except KeyboardInterrupt:
        logger.info("收到中断信号，停止测试")
    except Exception as e:
        logger.error("测试出错: %s", e, exc_info=True)

    logger.info("测试结束，共执行 %d 次移动", move_count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
