"""
探索导航模块

实现混合探索策略：小地图引导 + 8方向系统扫描
"""
import math
import random
import time
from typing import Optional, Tuple, List
from PIL import Image
import numpy as np

from src.core.config import get_config
from src.core.logger import get_logger
from src.map_navigation.minimap_analyzer import MinimapAnalyzer

logger = get_logger(__name__)


class SystematicScanner:
    """8方向系统扫描器"""

    # 8个方向：上、右上、右、右下、下、左下、左、左上
    DIRECTIONS = [
        (0, -1),   # 上
        (1, -1),   # 右上
        (1, 0),    # 右
        (1, 1),    # 右下
        (0, 1),    # 下
        (-1, 1),   # 左下
        (-1, 0),   # 左
        (-1, -1),  # 左上
    ]

    def __init__(self, steps_per_direction: int = 3):
        """
        初始化系统扫描器

        Args:
            steps_per_direction: 每个方向移动的次数
        """
        self.steps_per_direction = steps_per_direction
        self.current_direction_index = 0
        self.steps_in_current_direction = 0

    def get_next_direction(self) -> Tuple[float, float]:
        """
        获取下一个扫描方向

        Returns:
            方向向量 (dx, dy)
        """
        direction = self.DIRECTIONS[self.current_direction_index]
        self.steps_in_current_direction += 1

        # 如果当前方向已经移动足够次数，切换到下一个方向
        if self.steps_in_current_direction >= self.steps_per_direction:
            self.current_direction_index = (self.current_direction_index + 1) % len(self.DIRECTIONS)
            self.steps_in_current_direction = 0
            logger.debug(f"切换到方向 {self.current_direction_index}: {self.DIRECTIONS[self.current_direction_index]}")

        return direction

    def reset(self):
        """重置扫描器"""
        self.current_direction_index = 0
        self.steps_in_current_direction = 0


