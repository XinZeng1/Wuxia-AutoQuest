"""
鼠标控制模块
"""
import pyautogui
import time
from typing import Tuple
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)

# 设置pyautogui的安全设置
pyautogui.FAILSAFE = True  # 鼠标移到屏幕左上角会触发异常
pyautogui.PAUSE = 0.1  # 每次操作后暂停0.1秒


class MouseControl:
    """鼠标控制类"""
    
    def __init__(self):
        """初始化鼠标控制"""
        self.config = get_config()
        self._window_offset = (0, 0)
        self._update_window_offset()
    
    def _update_window_offset(self):
        """更新窗口偏移量"""
        window = self.config.window
        self._window_offset = (window.get('x', 0), window.get('y', 0))
        logger.debug(f"窗口偏移量: {self._window_offset}")
    
    def _to_screen_coords(self, x: int, y: int) -> Tuple[int, int]:
        """
        将游戏内坐标转换为屏幕坐标
        
        Args:
            x: 游戏内x坐标
            y: 游戏内y坐标
        
        Returns:
            (screen_x, screen_y) 屏幕坐标
        """
        screen_x = x + self._window_offset[0]
        screen_y = y + self._window_offset[1]
        return (screen_x, screen_y)
    
    def click(self, x: int, y: int, button: str = 'left', delay: float = None):
        """
        在指定坐标点击
        
        Args:
            x: 游戏内x坐标（相对于窗口）
            y: 游戏内y坐标（相对于窗口）
            button: 鼠标按钮 ('left', 'right', 'middle')
            delay: 点击延迟（秒），如果为None则使用配置中的值
        """
        screen_x, screen_y = self._to_screen_coords(x, y)
        
        # 验证坐标是否在合理范围内
        window = self.config.window
        window_width = window.get('width', 1920)
        window_height = window.get('height', 1080)
        
        if x < 0 or x >= window_width or y < 0 or y >= window_height:
            logger.warning(f"坐标超出窗口范围: ({x}, {y}), 窗口尺寸: {window_width}x{window_height}")
            logger.warning(f"将坐标限制在窗口范围内")
            x = max(0, min(x, window_width - 1))
            y = max(0, min(y, window_height - 1))
            screen_x, screen_y = self._to_screen_coords(x, y)
        
        if delay is None:
            delay = self.config.get('game.move_click_delay', 0.5)
        
        try:
            logger.info(f"点击坐标: 游戏内({x}, {y}) -> 屏幕坐标: ({screen_x}, {screen_y})")
            pyautogui.click(screen_x, screen_y, button=button)
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            logger.error(f"点击失败: {e}")
            raise
    
    def move(self, x: int, y: int):
        """
        移动鼠标到指定坐标（不点击）
        
        Args:
            x: 游戏内x坐标
            y: 游戏内y坐标
        """
        screen_x, screen_y = self._to_screen_coords(x, y)
        try:
            pyautogui.moveTo(screen_x, screen_y)
        except Exception as e:
            logger.error(f"移动鼠标失败: {e}")
            raise
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
        """
        拖拽操作
        
        Args:
            start_x: 起始x坐标
            start_y: 起始y坐标
            end_x: 结束x坐标
            end_y: 结束y坐标
            duration: 拖拽持续时间（秒）
        """
        start_screen = self._to_screen_coords(start_x, start_y)
        end_screen = self._to_screen_coords(end_x, end_y)
        
        try:
            pyautogui.drag(
                end_screen[0] - start_screen[0],
                end_screen[1] - start_screen[1],
                duration=duration,
                button='left'
            )
        except Exception as e:
            logger.error(f"拖拽失败: {e}")
            raise
    
    def update_config(self):
        """更新配置（当配置文件改变时调用）"""
        self._update_window_offset()
