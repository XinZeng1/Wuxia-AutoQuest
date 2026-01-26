"""
怪物检测诊断工具
用于分析怪物检测失败的原因，测试不同方法和参数
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from src.ui_interaction.screenshot import Screenshot
from src.monster_detection.monster_detector import MonsterDetector
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


class MonsterDetectionDiagnostic:
    """怪物检测诊断类"""
    
    def __init__(self):
        """初始化诊断工具"""
        self.config = get_config()
        self.screenshot = Screenshot()
        self.detector = MonsterDetector()
        
        # OpenCV匹配方法列表（归一化方法，可以直接与阈值比较）
        self.normalized_methods = {
            'TM_CCOEFF_NORMED': cv2.TM_CCOEFF_NORMED,
            'TM_CCORR_NORMED': cv2.TM_CCORR_NORMED,
            'TM_SQDIFF_NORMED': cv2.TM_SQDIFF_NORMED,
        }
        # 非归一化方法（仅用于参考，不能直接与阈值比较）
        self.unnormalized_methods = {
            'TM_CCOEFF': cv2.TM_CCOEFF,
            'TM_CCORR': cv2.TM_CCORR,
            'TM_SQDIFF': cv2.TM_SQDIFF,
        }
        # 所有方法（用于完整测试）
        self.match_methods = {**self.normalized_methods, **self.unnormalized_methods}
    
    def test_all_methods(self, screenshot: Image.Image, template_path: str, threshold: float = 0.6):
        """测试所有匹配方法"""
        print("\n" + "=" * 60)
        print("测试所有OpenCV匹配方法")
        print("=" * 60)
        
        template = cv2.imread(str(template_path))
        if template is None:
            print(f"❌ 无法加载模板: {template_path}")
            return {}
        
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        results = {}
        
        for method_name, method_code in self.match_methods.items():
            try:
                result = cv2.matchTemplate(screenshot_cv, template, method_code)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # 根据方法类型选择最佳值
                if method_code in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    best_val = 1 - min_val  # SQDIFF越小越好，转换为越大越好
                    best_loc = min_loc
                else:
                    best_val = max_val
                    best_loc = max_loc
                
                # 检查是否超过阈值
                matches = []
                if method_code in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                    locations = np.where(result <= (1 - threshold))
                else:
                    locations = np.where(result >= threshold)
                
                for pt in zip(*locations[::-1]):
                    h, w = template.shape[:2]
                    center_x = pt[0] + w // 2
                    center_y = pt[1] + h // 2
                    if method_code in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]:
                        conf = 1 - result[pt[1], pt[0]]
                    else:
                        conf = result[pt[1], pt[0]]
                    matches.append((center_x, center_y, float(conf)))
                
                results[method_name] = {
                    'best_confidence': float(best_val),
                    'best_location': best_loc,
                    'matches_count': len(matches),
                    'matches': matches[:10]  # 只保存前10个
                }
                
                # 只有归一化方法才能与阈值比较
                is_normalized = method_code in self.normalized_methods.values()
                if is_normalized:
                    status = "✅" if best_val >= threshold else "❌"
                    print(f"{status} {method_name:20s} | 最佳置信度: {best_val:.4f} | 匹配数: {len(matches)}")
                else:
                    # 非归一化方法显示信息但不与阈值比较
                    print(f"ℹ️  {method_name:20s} | 最佳值: {best_val:.2f} | 匹配数: {len(matches)} (非归一化)")
                
            except Exception as e:
                print(f"❌ {method_name:20s} | 错误: {e}")
                results[method_name] = {'error': str(e)}
        
        return results
    
    def test_threshold_range(self, screenshot: Image.Image, template_path: str, method: int = cv2.TM_CCOEFF_NORMED):
        """测试不同阈值下的匹配结果"""
        print("\n" + "=" * 60)
        print("测试不同阈值下的匹配结果")
        print("=" * 60)
        
        template = cv2.imread(str(template_path))
        if template is None:
            print(f"❌ 无法加载模板: {template_path}")
            return
        
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        result = cv2.matchTemplate(screenshot_cv, template, method)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        # 判断是否为SQDIFF方法（越小越好）
        is_sqdiff = method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]
        
        if is_sqdiff:
            # SQDIFF方法：值越小越好，转换为越大越好
            best_val = 1 - min_val
            best_loc = min_loc
            print(f"匹配结果范围: 最小值={min_val:.4f}, 最大值={max_val:.4f}")
            print(f"转换后最佳值: {best_val:.4f} (越小越好，已转换)")
            print(f"最佳位置: {min_loc}")
        else:
            best_val = max_val
            best_loc = max_loc
            print(f"匹配结果范围: 最小值={min_val:.4f}, 最大值={max_val:.4f}")
            print(f"最佳位置: {max_loc}")
        print()
        
        # 测试不同阈值
        thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        for threshold in thresholds:
            if is_sqdiff:
                # SQDIFF: 值越小越好，所以阈值转换为 (1 - threshold)
                locations = np.where(result <= (1 - threshold))
            else:
                locations = np.where(result >= threshold)
            match_count = len(list(zip(*locations[::-1])))
            print(f"阈值 {threshold:.1f}: {match_count:4d} 个匹配")
    
    def visualize_matches(self, screenshot: Image.Image, template_path: str, 
                         method: int = cv2.TM_CCOEFF_NORMED, threshold: float = 0.6,
                         save_path: str = None):
        """可视化所有可能的匹配位置"""
        template = cv2.imread(str(template_path))
        if template is None:
            print(f"❌ 无法加载模板: {template_path}")
            return None
        
        screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        result = cv2.matchTemplate(screenshot_cv, template, method)
        
        # 判断是否为SQDIFF方法（越小越好）
        is_sqdiff = method in [cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED]
        
        # 创建可视化图像
        vis_image = screenshot.copy()
        draw = ImageDraw.Draw(vis_image)
        
        h, w = template.shape[:2]
        if is_sqdiff:
            locations = np.where(result <= (1 - threshold))
        else:
            locations = np.where(result >= threshold)
        matches = []
        
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            if is_sqdiff:
                confidence = 1 - result[pt[1], pt[0]]  # SQDIFF越小越好，转换为越大越好
            else:
                confidence = result[pt[1], pt[0]]
            matches.append((center_x, center_y, float(confidence)))
        
        # 按置信度排序
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # 绘制匹配位置
        colors = ['red', 'orange', 'yellow', 'green', 'blue']
        for i, (x, y, conf) in enumerate(matches[:20]):  # 只标记前20个
            color = colors[i % len(colors)]
            # 绘制矩形框
            draw.rectangle(
                [x - w//2, y - h//2, x + w//2, y + h//2],
                outline=color,
                width=2
            )
            # 绘制置信度文本
            try:
                draw.text((x - w//2, y - h//2 - 15), f"{conf:.2f}", fill=color)
            except:
                pass
        
        if save_path:
            vis_image.save(save_path)
            print(f"\n可视化图像已保存到: {save_path}")
        
        return vis_image, matches
    
    def analyze_image_quality(self, image: Image.Image):
        """分析图像质量"""
        print("\n" + "=" * 60)
        print("图像质量分析")
        print("=" * 60)
        
        img_array = np.array(image)
        
        # 转换为灰度
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # 计算统计信息
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)
        min_brightness = np.min(gray)
        max_brightness = np.max(gray)
        
        print(f"亮度统计:")
        print(f"  平均值: {mean_brightness:.2f}")
        print(f"  标准差: {std_brightness:.2f}")
        print(f"  范围: {min_brightness} - {max_brightness}")
        
        # 对比度评估
        contrast = std_brightness / (mean_brightness + 1e-5)
        print(f"  对比度: {contrast:.4f}")
        
        # 图像尺寸
        print(f"\n图像尺寸: {image.size[0]}x{image.size[1]}")
        
        return {
            'mean_brightness': mean_brightness,
            'std_brightness': std_brightness,
            'contrast': contrast,
            'size': image.size
        }


def main():
    """主函数"""
    try:
        print("=" * 60)
        print("怪物检测诊断工具")
        print("=" * 60)
        
        # 初始化
        diagnostic = MonsterDetectionDiagnostic()
        config = get_config()
        threshold = config.get('recognition.template_match_threshold', 0.6)
        
        # 检查模板文件
        template_path = project_root / "templates" / "monster.png"
        if not template_path.exists():
            print(f"❌ 模板文件不存在: {template_path}")
            return
        
        print(f"\n模板文件: {template_path}")
        template_img = Image.open(template_path)
        print(f"模板尺寸: {template_img.size}")
        
        # 截图
        print("\n正在截图...")
        screenshot = Screenshot().capture_full_window()
        print(f"截图尺寸: {screenshot.size}")
        
        # 保存截图
        screenshot_path = project_root / "diagnostic_screenshot.png"
        screenshot.save(screenshot_path)
        print(f"截图已保存到: {screenshot_path}")
        
        # 分析图像质量
        print("\n分析模板图像质量...")
        template_quality = diagnostic.analyze_image_quality(template_img)
        
        print("\n分析截图图像质量...")
        screenshot_quality = diagnostic.analyze_image_quality(screenshot)
        
        # 测试所有匹配方法
        methods_results = diagnostic.test_all_methods(screenshot, template_path, threshold)
        
        # 找出最佳归一化方法（只考虑归一化方法）
        best_method = None
        best_confidence = 0
        for method_name, result in methods_results.items():
            if 'best_confidence' in result and method_name in diagnostic.normalized_methods:
                if result['best_confidence'] > best_confidence:
                    best_confidence = result['best_confidence']
                    best_method = method_name
        
        if best_method:
            print(f"\n✅ 最佳归一化匹配方法: {best_method} (置信度: {best_confidence:.4f})")
        else:
            print("\n❌ 所有归一化方法都无法匹配")
            # 如果没有归一化方法匹配，使用默认方法
            best_method = 'TM_CCOEFF_NORMED'
            best_confidence = 0
        
        # 测试阈值范围（只使用归一化方法）
        best_method_code = diagnostic.normalized_methods.get(best_method, cv2.TM_CCOEFF_NORMED)
        diagnostic.test_threshold_range(screenshot, template_path, best_method_code)
        
        # 可视化匹配结果（使用归一化方法）
        print("\n生成可视化图像...")
        vis_path = project_root / "diagnostic_matches_visualization.png"
        # 使用归一化方法进行可视化
        vis_method = diagnostic.normalized_methods.get(best_method, cv2.TM_CCORR_NORMED)
        vis_image, matches = diagnostic.visualize_matches(
            screenshot, template_path, 
            vis_method, threshold=0.3,  # 使用较低阈值以显示更多匹配
            save_path=str(vis_path)
        )
        
        if matches:
            print(f"\n找到 {len(matches)} 个可能的匹配位置（阈值0.3）")
            print("前5个最佳匹配:")
            for i, (x, y, conf) in enumerate(matches[:5]):
                print(f"  {i+1}. 位置({x}, {y}), 置信度: {conf:.4f}")
        
        # 生成诊断报告
        print("\n" + "=" * 60)
        print("诊断报告")
        print("=" * 60)
        print(f"\n当前配置阈值: {threshold}")
        print(f"最佳匹配方法: {best_method}")
        print(f"最佳置信度: {best_confidence:.4f}")
        
        if best_method and best_confidence > 0:
            if best_confidence < threshold:
                print(f"\n⚠️  问题诊断:")
                print(f"   最佳归一化方法 ({best_method}) 的置信度 ({best_confidence:.4f}) 低于配置阈值 ({threshold})")
                print(f"   建议:")
                print(f"   1. 降低阈值到 {max(0.3, best_confidence * 0.9):.2f} 或更低")
                print(f"   2. 检查模板图像是否与实际怪物图标匹配")
                print(f"   3. 在配置中使用 {best_method} 方法:")
                print(f"      recognition:")
                print(f"        match_methods:")
                print(f"          - \"{best_method}\"")
            else:
                print(f"\n✅ 检测应该可以工作")
                print(f"   最佳归一化方法 ({best_method}) 的置信度 ({best_confidence:.4f}) 高于配置阈值 ({threshold})")
                print(f"   建议在配置中使用此方法:")
                print(f"      recognition:")
                print(f"        match_methods:")
                print(f"          - \"{best_method}\"")
        else:
            print(f"\n❌ 所有归一化方法都无法匹配")
            print(f"   建议:")
            print(f"   1. 检查模板图像是否与实际怪物图标匹配")
            print(f"   2. 重新截图一个更清晰的怪物模板")
            print(f"   3. 尝试启用图像预处理（在配置中设置 recognition.preprocess.enabled: true）")
        
        print(f"\n生成的文件:")
        print(f"  - {screenshot_path}")
        print(f"  - {vis_path}")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 诊断失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