class ExplorationNavigator:
    """探索导航器 - 混合策略"""

    def __init__(self, screenshot=None, navigator=None):
        """
        初始化探索导航器

        Args:
            screenshot: Screenshot实例
            navigator: MapNavigator实例
        """
        from src.ui_interaction.screenshot import Screenshot
        from src.map_navigation.map_navigator import MapNavigator

        self.config = get_config()
        self.screenshot = screenshot or Screenshot()
        self.navigator = navigator or MapNavigator()
        self.minimap_analyzer = MinimapAnalyzer()
        self.systematic_scanner = SystematicScanner(steps_per_direction=3)

        # 窗口尺寸
        self.window_size = self.screenshot.get_window_size()

        # 卡死检测
        self.position_history: List[np.ndarray] = []
        self.max_history_size = 5
        self.stuck_similarity_threshold = 0.95
        self.last_move_time = time.monotonic()
        self.stuck_timeout = 3.0  # 3秒无移动视为卡死

        # 探索配置
        self.move_distance = 100  # 移动距离（像素）
        self.escape_radius = 80  # 逃逸半径

    def explore_to_unexplored(self, full_image: Optional[Image.Image] = None) -> bool:
        """
        向未探索区域移动（基于小地图分析）

        Args:
            full_image: 完整窗口截图，如果为None则重新截图

        Returns:
            True 如果成功移动，False 如果没有未探索区域
        """
        if full_image is None:
            full_image = self.screenshot.capture_full_window()

        # 获取小地图
        minimap = self.screenshot.capture_minimap(full_image)
        if minimap is None:
            logger.warning("无法获取小地图")
            return False

        # 分析小地图，获取未探索区域方向
        direction = self.minimap_analyzer.calculate_direction_to_unexplored(minimap)
        if direction is None:
            logger.debug("小地图上没有未探索区域")
            return False

        # 计算移动目标点
        dx, dy = direction
        target = self._calculate_move_target(dx, dy, self.move_distance)

        # 移动
        self.navigator.move_to(target[0], target[1])
        self._record_move(minimap)

        logger.info(f"向未探索区域移动: 方向({dx:.2f}, {dy:.2f}), 目标{target}")
        return True

    def explore_systematic(self) -> bool:
        """
        系统性扫描（8方向）

        Returns:
            True 表示成功移动
        """
        # 获取下一个扫描方向
        direction = self.systematic_scanner.get_next_direction()
        dx, dy = direction

        # 计算移动目标点
        target = self._calculate_move_target(dx, dy, self.move_distance)

        # 移动
        self.navigator.move_to(target[0], target[1])

        # 获取小地图用于卡死检测
        full_image = self.screenshot.capture_full_window()
        minimap = self.screenshot.capture_minimap(full_image)
        if minimap:
            self._record_move(minimap)

        logger.info(f"系统扫描移动: 方向{direction}, 目标{target}")
        return True

    def _calculate_move_target(self, dx: float, dy: float, distance: float) -> Tuple[int, int]:
        """
        计算移动目标点（从屏幕中心出发）

        Args:
            dx: x方向分量
            dy: y方向分量
            distance: 移动距离

        Returns:
            目标坐标 (x, y)
        """
        w, h = self.window_size
        center_x, center_y = w / 2, h / 2

        target_x = center_x + dx * distance
        target_y = center_y + dy * distance

        # 限制在窗口范围内
        target_x = max(0, min(w - 1, target_x))
        target_y = max(0, min(h - 1, target_y))

        return (int(target_x), int(target_y))

    def _record_move(self, minimap: Image.Image):
        """
        记录移动（用于卡死检测）

        Args:
            minimap: 小地图图像
        """
        fingerprint = self.minimap_analyzer.get_minimap_fingerprint(minimap)
        self.position_history.append(fingerprint)

        # 保持历史记录大小
        if len(self.position_history) > self.max_history_size:
            self.position_history.pop(0)

        self.last_move_time = time.monotonic()

    def is_stuck(self) -> bool:
        """
        检测是否卡死

        Returns:
            True 如果卡死，False 否则
        """
        # 方法1：位置历史检测
        if len(self.position_history) >= self.max_history_size:
            # 比较最近的位置是否几乎相同
            recent = self.position_history[-self.max_history_size:]
            similarities = []
            for i in range(len(recent) - 1):
                sim = self.minimap_analyzer.compare_fingerprints(recent[i], recent[i + 1])
                similarities.append(sim)

            avg_similarity = np.mean(similarities)
            if avg_similarity > self.stuck_similarity_threshold:
                logger.warning(f"检测到卡死（位置相似度: {avg_similarity:.3f}）")
                return True

        # 方法2：超时检测
        elapsed = time.monotonic() - self.last_move_time
        if elapsed > self.stuck_timeout:
            logger.warning(f"检测到卡死（超时: {elapsed:.1f}秒）")
            return True

        return False

    def escape(self):
        """随机逃逸（用于摆脱卡死）"""
        w, h = self.window_size
        center_x, center_y = w / 2, h / 2

        # 随机方向
        angle = random.uniform(0, 2 * math.pi)
        dx = math.cos(angle)
        dy = math.sin(angle)

        # 随机距离
        distance = random.uniform(self.escape_radius * 0.5, self.escape_radius)

        target_x = int(center_x + dx * distance)
        target_y = int(center_y + dy * distance)

        # 限制在窗口范围内
        target_x = max(0, min(w - 1, target_x))
        target_y = max(0, min(h - 1, target_y))

        self.navigator.move_to(target_x, target_y)

        # 清空历史记录
        self.position_history.clear()
        self.last_move_time = time.monotonic()

        logger.info(f"随机逃逸: ({target_x}, {target_y})")

    def is_exploration_complete(self, full_image: Optional[Image.Image] = None) -> bool:
        """
        检查探索是否完成（基于小地图）

        Args:
            full_image: 完整窗口截图

        Returns:
            True 如果小地图已全部探索
        """
        if full_image is None:
            full_image = self.screenshot.capture_full_window()

        minimap = self.screenshot.capture_minimap(full_image)
        if minimap is None:
            return False

        return self.minimap_analyzer.is_minimap_fully_explored(minimap)

