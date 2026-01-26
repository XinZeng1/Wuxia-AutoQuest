"""
屏幕截图模块
"""
import mss
import numpy as np
import cv2
from PIL import Image
from typing import Tuple, Optional
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)

# 尝试导入 Quartz（Mac 专用）
try:
    import Quartz.CoreGraphics as CG
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False
    logger.warning("Quartz.CoreGraphics 未安装，将使用 mss 截图。Mac 上建议安装 pyobjc 以获得更清晰的截图")


class Screenshot:
    """屏幕截图类"""
    
    def __init__(self):
        """初始化截图工具"""
        self.config = get_config()
        self.sct = mss.mss()
        self._window_region = None
        self._use_retina = self.config.get('screenshot.use_retina', True)  # 默认使用 Retina 截图
        self._update_window_region()
    
    def _update_window_region(self):
        """更新窗口区域配置"""
        window = self.config.window
        self._window_region = {
            'left': window.get('x', 0),
            'top': window.get('y', 0),
            'width': window.get('width', 1920),
            'height': window.get('height', 1080)
        }
        logger.debug(f"窗口区域配置: {self._window_region}")
    
    def _capture_mac_retina(self, region: dict) -> Image.Image:
        """
        使用 Mac Retina 截图（高分辨率，更清晰）
        
        Args:
            region: 区域字典，包含 left, top, width, height
        
        Returns:
            PIL Image对象
        """
        if not HAS_QUARTZ:
            raise RuntimeError("Quartz.CoreGraphics 未安装，无法使用 Retina 截图")
        
        try:
            # 1. 创建坐标区域
            rect = CG.CGRectMake(region['left'], region['top'], region['width'], region['height'])
            
            # 2. 截取图像
            image_ref = CG.CGWindowListCreateImage(
                rect, 
                CG.kCGWindowListOptionOnScreenOnly, 
                CG.kCGNullWindowID, 
                CG.kCGWindowImageDefault
            )
            
            if not image_ref:
                raise RuntimeError("无法创建截图")
            
            # 3. 获取关键元数据
            width = CG.CGImageGetWidth(image_ref)
            height = CG.CGImageGetHeight(image_ref)
            bytes_per_row = CG.CGImageGetBytesPerRow(image_ref)  # 关键：获取系统实际的每行字节数
            
            # 4. 提取原始字节数据
            data_provider = CG.CGImageGetDataProvider(image_ref)
            data = CG.CGDataProviderCopyData(data_provider)
            
            # 5. 将数据转为 numpy 数组
            # 先转成包含填充字节的矩阵
            img_np = np.frombuffer(data, dtype=np.uint8).reshape((height, bytes_per_row))
            
            # 6. 切除右侧的填充字节 (Padding)
            # 每个像素 4 字节，实际需要的宽度是 width * 4
            actual_data_width = width * 4
            img_np = img_np[:, :actual_data_width].reshape((height, width, 4))
            
            # 7. 颜色空间转换
            # Quartz 默认通常是 BGRA，我们需要转为 RGB 供 PIL 使用
            img_bgr = cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            
            # 8. 转换为 PIL Image
            return Image.fromarray(img_rgb)
            
        except Exception as e:
            logger.error(f"Retina 截图失败: {e}")
            raise
    
    def capture(self, region: Optional[dict] = None) -> Image.Image:
        """
        截取屏幕指定区域
        
        Args:
            region: 区域字典，包含 left, top, width, height
                   如果为None，则截取整个配置的窗口区域
        
        Returns:
            PIL Image对象
        """
        if region is None:
            region = self._window_region
        else:
            # 如果提供了区域，需要加上窗口的偏移
            window = self.config.window
            region = {
                'left': region.get('left', 0) + window.get('x', 0),
                'top': region.get('top', 0) + window.get('y', 0),
                'width': region.get('width', region.get('left', 0)),
                'height': region.get('height', region.get('top', 0))
            }
        
        # 如果启用 Retina 截图且系统支持，使用 Retina 截图
        if self._use_retina and HAS_QUARTZ:
            try:
                return self._capture_mac_retina(region)
            except Exception as e:
                logger.warning(f"Retina 截图失败，回退到 mss: {e}")
                # 回退到 mss
                pass
        
        # 使用 mss 截图（备选方案）
        try:
            screenshot = self.sct.grab(region)
            # 转换为PIL Image
            img = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            return img
        except Exception as e:
            logger.error(f"截图失败: {e}")
            raise
    
    def capture_full_window(self) -> Image.Image:
        """
        截取整个配置的窗口区域
        
        Returns:
            PIL Image对象
        """
        return self.capture()

    def capture_minimap(self, full_image: Optional[Image.Image] = None) -> Optional[Image.Image]:
        """
        截取小地图区域。严格处理 Retina 2x 像素映射。
        """
        minimap_cfg = self.config.get('minimap') or {}
        if not isinstance(minimap_cfg, dict):
            return None
        region = minimap_cfg.get('region') or {}
        if not region:
            return None
        left = int(region.get('left', 0))
        top = int(region.get('top', 0))
        w = int(region.get('width', 0))
        h = int(region.get('height', 0))
        if w <= 0 or h <= 0:
            return None
        if full_image is None:
            full_image = self.capture_full_window()
        cw, ch = self.get_window_size()
        iw, ih = full_image.size
        sx = iw / max(1, cw)
        sy = ih / max(1, ch)
        x0 = max(0, min(int(left * sx), iw - 1))
        y0 = max(0, min(int(top * sy), ih - 1))
        x1 = max(x0 + 1, min(int((left + w) * sx), iw))
        y1 = max(y0 + 1, min(int((top + h) * sy), ih))
        return full_image.crop((x0, y0, x1, y1))
    
    def get_window_size(self) -> Tuple[int, int]:
        """
        获取窗口大小
        
        Returns:
            (width, height) 元组
        """
        window = self.config.window
        return (window.get('width', 1920), window.get('height', 1080))
    
    def update_config(self):
        """更新配置（当配置文件改变时调用）"""
        self._update_window_region()
