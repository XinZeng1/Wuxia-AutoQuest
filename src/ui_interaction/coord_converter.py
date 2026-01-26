"""
坐标转换模块
"""
from typing import Tuple
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class CoordConverter:
    """坐标转换类"""
    
    def __init__(self):
        """初始化坐标转换器"""
        self.config = get_config()
        self._update_window_info()
    
    def _update_window_info(self):
        """更新窗口信息"""
        window = self.config.window
        self.window_x = window.get('x', 0)
        self.window_y = window.get('y', 0)
        self.window_width = window.get('width', 1920)
        self.window_height = window.get('height', 1080)
    
    def game_to_screen(self, game_x: int, game_y: int) -> Tuple[int, int]:
        """
        将游戏内坐标转换为屏幕坐标
        
        Args:
            game_x: 游戏内x坐标
            game_y: 游戏内y坐标
        
        Returns:
            (screen_x, screen_y) 屏幕坐标
        """
        screen_x = game_x + self.window_x
        screen_y = game_y + self.window_y
        return (screen_x, screen_y)
    
    def screen_to_game(self, screen_x: int, screen_y: int) -> Tuple[int, int]:
        """
        将屏幕坐标转换为游戏内坐标
        
        Args:
            screen_x: 屏幕x坐标
            screen_y: 屏幕y坐标
        
        Returns:
            (game_x, game_y) 游戏内坐标
        """
        game_x = screen_x - self.window_x
        game_y = screen_y - self.window_y
        return (game_x, game_y)
    
    def is_in_window(self, game_x: int, game_y: int) -> bool:
        """
        检查游戏坐标是否在窗口范围内
        
        Args:
            game_x: 游戏内x坐标
            game_y: 游戏内y坐标
        
        Returns:
            是否在窗口内
        """
        return (0 <= game_x < self.window_width and 
                0 <= game_y < self.window_height)
    
    def update_config(self):
        """更新配置（当配置文件改变时调用）"""
        self._update_window_info()
