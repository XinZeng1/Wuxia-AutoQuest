"""
地图探索测试脚本

只探索地图，不打怪，用于测试探索功能
"""
import sys
from pathlib import Path
import time
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.map_navigation.map_navigator import MapNavigator
from src.map_navigation.exploration_navigator import ExplorationNavigator
from src.exploration_tracking.exploration_tracker import ExplorationTracker
from src.core.logger import setup_logger, get_logger

setup_logger(level='INFO', console=True)
logger = get_logger(__name__)


class ExplorationTest:
    """地图探索测试"""

    def __init__(self):
        self.screenshot = Screenshot()
        self.navigator = MapNavigator()
        self.exploration_navigator = ExplorationNavigator(
            screenshot=self.screenshot,
            navigator=self.navigator
        )
        self.exploration_tracker = ExplorationTracker()

        # 统计信息
        self.total_moves = 0
        self.minimap_guided_moves = 0
        self.systematic_moves = 0
        self.stuck_count = 0
        self.start_time = None

        logger.info("地图探索测试初始化完成")

    def check_exploration(self):
        """检查探索度"""
        try:
            exploration = self.exploration_tracker.get_current_exploration()
            if exploration is not None:
                logger.info(f"当前探索度: {exploration}%")
                return exploration
        except Exception as e:
            logger.warning(f"无法检测探索度: {e}")
        return None

    def explore_once(self, use_minimap=True):
        """执行一次探索移动

        Args:
            use_minimap: 是否优先使用小地图引导

        Returns:
            bool: 是否成功移动
        """
        try:
            # 检查是否卡死
            if self.exploration_navigator.is_stuck():
                logger.warning("检测到卡死，执行逃逸")
                self.exploration_navigator.escape()
                self.stuck_count += 1
                time.sleep(1.0)
                return True

            # 尝试小地图引导
            if use_minimap:
                logger.debug("尝试使用小地图引导")
                if self.exploration_navigator.explore_to_unexplored():
                    self.minimap_guided_moves += 1
                    self.total_moves += 1
                    logger.info(f"小地图引导移动 (总移动: {self.total_moves})")
                    return True

            # 使用系统扫描
            logger.debug("使用系统扫描")
            self.exploration_navigator.explore_systematic()
            self.systematic_moves += 1
            self.total_moves += 1
            logger.info(f"系统扫描移动 (总移动: {self.total_moves})")
            return True

        except Exception as e:
            logger.error(f"探索移动失败: {e}", exc_info=True)
            return False

    def run_exploration(
        self,
        duration_minutes=None,
        max_moves=None,
        move_interval=1.5,
        check_exploration_interval=10
    ):
        """运行探索循环

        Args:
            duration_minutes: 运行时长（分钟），None表示无限
            max_moves: 最大移动次数，None表示无限
            move_interval: 移动间隔（秒）
            check_exploration_interval: 检查探索度间隔（次数）
        """
        logger.info("=" * 60)
        logger.info("开始地图探索")
        logger.info(f"运行时长: {duration_minutes if duration_minutes else '无限'} 分钟")
        logger.info(f"最大移动次数: {max_moves if max_moves else '无限'}")
        logger.info(f"移动间隔: {move_interval}秒")
        logger.info("按 Ctrl+C 停止")
        logger.info("=" * 60)

        self.start_time = time.time()
        last_exploration_check = 0

        try:
            while True:
                # 检查时长限制
                if duration_minutes:
                    elapsed_minutes = (time.time() - self.start_time) / 60
                    if elapsed_minutes >= duration_minutes:
                        logger.info(f"已运行 {duration_minutes} 分钟，停止探索")
                        break

                # 检查移动次数限制
                if max_moves and self.total_moves >= max_moves:
                    logger.info(f"已完成 {max_moves} 次移动，停止探索")
                    break

                # 定期检查探索度
                if self.total_moves - last_exploration_check >= check_exploration_interval:
                    exploration = self.check_exploration()
                    if exploration and exploration >= 100:
                        logger.info("探索度已达到100%，完成！")
                        break
                    last_exploration_check = self.total_moves

                # 执行探索移动
                logger.info(f"\n--- 移动 #{self.total_moves + 1} ---")
                success = self.explore_once(use_minimap=True)

                if success:
                    # 输出统计
                    elapsed = time.time() - self.start_time
                    logger.info(f"已运行: {elapsed/60:.1f}分钟, "
                              f"移动: {self.total_moves}, "
                              f"小地图: {self.minimap_guided_moves}, "
                              f"系统扫描: {self.systematic_moves}, "
                              f"卡死: {self.stuck_count}")

                    # 等待
                    time.sleep(move_interval)
                else:
                    logger.warning("移动失败，等待后重试")
                    time.sleep(2.0)

        except KeyboardInterrupt:
            logger.info("\n收到中断信号，停止探索")

        # 输出最终统计
        self.print_summary()

    def print_summary(self):
        """输出统计摘要"""
        logger.info("=" * 60)
        logger.info("探索统计摘要")
        logger.info("=" * 60)

        if self.start_time:
            elapsed = time.time() - self.start_time
            logger.info(f"总运行时间: {elapsed/60:.1f}分钟 ({elapsed:.0f}秒)")

        logger.info(f"总移动次数: {self.total_moves}")
        logger.info(f"小地图引导移动: {self.minimap_guided_moves}")
        logger.info(f"系统扫描移动: {self.systematic_moves}")
        logger.info(f"卡死次数: {self.stuck_count}")

        if self.total_moves > 0:
            minimap_ratio = self.minimap_guided_moves / self.total_moves * 100
            logger.info(f"小地图引导比例: {minimap_ratio:.1f}%")

            if self.start_time:
                moves_per_minute = self.total_moves / (elapsed / 60)
                logger.info(f"平均移动速度: {moves_per_minute:.1f} 次/分钟")

        # 最终探索度
        exploration = self.check_exploration()
        if exploration:
            logger.info(f"最终探索度: {exploration}%")

        logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='地图探索测试')
    parser.add_argument('--duration', type=int, default=None,
                       help='运行时长（分钟），默认无限')
    parser.add_argument('--moves', type=int, default=None,
                       help='最大移动次数，默认无限')
    parser.add_argument('--interval', type=float, default=1.5,
                       help='移动间隔（秒），默认1.5秒')
    parser.add_argument('--check-interval', type=int, default=10,
                       help='检查探索度间隔（移动次数），默认10次')

    args = parser.parse_args()

    tester = ExplorationTest()
    tester.run_exploration(
        duration_minutes=args.duration,
        max_moves=args.moves,
        move_interval=args.interval,
        check_exploration_interval=args.check_interval
    )


if __name__ == "__main__":
    main()
