"""
怪物检测循环测试脚本

持续检测怪物，显示检测结果和统计信息
"""
import sys
from pathlib import Path
import time
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.monster_detection.monster_detector import MonsterDetector
from src.map_navigation.map_navigator import MapNavigator
from src.core.logger import setup_logger, get_logger
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np

setup_logger(level='INFO', console=True)
logger = get_logger(__name__)


class MonsterTestLoop:
    """怪物检测循环测试"""

    def __init__(self):
        self.screenshot = Screenshot()
        self.detector = MonsterDetector()
        self.navigator = MapNavigator()

        # 统计信息
        self.total_scans = 0
        self.total_monsters_found = 0
        self.scan_times = []

        logger.info(f"检测方法: {self.detector.detection_method}")

    def visualize_monsters(self, screenshot: Image.Image, monsters):
        """可视化检测到的怪物"""
        vis_img = screenshot.copy()
        draw = ImageDraw.Draw(vis_img)

        try:
            font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 20)
        except:
            font = ImageFont.load_default()

        # 计算坐标转换比例（窗口逻辑坐标 -> 截图物理像素）
        window_width, window_height = self.screenshot.get_window_size()
        scale_x = screenshot.width / window_width
        scale_y = screenshot.height / window_height

        for i, (x, y, conf) in enumerate(monsters):
            # 将窗口逻辑坐标转换为截图物理像素坐标
            screenshot_x = int(x * scale_x)
            screenshot_y = int(y * scale_y)

            # 绘制十字标记
            size = 20
            draw.line([(screenshot_x - size, screenshot_y), (screenshot_x + size, screenshot_y)], fill='red', width=3)
            draw.line([(screenshot_x, screenshot_y - size), (screenshot_x, screenshot_y + size)], fill='red', width=3)

            # 绘制圆圈
            draw.ellipse([screenshot_x - 10, screenshot_y - 10, screenshot_x + 10, screenshot_y + 10], outline='red', width=2)

            # 绘制编号和置信度
            text = f"#{i+1} ({conf:.2f})"
            draw.text((screenshot_x + 15, screenshot_y - 10), text, fill='red', font=font)

        return vis_img

    def run_single_scan(self, save_image=False):
        """执行单次扫描"""
        logger.info("=" * 60)
        logger.info(f"扫描 #{self.total_scans + 1}")

        # 截图
        start_time = time.time()
        screenshot = self.screenshot.capture_full_window()

        # 检测怪物
        monsters = self.detector.detect_monsters(screenshot)
        scan_time = time.time() - start_time

        # 更新统计
        self.total_scans += 1
        self.total_monsters_found += len(monsters)
        self.scan_times.append(scan_time)

        # 输出结果
        logger.info(f"检测耗时: {scan_time:.2f}秒")
        logger.info(f"检测到 {len(monsters)} 个怪物")

        if monsters:
            # 选择最近的怪物
            current_pos = self.navigator.get_current_position()
            nearest = self.detector.select_nearest_monster(current_pos, monsters)

            logger.info("怪物列表:")
            for i, (x, y, conf) in enumerate(monsters):
                is_nearest = (nearest and x == nearest[0] and y == nearest[1])
                marker = " [最近]" if is_nearest else ""
                logger.info(f"  #{i+1}: 位置({x}, {y}), 置信度: {conf:.3f}{marker}")

            # 保存可视化图像
            if save_image:
                vis_img = self.visualize_monsters(screenshot, monsters)
                output_path = project_root / f"monster_scan_{self.total_scans}.png"
                vis_img.save(output_path)
                logger.info(f"可视化结果已保存: {output_path}")

        # 输出统计
        avg_time = sum(self.scan_times) / len(self.scan_times)
        avg_monsters = self.total_monsters_found / self.total_scans
        logger.info(f"统计: 平均耗时 {avg_time:.2f}秒, 平均检测 {avg_monsters:.1f} 个怪物")

        return monsters

    def run_loop(self, interval=5, max_scans=None, save_images=False):
        """循环检测怪物

        Args:
            interval: 扫描间隔（秒）
            max_scans: 最大扫描次数，None表示无限循环
            save_images: 是否保存可视化图像
        """
        logger.info("=" * 60)
        logger.info("开始怪物检测循环")
        logger.info(f"扫描间隔: {interval}秒")
        logger.info(f"最大扫描次数: {max_scans if max_scans else '无限'}")
        logger.info(f"保存图像: {'是' if save_images else '否'}")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 60)

        try:
            while True:
                if max_scans and self.total_scans >= max_scans:
                    logger.info(f"已完成 {max_scans} 次扫描，停止")
                    break

                self.run_single_scan(save_image=save_images)

                if max_scans is None or self.total_scans < max_scans:
                    logger.info(f"等待 {interval} 秒后进行下一次扫描...")
                    time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\n收到中断信号，停止扫描")

        # 输出最终统计
        self.print_summary()

    def print_summary(self):
        """输出统计摘要"""
        logger.info("=" * 60)
        logger.info("扫描统计摘要")
        logger.info("=" * 60)
        logger.info(f"总扫描次数: {self.total_scans}")
        logger.info(f"总检测怪物数: {self.total_monsters_found}")

        if self.scan_times:
            avg_time = sum(self.scan_times) / len(self.scan_times)
            min_time = min(self.scan_times)
            max_time = max(self.scan_times)
            logger.info(f"平均扫描耗时: {avg_time:.2f}秒")
            logger.info(f"最快扫描耗时: {min_time:.2f}秒")
            logger.info(f"最慢扫描耗时: {max_time:.2f}秒")

        if self.total_scans > 0:
            avg_monsters = self.total_monsters_found / self.total_scans
            logger.info(f"平均每次检测怪物数: {avg_monsters:.1f}")

        logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='怪物检测循环测试')
    parser.add_argument('--interval', type=int, default=5, help='扫描间隔（秒），默认5秒')
    parser.add_argument('--count', type=int, default=None, help='扫描次数，默认无限循环')
    parser.add_argument('--save', action='store_true', help='保存可视化图像')
    parser.add_argument('--single', action='store_true', help='只执行一次扫描')

    args = parser.parse_args()

    tester = MonsterTestLoop()

    if args.single:
        # 单次扫描
        tester.run_single_scan(save_image=True)
        tester.print_summary()
    else:
        # 循环扫描
        tester.run_loop(
            interval=args.interval,
            max_scans=args.count,
            save_images=args.save
        )


if __name__ == "__main__":
    main()
