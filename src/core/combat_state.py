"""
战斗状态检测模块
"""
from PIL import Image
from typing import Optional
from src.ui_interaction.screenshot import Screenshot
from src.ui_interaction.image_match import ImageMatcher
from src.ui_interaction.ocr import OCR
from src.core.config import get_config
from src.core.logger import get_logger
import time

logger = get_logger(__name__)


class CombatStateDetector:
    """战斗状态检测类"""
    
    def __init__(self):
        """初始化战斗状态检测器"""
        self.config = get_config()
        self.screenshot = Screenshot()
        self.matcher = ImageMatcher()
        # 不再使用OCR类，直接使用EasyOCR（参考怪物检测）
        # self.ocr = OCR()
        
        # 检测方法配置：'ocr', 'template', 或 'both'
        self.detection_method = self.config.get('combat.detection_method', 'ocr')
        
        # 战斗界面特征模板（需要根据实际游戏界面配置）
        self.combat_template = "combat_ui.png"  # 战斗界面特征
        self.map_template = "map_ui.png"  # 地图界面特征
        
        # OCR检测配置
        # 注意：detection_region 的坐标是相对于游戏窗口的，不是屏幕坐标
        # 例如：如果窗口在屏幕 (100, 400)，窗口大小 674x316
        # 那么 detection_region 的 left=506 表示窗口内从左边界向右506像素的位置
        combat_config = self.config.get('combat', {})
        detection_region = combat_config.get('detection_region', {})
        
        if detection_region:
            self.detection_region = detection_region
        else:
            # 默认区域：窗口右边（需要根据实际界面调整）
            window = self.config.window
            window_width = window.get('width', 674)
            window_height = window.get('height', 316)
            # 默认：右边区域，宽度约20%，高度约30%，居中
            self.detection_region = {
                'left': int(window_width * 0.75),  # 从窗口75%位置开始
                'top': int(window_height * 0.35),   # 从窗口35%位置开始
                'width': int(window_width * 0.2),  # 宽度20%
                'height': int(window_height * 0.3)  # 高度30%
            }
        
        # OCR识别关键词
        self.combat_keywords = combat_config.get('keywords', ['认输'])
    
    def _detect_by_ocr(self, screenshot: Image.Image) -> bool:
        """
        使用OCR识别"认输"文字来检测战斗状态
        
        Args:
            screenshot: 窗口截图（capture_full_window返回的，坐标相对于窗口）
        
        Returns:
            是否在战斗中
        """
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
            
            # 裁剪检测区域（坐标相对于窗口截图，需要考虑缩放）
            region = self.detection_region
            left = int(region['left'] * scale_x)
            top = int(region['top'] * scale_y)
            right = int((region['left'] + region['width']) * scale_x)
            bottom = int((region['top'] + region['height']) * scale_y)
            
            # 边界检查
            if left < 0:
                logger.warning(f"检测区域左边界超出截图范围: {left} < 0，已调整为0")
                left = 0
            if top < 0:
                logger.warning(f"检测区域上边界超出截图范围: {top} < 0，已调整为0")
                top = 0
            if right > screenshot_width:
                logger.warning(f"检测区域右边界超出截图范围: {right} > {screenshot_width}，已调整为{screenshot_width}")
                right = screenshot_width
            if bottom > screenshot_height:
                logger.warning(f"检测区域下边界超出截图范围: {bottom} > {screenshot_height}，已调整为{screenshot_height}")
                bottom = screenshot_height
            
            # 确保区域有效
            if right <= left or bottom <= top:
                logger.error(f"检测区域无效: ({left}, {top}, {right}, {bottom})，截图尺寸: {screenshot_width}x{screenshot_height}")
                return False
            
            cropped = screenshot.crop((left, top, right, bottom))
            
            # 参考怪物检测的逻辑：直接使用EasyOCR的readtext方法
            try:
                import easyocr
                import numpy as np
                
                # 初始化easyocr（只初始化一次）
                if not hasattr(self, '_easyocr_reader'):
                    logger.debug("初始化EasyOCR...")
                    self._easyocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
                
                # 转换为numpy数组
                img_array = np.array(cropped)
                
                # 使用easyocr识别（参考怪物检测，不依赖置信度阈值过滤）
                results = self._easyocr_reader.readtext(img_array)
                
                # 遍历所有识别结果，检查是否包含战斗关键词（参考怪物检测逻辑）
                for (bbox, text, conf) in results:
                    # 检查是否包含战斗关键词（不依赖置信度阈值，只要包含关键词就认为在战斗）
                    for keyword in self.combat_keywords:
                        if keyword in text:
                            logger.debug(f"检测到战斗关键词: '{keyword}' (文本: '{text}')")
                            return True
                
                logger.debug(f"未检测到战斗关键词，识别到 {len(results)} 个文本块")
                return False
                
            except ImportError:
                logger.error("EasyOCR未安装，请运行: pip install easyocr")
                return False
            except Exception as e:
                logger.error(f"EasyOCR战斗检测失败: {e}", exc_info=True)
                return False
        except Exception as e:
            logger.error(f"OCR战斗检测失败: {e}", exc_info=True)
            return False
    
    def _detect_by_template(self, screenshot: Image.Image) -> bool:
        """
        使用模板匹配检测战斗状态
        
        Args:
            screenshot: 屏幕截图
        
        Returns:
            是否在战斗中
        """
        # 方法1：检测战斗界面特征
        if self.combat_template:
            match = self.matcher.match_template(
                screenshot,
                self.combat_template,
                threshold=0.7  # 战斗界面检测可以降低阈值
            )
            if match:
                logger.debug("检测到战斗界面（模板匹配）")
                return True
        
        # 方法2：检测是否不在地图界面（作为补充判断）
        if self.map_template:
            match = self.matcher.match_template(
                screenshot,
                self.map_template,
                threshold=0.7
            )
            if not match:
                logger.debug("未检测到地图界面，可能在战斗中（模板匹配）")
                return True
        
        return False
    
    def is_in_combat(self, screenshot: Optional[Image.Image] = None) -> bool:
        """
        检测是否在战斗中
        
        Args:
            screenshot: 屏幕截图，如果为None则重新截图
        
        Returns:
            是否在战斗中
        """
        if screenshot is None:
            screenshot = self.screenshot.capture_full_window()
        
        # 根据配置的检测方法进行检测
        if self.detection_method == 'ocr':
            return self._detect_by_ocr(screenshot)
        elif self.detection_method == 'template':
            return self._detect_by_template(screenshot)
        elif self.detection_method == 'both':
            # 两种方法都尝试，任一成功即返回True
            ocr_result = self._detect_by_ocr(screenshot)
            template_result = self._detect_by_template(screenshot)
            return ocr_result or template_result
        else:
            # 默认使用OCR
            logger.warning(f"未知的检测方法: {self.detection_method}，使用OCR")
            return self._detect_by_ocr(screenshot)
    
    def wait_for_combat_end(
        self,
        timeout: Optional[int] = None,
        check_interval: Optional[float] = None
    ) -> bool:
        """
        等待战斗结束
        
        Args:
            timeout: 超时时间（秒），如果为None则使用配置中的值
            check_interval: 检查间隔（秒），如果为None则使用配置中的值（默认1秒）
        
        Returns:
            是否成功等待到战斗结束（True）或超时（False）
        """
        if timeout is None:
            timeout = self.config.get('game.battle_timeout', 300)
        
        if check_interval is None:
            check_interval = self.config.get('combat.check_interval', 1.0)
        
        logger.info(f"等待战斗结束，超时时间: {timeout}秒，检查间隔: {check_interval}秒")
        start_time = time.time()
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > timeout:
                logger.warning(f"战斗等待超时: {timeout}秒")
                return False
            
            if not self.is_in_combat():
                logger.info(f"战斗结束，耗时: {elapsed:.1f}秒")
                return True
            
            time.sleep(check_interval)
    
    def set_combat_template(self, template_path: str):
        """
        设置战斗界面模板
        
        Args:
            template_path: 模板文件路径
        """
        self.combat_template = template_path
        logger.info(f"设置战斗界面模板: {template_path}")
    
    def set_map_template(self, template_path: str):
        """
        设置地图界面模板
        
        Args:
            template_path: 模板文件路径
        """
        self.map_template = template_path
        logger.info(f"设置地图界面模板: {template_path}")
    
    def set_detection_region(self, left: int, top: int, width: int, height: int):
        """
        设置战斗检测区域
        
        Args:
            left: 左边界（相对于游戏窗口，不是屏幕坐标）
            top: 上边界（相对于游戏窗口，不是屏幕坐标）
            width: 宽度
            height: 高度
        
        注意：坐标是相对于游戏窗口的，例如：
        - 如果窗口在屏幕 (100, 400)，窗口大小 674x316
        - 那么 left=506 表示窗口内从左边界向右506像素的位置
        - 不是屏幕坐标 606 (100+506)
        """
        self.detection_region = {
            'left': left,
            'top': top,
            'width': width,
            'height': height
        }
        logger.info(f"设置战斗检测区域: {self.detection_region}")
    
    def get_detection_region(self) -> dict:
        """
        获取战斗检测区域配置
        
        Returns:
            区域字典
        """
        return self.detection_region.copy()
