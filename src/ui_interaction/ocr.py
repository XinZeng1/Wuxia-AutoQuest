"""
OCR文本识别模块
"""
import pytesseract
from PIL import Image
import cv2
import numpy as np
from typing import Optional
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class OCR:
    """OCR文本识别类"""
    
    def __init__(self):
        """初始化OCR"""
        self.config = get_config()
        self.engine = self.config.get('recognition.ocr.engine', 'pytesseract')
        self.lang = self.config.get('recognition.ocr.lang', 'chi_sim')
        
        # 配置pytesseract（如果需要）
        if self.engine == 'pytesseract':
            # 可以在这里设置tesseract路径（如果需要）
            # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
            pass
    
    def _preprocess_image(self, image: Image.Image, scale_factor: float = 2.0) -> np.ndarray:
        """
        预处理图像以提高OCR准确率
        
        Args:
            image: PIL Image对象
            scale_factor: 图像放大倍数（小图像需要放大以提高识别率）
        
        Returns:
            处理后的OpenCV图像数组
        """
        # 转换为OpenCV格式
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # 如果图像太小，先放大（使用更高质量的插值）
        height, width = gray.shape
        if width < 100 or height < 30:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            # 使用LANCZOS插值，质量更好但速度稍慢
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 轻微锐化（提高清晰度，但不过度）
        kernel_sharpen = np.array([[-1, -1, -1],
                                   [-1,  9, -1],
                                   [-1, -1, -1]]) / 1.0
        gray = cv2.filter2D(gray, -1, kernel_sharpen)
        
        # 增强对比度（降低强度，减少过度处理）
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))  # 降低clipLimit
        gray = clahe.apply(gray)
        
        # 二值化 - 使用OTSU自适应阈值（通常效果最好）
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 如果OTSU效果不好，尝试固定阈值
        # 计算平均亮度
        mean_brightness = np.mean(binary)
        if mean_brightness > 240:  # 图像很亮，可能是白底黑字
            _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        elif mean_brightness < 15:  # 图像很暗，可能是黑底白字
            _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
        
        # 轻度降噪（减少参数，避免过度模糊）
        binary = cv2.fastNlMeansDenoising(binary, None, h=5, templateWindowSize=7, searchWindowSize=21)
        
        # 形态学操作：轻微处理，去除小噪点（使用更小的核）
        kernel = np.ones((1, 1), np.uint8)  # 减小核大小
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        return binary
    
    def recognize(self, image: Image.Image, lang: Optional[str] = None, save_debug: bool = False) -> str:
        """
        识别图像中的文本
        
        Args:
            image: PIL Image对象
            lang: 语言代码，如果为None则使用配置中的值
            save_debug: 是否保存预处理后的图像用于调试
        
        Returns:
            识别的文本字符串
        """
        if lang is None:
            lang = self.lang
        
        try:
            if self.engine == 'pytesseract':
                # 预处理图像
                processed = self._preprocess_image(image)
                
                # 保存调试图像
                if save_debug:
                    try:
                        from pathlib import Path
                        debug_path = Path(__file__).parent.parent.parent / "ocr_debug.png"
                        Image.fromarray(processed).save(debug_path)
                        logger.debug(f"预处理图像已保存到: {debug_path}")
                    except:
                        pass
                
                # 转换为PIL Image
                processed_pil = Image.fromarray(processed)
                
                # OCR识别 - 尝试多种配置
                # 添加字符白名单，提高%符号识别率
                configs = [
                    '--psm 7 -c tessedit_char_whitelist=探索度0123456789%',  # 单行文本 + 字符白名单
                    '--psm 8 -c tessedit_char_whitelist=探索度0123456789%',  # 单个单词 + 字符白名单
                    '--psm 6 -c tessedit_char_whitelist=探索度0123456789%',  # 单一文本块 + 字符白名单
                    '--psm 7',  # 单行文本（无白名单，作为备选）
                    '--psm 8',  # 单个单词（无白名单，作为备选）
                    '--psm 6',  # 单一文本块（无白名单，作为备选）
                ]
                
                best_text = ""
                for config in configs:
                    try:
                        text = pytesseract.image_to_string(
                            processed_pil,
                            lang=lang,
                            config=config
                        )
                        text = text.strip().replace('\n', ' ').replace('\r', '')
                        if text and len(text) > len(best_text):
                            best_text = text
                    except:
                        continue
                
                # 如果所有配置都失败，使用默认配置
                if not best_text:
                    text = pytesseract.image_to_string(processed_pil, lang=lang)
                    best_text = text.strip().replace('\n', ' ').replace('\r', '')
                
                logger.debug(f"OCR识别结果: {best_text}")
                return best_text
            elif self.engine == 'easyocr':
                # 使用EasyOCR识别
                try:
                    import easyocr
                    import numpy as np
                    
                    # 初始化easyocr（只初始化一次）
                    if not hasattr(self, '_easyocr_reader'):
                        logger.debug("初始化EasyOCR...")
                        self._easyocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
                    
                    # 转换为numpy数组
                    img_array = np.array(image)
                    
                    # 使用easyocr识别
                    results = self._easyocr_reader.readtext(img_array)
                    
                    # 合并所有识别到的文本
                    texts = []
                    for (bbox, text, conf) in results:
                        if conf > 0.3:  # 只保留置信度较高的文本
                            texts.append(text)
                    
                    result_text = ' '.join(texts)
                    logger.debug(f"EasyOCR识别结果: {result_text}")
                    return result_text
                except ImportError:
                    logger.error("EasyOCR未安装，请运行: pip install easyocr")
                    return ""
                except Exception as e:
                    logger.error(f"EasyOCR识别失败: {e}")
                    return ""
            else:
                logger.warning(f"不支持的OCR引擎: {self.engine}")
                return ""
        except Exception as e:
            logger.error(f"OCR识别失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return ""
    
    def recognize_number(self, image: Image.Image) -> Optional[int]:
        """
        识别图像中的数字
        
        Args:
            image: PIL Image对象
        
        Returns:
            识别到的数字，如果识别失败返回None
        """
        text = self.recognize(image, lang='eng')  # 数字用英文识别
        
        # 提取数字
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                pass
        
        return None
