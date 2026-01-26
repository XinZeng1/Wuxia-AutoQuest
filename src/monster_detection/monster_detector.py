"""
怪物检测模块
"""
from PIL import Image, ImageDraw, ImageFont
from typing import List, Tuple, Optional, Dict
import re
import numpy as np
from src.ui_interaction.screenshot import Screenshot
from src.ui_interaction.image_match import ImageMatcher
from src.ui_interaction.ocr import OCR
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class MonsterDetector:
    """怪物检测类"""
    
    def __init__(self):
        """初始化怪物检测器"""
        self.config = get_config()
        self.screenshot = Screenshot()
        self.matcher = ImageMatcher()
        self.ocr = OCR()
        
        # 怪物模板路径（需要在templates目录下放置怪物图标模板）
        # 支持多个模板（列表形式）
        monster_templates = self.config.get('monster.templates', ["monster.png"])
        if isinstance(monster_templates, str):
            self.monster_templates = [monster_templates]
        else:
            self.monster_templates = monster_templates
        self.monster_template = self.monster_templates[0]  # 默认使用第一个
        
        # 检测方法配置
        self.detection_method = self.config.get('monster.detection_method', 'name')  # 'name' 或 'template'
        
        # 怪物名称关键词列表（用于匹配）
        monster_names = self.config.get('monster.name_keywords', [])
        if isinstance(monster_names, str):
            self.monster_name_keywords = [monster_names]
        else:
            self.monster_name_keywords = monster_names if monster_names else [
                '白虎', '兖州', '大盗', '巡查', '堂主', '党', '怪物', '敌人'
            ]
    
    def set_monster_template(self, template_path: str):
        """
        设置怪物模板路径
        
        Args:
            template_path: 模板文件路径（相对于templates目录或绝对路径）
        """
        self.monster_template = template_path
        logger.info(f"设置怪物模板: {template_path}")
    
    def detect_monsters(
        self,
        screenshot: Optional[Image.Image] = None,
        template_path: Optional[str] = None,
        use_all_templates: bool = True,
        method: Optional[str] = None
    ) -> List[Tuple[int, int, float]]:
        """
        检测地图上的怪物
        
        Args:
            screenshot: 屏幕截图，如果为None则重新截图
            template_path: 怪物模板路径，如果为None则使用默认模板
            use_all_templates: 是否使用所有配置的模板
            method: 检测方法 ('name' 或 'template')，如果为None则使用配置的方法
        
        Returns:
            怪物位置列表，每个元素是 (x, y, confidence) 元组
            x, y是相对于窗口的坐标
        """
        if screenshot is None:
            screenshot = self.screenshot.capture_full_window()
        
        # 确定使用的检测方法
        detection_method = method if method is not None else self.detection_method
        
        if detection_method == 'name':
            return self._detect_monsters_by_name(screenshot)
        else:
            return self._detect_monsters_by_template(screenshot, template_path, use_all_templates)
    
    def _preprocess_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        预处理图像以提高OCR识别率（针对怪物名称）
        使用轻量预处理，避免过度处理导致模糊
        
        Args:
            image: PIL Image对象
        
        Returns:
            预处理后的PIL Image对象
        """
        import cv2
        
        # 获取预处理配置
        preprocess_mode = self.config.get('monster.ocr_preprocess_mode', 'light')
        # 'none': 不预处理
        # 'light': 轻量预处理（只轻微增强对比度）
        # 'medium': 中等预处理（轻微放大+对比度增强）
        # 'heavy': 重度预处理（放大+对比度+锐化）
        
        if preprocess_mode == 'none':
            # 直接转换为灰度图，不进行其他处理
            img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            return Image.fromarray(gray)
        
        # 转换为OpenCV格式
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # 转换为灰度图
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        if preprocess_mode == 'light':
            # 只轻微增强对比度，不放大，不锐化
            clahe = cv2.createCLAHE(clipLimit=1.2, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
            return Image.fromarray(gray)
        
        # medium 或 heavy 模式才进行放大
        height, width = gray.shape
        
        if preprocess_mode == 'medium':
            # 轻微放大（只对很小的图像放大）
            if width < 500:
                scale_factor = 1.5
            elif width < 800:
                scale_factor = 1.2
            else:
                scale_factor = 1.0  # 不放大
        else:  # heavy
            # 更激进的放大
            if width < 600:
                scale_factor = 2.0
            elif width < 1000:
                scale_factor = 1.5
            else:
                scale_factor = 1.2
        
        if scale_factor > 1.0:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            # 使用高质量插值
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # 增强对比度
        if preprocess_mode == 'medium':
            clahe = cv2.createCLAHE(clipLimit=1.3, tileGridSize=(8, 8))
        else:  # heavy
            clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        
        # 只有heavy模式才锐化
        if preprocess_mode == 'heavy':
            # 非常轻微的锐化
            kernel_sharpen = np.array([[0, -0.3, 0],
                                       [-0.3, 2.2, -0.3],
                                       [0, -0.3, 0]])
            gray = cv2.filter2D(gray, -1, kernel_sharpen)
        
        # 转换为PIL Image
        return Image.fromarray(gray)
    
    def _detect_monsters_by_name(
        self,
        screenshot: Image.Image
    ) -> List[Tuple[int, int, float]]:
        """
        通过OCR识别怪物名称来检测怪物
        
        Args:
            screenshot: 屏幕截图
        
        Returns:
            怪物位置列表，每个元素是 (x, y, confidence) 元组
        """
        logger.debug("使用OCR识别怪物名称...")
        
        # 尝试使用easyocr或pytesseract
        ocr_engine = self.config.get('recognition.ocr.engine', 'pytesseract')
        
        if ocr_engine == 'easyocr':
            return self._detect_monsters_with_easyocr(screenshot)
        else:
            return self._detect_monsters_with_pytesseract(screenshot)
    
    def _detect_monsters_with_easyocr(self, screenshot: Image.Image) -> List[Tuple[int, int, float]]:
        """
        使用easyocr识别怪物名称
        """
        logger.debug("使用EasyOCR识别怪物名称...")
        
        try:
            import easyocr
            import numpy as np
            
            # 初始化easyocr（只初始化一次）
            if not hasattr(self, '_easyocr_reader'):
                logger.debug("初始化EasyOCR...")
                self._easyocr_reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
            
            # 转换为numpy数组
            img_array = np.array(screenshot)
            
            # 获取窗口实际尺寸（用于坐标缩放）
            window_width = self.screenshot.get_window_size()[0]
            window_height = self.screenshot.get_window_size()[1]
            
            # 检查是否需要缩放坐标（Retina截图可能返回2x分辨率）
            scale_x = window_width / screenshot.width if screenshot.width > 0 else 1.0
            scale_y = window_height / screenshot.height if screenshot.height > 0 else 1.0
            
            logger.debug(f"截图尺寸: {screenshot.width}x{screenshot.height}, 窗口尺寸: {window_width}x{window_height}")
            logger.debug(f"坐标缩放因子: x={scale_x:.2f}, y={scale_y:.2f}")
            
            # 使用easyocr识别
            results = self._easyocr_reader.readtext(img_array)
            
            monsters = []
            for (bbox, text, conf) in results:
                # bbox是四个点的坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                # 计算文本中心位置
                x_coords = [point[0] for point in bbox]
                y_coords = [point[1] for point in bbox]
                text_x = int(sum(x_coords) / len(x_coords))
                text_y = int(sum(y_coords) / len(y_coords))
                
                # 缩放坐标到窗口尺寸（如果截图是Retina 2x，需要除以2）
                text_x = int(text_x * scale_x)
                text_y = int(text_y * scale_y)
                
                # 计算文本宽度和高度（用于推断怪物位置）
                text_w = int((max(x_coords) - min(x_coords)) * scale_x)
                text_h = int((max(y_coords) - min(y_coords)) * scale_y)
                
                # 检查文本是否包含怪物名称关键词
                is_monster_name = False
                for keyword in self.monster_name_keywords:
                    if keyword in text:
                        is_monster_name = True
                        break
                
                # 也检查是否包含等级信息
                if not is_monster_name:
                    if re.search(r'\d+级|Lv\d+', text):
                        if len(text) > 2:
                            is_monster_name = True
                
                if is_monster_name:
                    # 怪物位置在文字中间下面5px左右
                    # 文字中心Y = text_y + text_h / 2
                    # 文字中心下方5px = text_y + text_h / 2 + 5
                    text_center_y = text_y + text_h / 2
                    monster_x = text_x
                    monster_y = int(text_center_y + 40 * scale_y)  # 文字中心下方5px（按比例缩放）
                    
                    # 检查坐标是否在窗口范围内（使用窗口尺寸，不是截图尺寸）
                    if 0 <= monster_x < window_width and 0 <= monster_y < window_height:
                        confidence = float(conf)
                        monsters.append((monster_x, monster_y, confidence))
                        logger.debug(f"检测到怪物名称: '{text}' 位置({monster_x}, {monster_y}), 置信度: {conf:.3f}")
                    else:
                        logger.warning(f"怪物位置超出窗口范围: ({monster_x}, {monster_y}), 窗口尺寸: {window_width}x{window_height}")
            
            # 去除重复的匹配
            if monsters:
                filtered_monsters = []
                for monster in monsters:
                    x, y, conf = monster
                    is_duplicate = False
                    for existing in filtered_monsters:
                        ex, ey, _ = existing
                        distance = ((x - ex) ** 2 + (y - ey) ** 2) ** 0.5
                        if distance < 40:
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        filtered_monsters.append(monster)
                
                monsters = filtered_monsters
            
            if monsters:
                logger.info(f"通过EasyOCR识别检测到 {len(monsters)} 个怪物")
                for i, monster in enumerate(monsters[:10]):
                    logger.debug(f"  怪物{i+1}: 位置({monster[0]}, {monster[1]}), 置信度: {monster[2]:.3f}")
            else:
                logger.debug("未检测到任何怪物名称")
            
            return monsters
            
        except ImportError:
            logger.error("EasyOCR未安装，请运行: pip install easyocr")
            return []
        except Exception as e:
            logger.error(f"EasyOCR识别失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _detect_monsters_with_pytesseract(self, screenshot: Image.Image) -> List[Tuple[int, int, float]]:
        """
        使用pytesseract识别怪物名称
        """
        logger.debug("使用pytesseract识别怪物名称...")
        
        try:
            import pytesseract
            
            # 预处理图像以提高识别率
            preprocess_mode = self.config.get('monster.ocr_preprocess_mode', 'light')
            preprocessed = self._preprocess_for_ocr(screenshot)
            
            # 保存预处理后的图像用于调试
            try:
                from pathlib import Path
                debug_path = Path(__file__).parent.parent.parent / "monster_ocr_debug.png"
                preprocessed.save(debug_path)
                logger.debug(f"预处理图像已保存到: {debug_path} (模式: {preprocess_mode})")
            except:
                pass
            
            # 尝试多种OCR配置以提高识别率
            ocr_configs = [
                '--psm 6',  # 单一文本块
                '--psm 11',  # 稀疏文本（适合游戏UI）
                '--psm 12',  # 带OSD的稀疏文本
                '--psm 3',   # 完全自动页面分割
                '--psm 6 -c tessedit_char_whitelist=0123456789级白虎兖州大盗巡查堂主党怪物敌人劫匪',  # 带字符白名单
            ]
            
            all_monsters = []
            all_texts = {}  # 用于去重：{text: (x, y, w, h, conf)}
            
            for config in ocr_configs:
                try:
                    # 使用pytesseract获取详细的OCR结果（包含位置信息）
                    ocr_data = pytesseract.image_to_data(
                        preprocessed,
                        lang=self.ocr.lang,
                        config=config,
                        output_type=pytesseract.Output.DICT
                    )
                    
                    n_boxes = len(ocr_data['text'])
                    
                    for i in range(n_boxes):
                        text = ocr_data['text'][i].strip()
                        conf = float(ocr_data['conf'][i])
                        
                        # 跳过空文本和低置信度文本（降低阈值以识别更多文本）
                        if not text or conf < 20:
                            continue
                        
                        # 检查文本是否包含怪物名称关键词
                        is_monster_name = False
                        matched_keyword = None
                        for keyword in self.monster_name_keywords:
                            if keyword in text:
                                is_monster_name = True
                                matched_keyword = keyword
                                break
                        
                        # 也检查是否包含等级信息（如"47级"、"Lv49"等）
                        level_match = re.search(r'\d+级|Lv\d+', text)
                        if not is_monster_name and level_match:
                            # 如果包含等级，检查前后文本是否可能是怪物名称
                            # 检查文本长度和字符类型
                            if len(text) > 2:  # 至少3个字符才可能是怪物名称+等级
                                is_monster_name = True
                        
                        if is_monster_name:
                            # 获取文本位置（需要根据缩放因子调整）
                            preprocess_mode = self.config.get('monster.ocr_preprocess_mode', 'light')
                            if preprocess_mode == 'none':
                                scale_factor = 1.0
                            elif preprocess_mode == 'light':
                                scale_factor = 1.0
                            elif preprocess_mode == 'medium':
                                if screenshot.width < 500:
                                    scale_factor = 1.5
                                elif screenshot.width < 800:
                                    scale_factor = 1.2
                                else:
                                    scale_factor = 1.0
                            else:  # heavy
                                if screenshot.width < 600:
                                    scale_factor = 2.0
                                elif screenshot.width < 1000:
                                    scale_factor = 1.5
                                else:
                                    scale_factor = 1.2
                            
                            x = int(ocr_data['left'][i] / scale_factor)
                            y = int(ocr_data['top'][i] / scale_factor)
                            w = int(ocr_data['width'][i] / scale_factor)
                            h = int(ocr_data['height'][i] / scale_factor)
                            
                            # 使用文本作为key去重（相同文本只保留置信度最高的）
                            text_key = f"{x}_{y}_{text[:10]}"  # 使用位置和文本前10个字符作为key
                            if text_key not in all_texts:
                                all_texts[text_key] = (text, x, y, w, h, conf)
                            else:
                                # 如果已存在，保留置信度更高的
                                existing_conf = all_texts[text_key][5]
                                if conf > existing_conf:
                                    all_texts[text_key] = (text, x, y, w, h, conf)
                except Exception as e:
                    logger.debug(f"OCR配置 {config} 失败: {e}")
                    continue
            
            # 处理所有识别到的文本
            for text, x, y, w, h, conf in all_texts.values():
                # 怪物位置通常在名称文本的下方中心
                # 假设怪物在名称下方约20-40像素
                monster_x = x + w // 2
                monster_y = y + h + 30  # 名称下方30像素
                
                # 确保位置在截图范围内
                if monster_x < 0 or monster_x >= screenshot.width:
                    continue
                if monster_y < 0 or monster_y >= screenshot.height:
                    continue
                
                # 置信度基于OCR置信度（转换为0-1范围）
                confidence = min(1.0, conf / 100.0)
                
                all_monsters.append((monster_x, monster_y, confidence))
                logger.debug(f"检测到怪物名称: '{text}' 位置({monster_x}, {monster_y}), OCR置信度: {conf:.1f}")
            
            # 去除重复的匹配（基于位置）
            if all_monsters:
                filtered_monsters = []
                for monster in all_monsters:
                    x, y, conf = monster
                    is_duplicate = False
                    for existing in filtered_monsters:
                        ex, ey, _ = existing
                        distance = ((x - ex) ** 2 + (y - ey) ** 2) ** 0.5
                        if distance < 40:  # 如果距离小于40像素，认为是重复
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        filtered_monsters.append(monster)
                
                all_monsters = filtered_monsters
            
            if all_monsters:
                logger.info(f"通过名称识别检测到 {len(all_monsters)} 个怪物")
                for i, monster in enumerate(all_monsters[:10]):  # 显示前10个
                    logger.debug(f"  怪物{i+1}: 位置({monster[0]}, {monster[1]}), 置信度: {monster[2]:.3f}")
            else:
                logger.debug("未检测到任何怪物名称")
                logger.debug(f"尝试的关键词: {self.monster_name_keywords}")
            
            return all_monsters
            
        except Exception as e:
            logger.error(f"OCR识别怪物名称失败: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
    
    def _detect_monsters_by_template(
        self,
        screenshot: Image.Image,
        template_path: Optional[str] = None,
        use_all_templates: bool = True
    ) -> List[Tuple[int, int, float]]:
        """
        通过模板匹配检测怪物（原有方法）
        
        Args:
            screenshot: 屏幕截图
            template_path: 怪物模板路径
            use_all_templates: 是否使用所有配置的模板
        
        Returns:
            怪物位置列表
        """
        all_matches = []
        
        # 确定要使用的模板列表
        if template_path is None:
            if use_all_templates:
                templates_to_try = self.monster_templates
            else:
                templates_to_try = [self.monster_template]
        else:
            templates_to_try = [template_path]
        
        # 使用每个模板进行检测
        for template in templates_to_try:
            logger.debug(f"使用模板 {template} 检测怪物...")
            # 尝试所有方法以提高识别率
            matches = self.matcher.match_all(screenshot, template, try_all_methods=True)
            
            if matches:
                logger.debug(f"模板 {template} 检测到 {len(matches)} 个匹配")
                all_matches.extend(matches)
        
        # 去除重复的匹配（基于位置）
        if all_matches:
            # 按置信度排序
            all_matches.sort(key=lambda x: x[2], reverse=True)
            # 简单的去重：如果两个匹配位置很近，保留置信度更高的
            filtered_matches = []
            for match in all_matches:
                x, y, conf = match
                is_duplicate = False
                for existing in filtered_matches:
                    ex, ey, _ = existing
                    distance = ((x - ex) ** 2 + (y - ey) ** 2) ** 0.5
                    if distance < 20:  # 如果距离小于20像素，认为是重复
                        is_duplicate = True
                        break
                if not is_duplicate:
                    filtered_matches.append(match)
            
            all_matches = filtered_matches
        
        if all_matches:
            logger.info(f"总共检测到 {len(all_matches)} 个怪物")
            for i, match in enumerate(all_matches[:5]):  # 只显示前5个
                logger.debug(f"  匹配{i+1}: 位置({match[0]}, {match[1]}), 置信度: {match[2]:.3f}")
        else:
            logger.debug("未检测到任何怪物匹配")
        
        return all_matches
    
    def select_nearest_monster(
        self,
        current_pos: Optional[Tuple[int, int]],
        monsters: Optional[List[Tuple[int, int, float]]] = None
    ) -> Optional[Tuple[int, int, float]]:
        """
        选择距离当前位置最近的怪物
        
        Args:
            current_pos: 当前位置 (x, y)，如果为None则使用第一个怪物
            monsters: 怪物列表，如果为None则自动检测
        
        Returns:
            最近的怪物 (x, y, confidence)，如果没有怪物返回None
        """
        if monsters is None:
            monsters = self.detect_monsters()
        
        if not monsters:
            logger.debug("没有检测到怪物")
            return None
        
        # 如果没有当前位置，返回第一个怪物（或置信度最高的）
        if current_pos is None:
            logger.debug("未知当前位置，选择第一个怪物")
            # 按置信度排序，选择置信度最高的
            sorted_monsters = sorted(monsters, key=lambda x: x[2], reverse=True)
            return sorted_monsters[0]
        
        # 计算距离并选择最近的
        current_x, current_y = current_pos
        nearest = None
        min_distance = float('inf')
        
        for monster in monsters:
            monster_x, monster_y, confidence = monster
            distance = ((monster_x - current_x) ** 2 + (monster_y - current_y) ** 2) ** 0.5
            
            if distance < min_distance:
                min_distance = distance
                nearest = monster
        
        if nearest:
            logger.info(f"选择最近的怪物: 位置({nearest[0]}, {nearest[1]}), 距离: {min_distance:.1f}")
        
        return nearest
    
    def select_monster_by_strategy(
        self,
        strategy: str = "nearest",
        current_pos: Optional[Tuple[int, int]] = None
    ) -> Optional[Tuple[int, int, float]]:
        """
        根据策略选择怪物
        
        Args:
            strategy: 选择策略 ("nearest" - 最近, "first" - 第一个, "highest_confidence" - 最高置信度)
            current_pos: 当前位置，用于"nearest"策略
        
        Returns:
            选中的怪物 (x, y, confidence)，如果没有怪物返回None
        """
        monsters = self.detect_monsters()
        
        if not monsters:
            return None
        
        if strategy == "nearest":
            if current_pos is None:
                logger.warning("nearest策略需要当前位置，使用first策略")
                strategy = "first"
            else:
                return self.select_nearest_monster(current_pos, monsters)
        
        if strategy == "first":
            return monsters[0]
        
        if strategy == "highest_confidence":
            # 按置信度排序
            sorted_monsters = sorted(monsters, key=lambda x: x[2], reverse=True)
            return sorted_monsters[0]
        
        logger.warning(f"未知的策略: {strategy}, 使用first策略")
        return monsters[0]
