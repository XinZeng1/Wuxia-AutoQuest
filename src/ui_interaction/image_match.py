"""
图像匹配模块
"""
import cv2
import numpy as np
from PIL import Image
from typing import Tuple, Optional, List
from pathlib import Path
from src.core.config import get_config
from src.core.logger import get_logger

logger = get_logger(__name__)


class ImageMatcher:
    """图像匹配类"""
    
    def __init__(self):
        """初始化图像匹配器"""
        self.config = get_config()
        self.template_dir = Path(__file__).parent.parent.parent / "templates"
        self.template_dir.mkdir(parents=True, exist_ok=True)
        self._threshold = self.config.get('recognition.template_match_threshold', 0.8)
        
        # 匹配方法配置
        self.match_methods = {
            'TM_CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'TM_CCORR_NORMED': cv2.TM_CCORR_NORMED,
            'TM_SQDIFF_NORMED': cv2.TM_SQDIFF_NORMED,
        }
        self.enabled_methods = self.config.get('recognition.match_methods', ['TM_CCOEFF_NORMED'])
    
    def _preprocess_image(self, image: np.ndarray, preprocess_options: Optional[dict] = None) -> np.ndarray:
        """
        预处理图像以提高匹配准确率
        
        Args:
            image: OpenCV图像数组
            preprocess_options: 预处理选项字典
        
        Returns:
            预处理后的图像
        """
        if preprocess_options is None:
            preprocess_options = self.config.get('recognition.preprocess', {})
        
        processed = image.copy()
        
        # 灰度化（如果还不是灰度图）
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        
        # 对比度增强
        if preprocess_options.get('enhance_contrast', False):
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            processed = clahe.apply(processed)
        
        # 边缘检测（可选）
        if preprocess_options.get('edge_detection', False):
            processed = cv2.Canny(processed, 50, 150)
        
        # 二值化（可选）
        if preprocess_options.get('binarize', False):
            _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        return processed
    
    def _load_template(self, template_path: str, preprocess: bool = False) -> np.ndarray:
        """
        加载模板图像
        
        Args:
            template_path: 模板图像路径
            preprocess: 是否预处理模板图像
        
        Returns:
            OpenCV图像数组
        """
        if not Path(template_path).is_absolute():
            template_path = self.template_dir / template_path
        
        template_path_obj = Path(template_path)
        if not template_path_obj.exists():
            error_msg = f"模板文件不存在: {template_path}"
            logger.error(error_msg)
            logger.error(f"请确保模板文件存在于: {self.template_dir}")
            raise FileNotFoundError(error_msg)
        
        template = cv2.imread(str(template_path))
        if template is None:
            error_msg = f"无法加载模板图像: {template_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 预处理
        if preprocess:
            template = self._preprocess_image(template)
            if len(template.shape) == 2:
                template = cv2.cvtColor(template, cv2.COLOR_GRAY2BGR)
        
        logger.debug(f"成功加载模板: {template_path}, 尺寸: {template.shape}")
        return template
    
    def match_template(
        self,
        screenshot: Image.Image,
        template_path: str,
        threshold: Optional[float] = None,
        method: int = cv2.TM_CCOEFF_NORMED
    ) -> Optional[Tuple[int, int, float]]:
        """
        在截图中匹配模板
        
        Args:
            screenshot: 屏幕截图（PIL Image）
            template_path: 模板图像路径
            threshold: 匹配阈值，如果为None则使用配置中的值
            method: OpenCV匹配方法
        
        Returns:
            如果找到匹配，返回 (x, y, confidence) 元组，否则返回None
            x, y是匹配位置的中心坐标（相对于截图）
        """
        if threshold is None:
            threshold = self._threshold
        
        try:
            # 加载模板
            template = self._load_template(template_path)
            
            # 转换截图为OpenCV格式
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 模板匹配
            result = cv2.matchTemplate(screenshot_cv, template, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            # 根据匹配方法选择最佳位置
            if method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                match_val = 1 - min_val
                match_loc = min_loc
            else:
                match_val = max_val
                match_loc = max_loc
            
            # 检查是否超过阈值
            if match_val >= threshold:
                # 计算中心坐标
                h, w = template.shape[:2]
                center_x = match_loc[0] + w // 2
                center_y = match_loc[1] + h // 2
                
                logger.debug(
                    f"模板匹配成功: {template_path}, "
                    f"位置: ({center_x}, {center_y}), "
                    f"置信度: {match_val:.3f}"
                )
                return (center_x, center_y, match_val)
            else:
                logger.debug(
                    f"模板匹配失败: {template_path}, "
                    f"置信度: {match_val:.3f} < 阈值: {threshold}"
                )
                return None
                
        except Exception as e:
            logger.error(f"模板匹配出错: {e}")
            return None
    
    def match_all(
        self,
        screenshot: Image.Image,
        template_path: str,
        threshold: Optional[float] = None,
        method: Optional[int] = None,
        try_all_methods: bool = False
    ) -> List[Tuple[int, int, float]]:
        """
        在截图中匹配所有出现的模板（可能有多个匹配）
        
        Args:
            screenshot: 屏幕截图
            template_path: 模板图像路径
            threshold: 匹配阈值，如果为None则使用配置中的值
            method: OpenCV匹配方法，如果为None则使用配置的方法
            try_all_methods: 是否尝试所有方法并选择最佳结果
        
        Returns:
            匹配结果列表，每个元素是 (x, y, confidence) 元组
        """
        if threshold is None:
            threshold = self._threshold
        
        try:
            # 检查是否需要预处理
            preprocess = self.config.get('recognition.preprocess.enabled', False)
            template = self._load_template(template_path, preprocess=preprocess)
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # 预处理截图
            if preprocess:
                screenshot_cv = self._preprocess_image(screenshot_cv)
                if len(screenshot_cv.shape) == 2:
                    screenshot_cv = cv2.cvtColor(screenshot_cv, cv2.COLOR_GRAY2BGR)
            
            all_matches = []
            
            # 确定要使用的方法
            if try_all_methods:
                methods_to_try = list(self.match_methods.values())
            elif method is not None:
                methods_to_try = [method]
            else:
                # 使用配置的方法
                methods_to_try = [self.match_methods.get(m, cv2.TM_CCOEFF_NORMED) 
                                 for m in self.enabled_methods 
                                 if m in self.match_methods]
                if not methods_to_try:
                    methods_to_try = [cv2.TM_CCOEFF_NORMED]
            
            # 尝试每种方法
            for method_code in methods_to_try:
                result = cv2.matchTemplate(screenshot_cv, template, method_code)
                
                # 找到所有超过阈值的匹配
                if method_code in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    locations = np.where(result <= (1 - threshold))
                else:
                    locations = np.where(result >= threshold)
                
                h, w = template.shape[:2]
                
                for pt in zip(*locations[::-1]):  # 交换x和y
                    center_x = pt[0] + w // 2
                    center_y = pt[1] + h // 2
                    if method_code in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                        confidence = 1 - result[pt[1], pt[0]]  # SQDIFF越小越好，转换为越大越好
                    else:
                        confidence = result[pt[1], pt[0]]
                    all_matches.append((center_x, center_y, float(confidence)))
            
            # 去除重叠的匹配（非极大值抑制）
            if all_matches:
                h, w = template.shape[:2]
                # 先按置信度排序
                all_matches.sort(key=lambda x: x[2], reverse=True)
                
                # 如果匹配数量过多，可能是误报，先进行初步过滤
                max_matches = self.config.get('recognition.max_matches', 10)
                if len(all_matches) > max_matches * 20:  # 如果超过预期20倍，说明阈值太低
                    logger.warning(f"匹配数量过多 ({len(all_matches)})，可能存在大量误报")
                    # 只保留置信度最高的前N个（NMS前先过滤）
                    all_matches = all_matches[:max_matches * 10]
                
                # 使用更严格的NMS（重叠阈值更小）
                overlap_threshold = self.config.get('recognition.nms_overlap_threshold', 0.3)
                all_matches = self._non_max_suppression(all_matches, w, h, overlap_threshold)
                
                # 限制返回的匹配数量（只保留置信度最高的N个）
                if len(all_matches) > max_matches:
                    logger.debug(f"经过NMS后仍有 {len(all_matches)} 个匹配，只保留置信度最高的 {max_matches} 个")
                    all_matches = all_matches[:max_matches]
                
                # 如果匹配数量仍然很多，使用置信度中位数过滤
                if len(all_matches) > max_matches * 2:
                    confidences = [m[2] for m in all_matches]
                    median_conf = sorted(confidences)[len(confidences) // 2]
                    # 只保留置信度高于中位数的匹配
                    if median_conf > threshold:
                        filtered = [m for m in all_matches if m[2] >= median_conf]
                        if len(filtered) < len(all_matches):
                            logger.debug(f"使用置信度中位数 ({median_conf:.3f}) 过滤，从 {len(all_matches)} 减少到 {len(filtered)}")
                            all_matches = filtered[:max_matches]
                
                # 如果匹配数量仍然很多，提高置信度阈值
                if len(all_matches) > max_matches:
                    # 使用更严格的阈值：只保留置信度非常高的匹配
                    strict_threshold = max(threshold, 0.85)  # 至少0.85
                    filtered_matches = [m for m in all_matches if m[2] >= strict_threshold]
                    if filtered_matches:
                        logger.debug(f"使用严格阈值 {strict_threshold:.2f}，从 {len(all_matches)} 个匹配中筛选出 {len(filtered_matches)} 个")
                        all_matches = filtered_matches[:max_matches]
            
            if all_matches:
                logger.debug(f"找到 {len(all_matches)} 个匹配: {template_path}")
                # 显示前3个匹配的置信度
                for i, match in enumerate(all_matches[:3]):
                    logger.debug(f"  匹配{i+1}: 位置({match[0]}, {match[1]}), 置信度: {match[2]:.3f}")
            else:
                # 如果没有匹配，尝试自适应阈值
                if threshold > 0.3:  # 只在阈值较高时尝试
                    logger.debug(f"未找到匹配，尝试自适应阈值...")
                    # 使用最佳方法计算最高置信度
                    best_result = None
                    best_method = methods_to_try[0]
                    for method_code in methods_to_try:
                        result = cv2.matchTemplate(screenshot_cv, template, method_code)
                        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                        if method_code in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                            best_val = 1 - min_val
                        else:
                            best_val = max_val
                        if best_result is None or best_val > best_result:
                            best_result = best_val
                            best_method = method_code
                    
                    # 如果最高置信度接近阈值，降低阈值重试
                    if best_result >= threshold * 0.8:  # 在阈值的80%以上
                        adaptive_threshold = max(0.3, best_result * 0.9)  # 使用最高置信度的90%
                        logger.debug(f"自适应阈值: {adaptive_threshold:.3f} (原阈值: {threshold:.3f})")
                        return self.match_all(screenshot, template_path, adaptive_threshold, best_method, False)
                    else:
                        logger.debug(f"未找到匹配，最高置信度: {best_result:.3f} (阈值: {threshold})")
            
            return all_matches
            
        except Exception as e:
            logger.error(f"多模板匹配出错: {e}")
            return []
    
    def _non_max_suppression(
        self,
        matches: List[Tuple[int, int, float]],
        template_w: int,
        template_h: int,
        overlap_threshold: float = 0.3
    ) -> List[Tuple[int, int, float]]:
        """
        非极大值抑制，去除重叠的匹配
        
        Args:
            matches: 匹配结果列表
            template_w: 模板宽度
            template_h: 模板高度
            overlap_threshold: 重叠阈值（默认0.3，更严格）
        
        Returns:
            去重后的匹配列表
        """
        if not matches:
            return []
        
        # 按置信度排序（应该已经排序了，但确保一下）
        matches = sorted(matches, key=lambda x: x[2], reverse=True)
        
        filtered = []
        for match in matches:
            x, y, conf = match
            
            # 检查是否与已有匹配重叠
            overlap = False
            for existing in filtered:
                ex, ey, _ = existing
                
                # 计算两个匹配框的距离
                # 匹配框的中心是(x, y)，大小是template_w x template_h
                # 计算两个框的最小距离
                dx = abs(x - ex)
                dy = abs(y - ey)
                
                # 如果两个框的中心距离小于模板尺寸的一半，认为是重叠
                # 使用更严格的距离判断
                min_distance = min(template_w, template_h) * 0.6  # 更严格：60%的模板尺寸
                if dx < min_distance and dy < min_distance:
                    # 进一步计算重叠区域
                    # 匹配框的边界
                    x1_min, x1_max = x - template_w // 2, x + template_w // 2
                    y1_min, y1_max = y - template_h // 2, y + template_h // 2
                    x2_min, x2_max = ex - template_w // 2, ex + template_w // 2
                    y2_min, y2_max = ey - template_h // 2, ey + template_h // 2
                    
                    # 计算重叠区域
                    overlap_x = max(0, min(x1_max, x2_max) - max(x1_min, x2_min))
                    overlap_y = max(0, min(y1_max, y2_max) - max(y1_min, y2_min))
                    overlap_area = overlap_x * overlap_y
                    template_area = template_w * template_h
                    
                    if overlap_area / template_area > overlap_threshold:
                        overlap = True
                        break
            
            if not overlap:
                filtered.append(match)
        
        return filtered
