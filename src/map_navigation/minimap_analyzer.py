"""
小地图分析模块

用于分析小地图，识别未探索区域，引导角色移动
"""
import cv2
import numpy as np
from PIL import Image
from typing import Optional, Tuple
from src.core.logger import get_logger

logger = get_logger(__name__)


class MinimapAnalyzer:
    """小地图分析器"""

    def __init__(self):
        """初始化小地图分析器"""
        # 阈值配置
        self.dark_threshold = 80  # 暗色区域阈值（未探索）
        self.obstacle_threshold = 30  # 障碍物阈值（纯黑色）
        self.min_unexplored_area = 50  # 最小未探索区域面积（像素）

    def detect_unexplored_areas(self, minimap_img: Image.Image) -> Optional[Tuple[int, int]]:
        """
        检测小地图上的未探索区域

        Args:
            minimap_img: 小地图图像（PIL Image）

        Returns:
            未探索区域的质心坐标 (x, y)，如果没有未探索区域则返回 None
        """
        try:
            # 转换为numpy数组
            img_array = np.array(minimap_img)

            # 转换为灰度图
            if len(img_array.shape) == 3:
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            else:
                gray = img_array

            # 阈值分割：识别暗色区域（未探索）
            # 暗色区域的灰度值较低，但不是纯黑色（障碍物）
            _, dark_areas = cv2.threshold(gray, self.dark_threshold, 255, cv2.THRESH_BINARY_INV)

            # 排除纯黑色区域（障碍物）
            _, obstacles = cv2.threshold(gray, self.obstacle_threshold, 255, cv2.THRESH_BINARY_INV)
            unexplored = cv2.bitwise_and(dark_areas, cv2.bitwise_not(obstacles))

            # 形态学操作：去除噪点
            kernel = np.ones((3, 3), np.uint8)
            unexplored = cv2.morphologyEx(unexplored, cv2.MORPH_OPEN, kernel)
            unexplored = cv2.morphologyEx(unexplored, cv2.MORPH_CLOSE, kernel)

            # 计算未探索区域的面积
            unexplored_area = np.sum(unexplored > 0)

            if unexplored_area < self.min_unexplored_area:
                logger.debug(f"未探索区域面积过小: {unexplored_area} < {self.min_unexplored_area}")
                return None

            # 计算未探索区域的质心
            moments = cv2.moments(unexplored)
            if moments['m00'] > 0:
                cx = int(moments['m10'] / moments['m00'])
                cy = int(moments['m01'] / moments['m00'])
                logger.debug(f"检测到未探索区域质心: ({cx}, {cy}), 面积: {unexplored_area}")
                return (cx, cy)

            return None

        except Exception as e:
            logger.error(f"检测未探索区域失败: {e}", exc_info=True)
            return None

    def calculate_direction_to_unexplored(
        self, minimap_img: Image.Image
    ) -> Optional[Tuple[float, float]]:
        """
        计算从小地图中心到未探索区域的方向向量

        Args:
            minimap_img: 小地图图像

        Returns:
            归一化的方向向量 (dx, dy)，如果没有未探索区域则返回 None
        """
        unexplored_center = self.detect_unexplored_areas(minimap_img)
        if unexplored_center is None:
            return None

        # 小地图中心坐标
        h, w = minimap_img.size[1], minimap_img.size[0]
        center_x, center_y = w / 2, h / 2

        # 计算方向向量
        dx = unexplored_center[0] - center_x
        dy = unexplored_center[1] - center_y

        # 归一化
        length = np.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            return None

        dx_norm = dx / length
        dy_norm = dy / length

        logger.debug(f"未探索区域方向: ({dx_norm:.2f}, {dy_norm:.2f})")
        return (dx_norm, dy_norm)

    def is_minimap_fully_explored(self, minimap_img: Image.Image) -> bool:
        """
        判断小地图是否已经全部探索完毕

        Args:
            minimap_img: 小地图图像

        Returns:
            True 如果已全部探索，False 否则
        """
        unexplored_center = self.detect_unexplored_areas(minimap_img)
        return unexplored_center is None

    def get_minimap_fingerprint(self, minimap_img: Image.Image) -> np.ndarray:
        """
        获取小地图的位置指纹（用于卡死检测）

        Args:
            minimap_img: 小地图图像

        Returns:
            小地图的指纹（32x32灰度图）
        """
        img_array = np.array(minimap_img)

        # 转换为灰度图
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # 缩放到32x32
        fingerprint = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
        return fingerprint.astype(np.float32)

    def compare_fingerprints(self, fp1: np.ndarray, fp2: np.ndarray) -> float:
        """
        比较两个小地图指纹的相似度

        Args:
            fp1: 指纹1
            fp2: 指纹2

        Returns:
            相似度（0-1），1表示完全相同，0表示完全不同
        """
        diff = np.abs(fp1 - fp2)
        mean_diff = np.mean(diff) / 255.0
        similarity = 1.0 - mean_diff
        return similarity

