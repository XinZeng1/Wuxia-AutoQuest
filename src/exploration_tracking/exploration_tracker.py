"""
探索度跟踪模块
"""
from PIL import Image
from typing import Optional, Tuple
import re
from src.ui_interaction.screenshot import Screenshot
from src.ui_interaction.ocr import OCR
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class ExplorationTracker:
    """探索度跟踪类"""
    
    def __init__(self):
        """初始化探索度跟踪器"""
        self.config = get_config()
        self.screenshot = Screenshot()
        self.ocr = OCR()
        self.target = self.config.get('game.exploration_target', 100)
        
        # 探索度文本区域（需要根据实际游戏界面调整）
        # 这些坐标是相对于窗口的
        # 可以从配置文件加载
        exploration_config = self.config.get('exploration', {})
        text_region = exploration_config.get('text_region', {})
        
        if text_region:
            self.exploration_text_region = text_region
        else:
            # 默认值（需要根据实际界面调整）
            self.exploration_text_region = {
                'left': 40,  # 需要根据实际界面调整
                'top': 30,   # 需要根据实际界面调整
                'width': 90,
                'height': 40
            }
    
    def get_exploration_text_region(self) -> dict:
        """
        获取探索度文本区域配置
        
        Returns:
            区域字典
        """
        return self.exploration_text_region
    
    def set_exploration_text_region(self, left: int, top: int, width: int, height: int):
        """
        设置探索度文本区域
        
        Args:
            left: 左边界
            top: 上边界
            width: 宽度
            height: 高度
        """
        self.exploration_text_region = {
            'left': left,
            'top': top,
            'width': width,
            'height': height
        }
        logger.info(f"设置探索度文本区域: {self.exploration_text_region}")
    
    def recognize_exploration_text(self, screenshot: Optional[Image.Image] = None, save_debug: bool = False, check_combat: bool = True) -> str:
        """
        识别探索度文本
        
        Args:
            screenshot: 屏幕截图，如果为None则重新截图
            save_debug: 是否保存预处理后的图像用于调试
            check_combat: 是否在识别失败时检查战斗状态（默认True）
        
        Returns:
            识别的文本（如 "探索度 36%"）
        """
        if screenshot is None:
            screenshot = self.screenshot.capture_full_window()
        
        try:
            # 获取截图实际尺寸
            screenshot_width, screenshot_height = screenshot.size
            
            # 获取配置的窗口尺寸（用于计算缩放比例）
            window = self.config.window
            config_width = window.get('width', screenshot_width)
            config_height = window.get('height', screenshot_height)
            
            # 计算缩放比例（Retina截图可能是2x分辨率）
            scale_x = screenshot_width / config_width if config_width > 0 else 1.0
            scale_y = screenshot_height / config_height if config_height > 0 else 1.0
            
            # 裁剪探索度文本区域（坐标相对于窗口截图，需要考虑缩放）
            region = self.exploration_text_region
            left = int(region['left'] * scale_x)
            top = int(region['top'] * scale_y)
            right = int((region['left'] + region['width']) * scale_x)
            bottom = int((region['top'] + region['height']) * scale_y)
            
            # 边界检查
            if left < 0:
                logger.debug(f"探索度检测区域左边界超出截图范围: {left} < 0，已调整为0")
                left = 0
            if top < 0:
                logger.debug(f"探索度检测区域上边界超出截图范围: {top} < 0，已调整为0")
                top = 0
            if right > screenshot_width:
                logger.debug(f"探索度检测区域右边界超出截图范围: {right} > {screenshot_width}，已调整为{screenshot_width}")
                right = screenshot_width
            if bottom > screenshot_height:
                logger.debug(f"探索度检测区域下边界超出截图范围: {bottom} > {screenshot_height}，已调整为{screenshot_height}")
                bottom = screenshot_height
            
            # 确保区域有效
            if right <= left or bottom <= top:
                logger.error(f"探索度检测区域无效: ({left}, {top}, {right}, {bottom})，截图尺寸: {screenshot_width}x{screenshot_height}")
                return ""
            
            logger.info(f"探索度检测 - 截图尺寸: {screenshot_width}x{screenshot_height}, 配置窗口: {config_width}x{config_height}, 缩放: {scale_x:.2f}x{scale_y:.2f}")
            logger.info(f"探索度检测 - 配置区域: ({region['left']}, {region['top']}) - ({region['left'] + region['width']}, {region['top'] + region['height']})")
            logger.info(f"探索度检测 - 实际裁剪: ({left}, {top}) - ({right}, {bottom}), 大小: {right - left}x{bottom - top}")
            
            cropped = screenshot.crop((left, top, right, bottom))
            
            # OCR识别（传递save_debug参数）
            text = self.ocr.recognize(cropped, save_debug=save_debug)
            logger.info(f"识别到的探索度文本: '{text}'")
            
            # 如果识别失败，先检查是否在战斗中（战斗界面会遮挡探索度文本）
            if not text or text.strip() == '':
                is_in_combat = False
                if check_combat:
                    try:
                        from src.core.combat_state import CombatStateDetector
                        combat_detector = CombatStateDetector()
                        is_in_combat = combat_detector.is_in_combat(screenshot)
                    except Exception as e:
                        logger.debug(f"检查战斗状态时出错: {e}")
                
                # 仅在确认不在战斗状态下才输出警告日志
                if not is_in_combat:
                    logger.warning(f"⚠️  探索度文本识别失败，可能原因：")
                    logger.warning(f"   1. 检测区域不包含'探索度'文字")
                    logger.warning(f"   2. OCR识别失败（图像质量或预处理问题）")
                    logger.warning(f"   3. 检测区域配置不正确")
                else:
                    logger.debug("探索度文本识别失败，但检测到战斗状态（战斗界面遮挡探索度文本是正常现象）")
            
            return text
        except Exception as e:
            logger.error(f"探索度文本识别失败: {e}", exc_info=True)
            return ""
    
    def parse_exploration_value(self, text: Optional[str] = None) -> Optional[int]:
        """
        从文本中解析探索度数值
        
        Args:
            text: 探索度文本，如果为None则自动识别
        
        Returns:
            探索度百分比（0-100），如果识别失败返回None
        """
        if text is None:
            text = self.recognize_exploration_text()
        
        if not text:
            # 不在这里输出警告，因为 recognize_exploration_text 已经处理了
            logger.debug("无法识别探索度文本")
            return None
        
        # 清理文本：移除空格和特殊字符
        text_clean = text.strip().replace(' ', '').replace('　', '')
        
        # 使用正则表达式提取数字
        # 匹配 "探索度 36%" 或 "36%" 等格式
        patterns = [
            r'探索度\s*(\d+)%?',  # 探索度 36% 或 探索度36
            r'探索度\s*(\d+)',     # 探索度 36
            r'(\d+)%',             # 36%
            r'(\d+)',              # 36
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text_clean)
            if match:
                try:
                    value_str = match.group(1)
                    value = int(value_str)
                    
                    # 处理OCR错误：如果识别成很大的数字（如2596），可能是25%被识别错了
                    # 优先取前两位数字（如2596取25）
                    if value > 100:
                        # 优先提取前两位数字
                        # 例如：2596 -> 25, 3696 -> 36
                        first_two = value // 100
                        if 0 <= first_two <= 100:
                            logger.debug(f"OCR可能误识别%符号，从 {value} 提取前两位 {first_two}%")
                            value = first_two
                        else:
                            # 如果前两位不合理，尝试最后两位
                            last_two = value % 100
                            if 0 <= last_two <= 100:
                                logger.debug(f"OCR可能误识别%符号，从 {value} 提取最后两位 {last_two}%")
                                value = last_two
                            else:
                                logger.warning(f"探索度值超出范围且无法修正: {value}")
                                continue
                    
                    # 确保值在合理范围内
                    if 0 <= value <= 100:
                        logger.debug(f"解析探索度: {value}%")
                        return value
                    else:
                        logger.warning(f"探索度值超出范围: {value}")
                except ValueError:
                    continue
        
        # 如果所有模式都失败，尝试更宽松的匹配
        # 提取所有数字，选择最合理的
        all_numbers = re.findall(r'\d+', text_clean)
        for num_str in all_numbers:
            try:
                num = int(num_str)
                # 如果数字在合理范围内，使用它
                if 0 <= num <= 100:
                    logger.debug(f"从文本中提取探索度: {num}% (宽松匹配)")
                    return num
                # 如果数字很大，优先提取前两位
                elif num > 100:
                    first_two = num // 100
                    if 0 <= first_two <= 100:
                        logger.debug(f"从大数字 {num} 提取前两位探索度: {first_two}%")
                        return first_two
                    # 如果前两位不合理，尝试最后两位
                    last_two = num % 100
                    if 0 <= last_two <= 100:
                        logger.debug(f"从大数字 {num} 提取最后两位探索度: {last_two}%")
                        return last_two
            except ValueError:
                continue
        
        logger.warning(f"无法从文本中解析探索度: {text}")
        return None
    
    def get_current_exploration(self) -> Optional[int]:
        """
        获取当前探索度
        
        Returns:
            当前探索度百分比，如果识别失败返回None
        """
        return self.parse_exploration_value()
    
    def is_exploration_complete(self, current: Optional[int] = None) -> bool:
        """
        判断探索度是否达到目标
        
        Args:
            current: 当前探索度，如果为None则自动获取
        
        Returns:
            是否达到目标
        """
        if current is None:
            current = self.get_current_exploration()
        
        if current is None:
            return False
        
        is_complete = current >= self.target
        if is_complete:
            logger.info(f"探索度达到目标: {current}% >= {self.target}%")
        else:
            logger.debug(f"探索度未达到目标: {current}% < {self.target}%")
        
        return is_complete
    
    def set_target(self, target: int):
        """
        设置探索度目标
        
        Args:
            target: 目标百分比（0-100）
        """
        if 0 <= target <= 100:
            self.target = target
            logger.info(f"设置探索度目标: {target}%")
        else:
            logger.error(f"无效的探索度目标: {target}")
