"""
地图导航模块
"""
from PIL import Image
from typing import Tuple, Optional, List
from src.ui_interaction.screenshot import Screenshot
from src.ui_interaction.mouse_control import MouseControl
from src.ui_interaction.image_match import ImageMatcher
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class MapNavigator:
    """地图导航类"""
    
    def __init__(self):
        """初始化地图导航器"""
        self.config = get_config()
        self.screenshot = Screenshot()
        self.mouse = MouseControl()
        self.matcher = ImageMatcher()
        
        # 角色位置（需要实时更新）
        self.current_position: Optional[Tuple[int, int]] = None
    
    def detect_character_position(
        self,
        screenshot: Optional[Image.Image] = None,
        character_template: str = "character.png"
    ) -> Optional[Tuple[int, int]]:
        """
        检测角色当前位置
        
        由于角色始终保持在屏幕中央，直接返回屏幕中心坐标
        
        Args:
            screenshot: 屏幕截图（未使用，保留以兼容接口）
            character_template: 角色模板路径（未使用，保留以兼容接口）
        
        Returns:
            角色位置 (x, y)，屏幕中心坐标
        """
        # 获取窗口大小
        width, height = self.screenshot.get_window_size()
        
        # 角色在屏幕中央
        center_x = width // 2
        center_y = height // 2
        
        self.current_position = (center_x, center_y)
        logger.debug(f"角色位置（屏幕中心）: ({center_x}, {center_y})")
        return (center_x, center_y)
    
    def move_to(self, target_x: int, target_y: int, delay: float = None):
        """
        控制角色移动到目标位置
        
        Args:
            target_x: 目标x坐标
            target_y: 目标y坐标
            delay: 点击延迟
        """
        logger.info(f"移动到目标位置: ({target_x}, {target_y})")
        self.mouse.click(target_x, target_y, delay=delay)
        
        # 更新当前位置（假设移动成功）
        # 实际应该通过检测来确认
        self.current_position = (target_x, target_y)
    
    def move_to_monster(self, monster_pos: Tuple[int, int, float]):
        """
        移动到怪物位置
        
        Args:
            monster_pos: 怪物位置 (x, y, confidence)
        """
        monster_x, monster_y, _ = monster_pos
        self.move_to(monster_x, monster_y)
    
    def get_current_position(self) -> Optional[Tuple[int, int]]:
        """
        获取当前位置
        
        Returns:
            当前位置 (x, y)，如果未知返回None
        """
        if self.current_position is None:
            # 尝试检测当前位置
            self.detect_character_position()
        
        return self.current_position
    
    def plan_path(
        self,
        start: Tuple[int, int],
        end: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """
        简单的路径规划（直线移动）
        
        Args:
            start: 起始位置 (x, y)
            end: 目标位置 (x, y)
        
        Returns:
            路径点列表（当前实现为直线，后续可以扩展为复杂路径）
        """
        # MVP版本：简单直线移动
        # 后续可以扩展为A*等算法
        return [end]
    
    def navigate_to(
        self,
        target_x: int,
        target_y: int,
        use_path_planning: bool = False
    ):
        """
        导航到目标位置（可选择使用路径规划）
        
        Args:
            target_x: 目标x坐标
            target_y: 目标y坐标
            use_path_planning: 是否使用路径规划
        """
        current = self.get_current_position()
        
        if current is None:
            logger.warning("未知当前位置，直接移动到目标")
            self.move_to(target_x, target_y)
            return
        
        if use_path_planning:
            # 使用路径规划
            path = self.plan_path(current, (target_x, target_y))
            for point in path:
                self.move_to(point[0], point[1])
        else:
            # 直接移动
            self.move_to(target_x, target_y)
