"""
对比不同OCR引擎的识别效果
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image, ImageDraw
import numpy as np
from src.monster_detection.monster_detector import MonsterDetector
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


def test_pytesseract(screenshot, keywords):
    """测试pytesseract"""
    print("\n" + "=" * 60)
    print("测试 pytesseract")
    print("=" * 60)
    
    try:
        import pytesseract
        
        # 尝试多种配置
        configs = [
            ('PSM 6', '--psm 6'),
            ('PSM 11', '--psm 11'),
            ('PSM 12', '--psm 12'),
            ('PSM 3', '--psm 3'),
        ]
        
        all_results = []
        all_texts = []  # 所有识别到的文本
        
        for config_name, config_str in configs:
            try:
                ocr_data = pytesseract.image_to_data(
                    screenshot,
                    lang='chi_sim',
                    config=config_str,
                    output_type=pytesseract.Output.DICT
                )
                
                n_boxes = len(ocr_data['text'])
                matched = []
                texts_in_config = []
                
                for i in range(n_boxes):
                    text = ocr_data['text'][i].strip()
                    conf = float(ocr_data['conf'][i])
                    
                    if text and conf >= 20:
                        texts_in_config.append((text, conf, ocr_data['left'][i], ocr_data['top'][i]))
                        for keyword in keywords:
                            if keyword in text:
                                matched.append((text, conf, ocr_data['left'][i], ocr_data['top'][i]))
                                break
                
                if texts_in_config:
                    print(f"\n{config_name}: 识别到 {len(texts_in_config)} 个文本块")
                    # 显示前10个文本
                    for text, conf, x, y in texts_in_config[:10]:
                        is_matched = any(keyword in text for keyword in keywords)
                        marker = " ✅" if is_matched else ""
                        print(f"  '{text}' 置信度: {conf:.1f} 位置({x}, {y}){marker}")
                    all_texts.extend(texts_in_config)
                
                if matched:
                    print(f"  其中 {len(matched)} 个匹配关键词")
                    all_results.extend(matched)
            except Exception as e:
                print(f"{config_name} 失败: {e}")
        
        if not all_results and all_texts:
            print(f"\n⚠️  识别到 {len(all_texts)} 个文本，但没有匹配关键词")
            print("所有识别到的文本:")
            unique_texts = {}
            for text, conf, x, y in all_texts:
                if text not in unique_texts or conf > unique_texts[text][1]:
                    unique_texts[text] = (text, conf, x, y)
            for text, conf, x, y in sorted(unique_texts.values(), key=lambda x: x[1], reverse=True)[:20]:
                print(f"  '{text}' 置信度: {conf:.1f}")
        
        return all_results
    except ImportError:
        print("pytesseract未安装")
        return []


def test_easyocr(screenshot, keywords):
    """测试easyocr"""
    print("\n" + "=" * 60)
    print("测试 EasyOCR")
    print("=" * 60)
    
    try:
        import easyocr
        
        # 初始化（只初始化一次）
        print("初始化EasyOCR（首次运行需要下载模型，可能需要几分钟）...")
        reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)
        
        # 转换为numpy数组
        img_array = np.array(screenshot)
        
        # 识别
        print("正在识别...")
        results = reader.readtext(img_array)
        
        print(f"\n识别到 {len(results)} 个文本块:")
        
        matched = []
        all_texts = []
        
        for (bbox, text, conf) in results:
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x = int(sum(x_coords) / len(x_coords))
            y = int(sum(y_coords) / len(y_coords))
            
            all_texts.append((text, float(conf), x, y))
            
            # 检查是否匹配关键词
            is_matched = False
            for keyword in keywords:
                if keyword in text:
                    matched.append((text, float(conf), x, y))
                    is_matched = True
                    break
            
            marker = " ✅" if is_matched else ""
            print(f"  '{text}' 置信度: {conf:.3f} 位置({x}, {y}){marker}")
        
        if matched:
            print(f"\n其中 {len(matched)} 个匹配关键词")
        else:
            print(f"\n⚠️  识别到 {len(all_texts)} 个文本，但没有匹配关键词")
            print("\n所有识别到的文本（按置信度排序）:")
            for text, conf, x, y in sorted(all_texts, key=lambda x: x[1], reverse=True)[:20]:
                print(f"  '{text}' 置信度: {conf:.3f}")
        
        return matched
    except ImportError:
        print("EasyOCR未安装，请运行: pip install easyocr")
        return []
    except Exception as e:
        print(f"EasyOCR失败: {e}")
        import traceback
        traceback.print_exc()
        return []


def analyze_image_quality(screenshot):
    """分析图像质量"""
    print("\n" + "=" * 60)
    print("图像质量分析")
    print("=" * 60)
    
    import cv2
    
    img_array = np.array(screenshot)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    
    # 计算清晰度（拉普拉斯方差）
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    # 计算对比度
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)
    contrast = std_brightness / (mean_brightness + 1e-5)
    
    print(f"图像尺寸: {screenshot.size[0]}x{screenshot.size[1]}")
    print(f"清晰度（拉普拉斯方差）: {laplacian_var:.2f}")
    print(f"  说明: >100 清晰, 50-100 一般, <50 模糊")
    print(f"对比度: {contrast:.4f}")
    print(f"  说明: >0.5 良好, 0.2-0.5 一般, <0.2 较差")
    print(f"平均亮度: {mean_brightness:.2f}")
    print(f"亮度标准差: {std_brightness:.2f}")
    
    # 评估
    issues = []
    if laplacian_var < 50:
        issues.append("图像可能模糊（清晰度 < 50）")
    if contrast < 0.2:
        issues.append("对比度较低（< 0.2）")
    if mean_brightness < 50 or mean_brightness > 200:
        issues.append("亮度异常")
    
    if issues:
        print("\n⚠️  发现的问题:")
        for issue in issues:
            print(f"  - {issue}")
        print("\n建议:")
        print("  1. 检查屏幕镜像软件的质量设置")
        print("  2. 尝试提高镜像分辨率")
        print("  3. 检查窗口配置是否正确")
    else:
        print("\n✅ 图像质量良好")


def main():
    """主函数"""
    try:
        print("=" * 60)
        print("OCR引擎对比测试工具")
        print("=" * 60)
        
        # 初始化
        detector = MonsterDetector()
        config = get_config()
        
        # 截图
        print("\n正在截图...")
        screenshot = detector.screenshot.capture_full_window()
        print(f"截图尺寸: {screenshot.size}")
        
        # 保存截图
        screenshot_path = project_root / "compare_ocr_screenshot.png"
        screenshot.save(screenshot_path)
        print(f"截图已保存到: {screenshot_path}")
        
        # 分析图像质量
        analyze_image_quality(screenshot)
        
        # 获取关键词
        keywords = config.get('monster.name_keywords', [])
        print(f"\n使用的关键词: {keywords}")
        
        # 测试pytesseract
        pytesseract_results = test_pytesseract(screenshot, keywords)
        
        # 测试easyocr
        easyocr_results = test_easyocr(screenshot, keywords)
        
        # 对比结果
        print("\n" + "=" * 60)
        print("对比结果")
        print("=" * 60)
        print(f"pytesseract: 找到 {len(pytesseract_results)} 个匹配")
        print(f"EasyOCR: 找到 {len(easyocr_results)} 个匹配")
        
        if len(easyocr_results) > len(pytesseract_results):
            print("\n✅ EasyOCR识别效果更好，建议使用EasyOCR")
            print("在 config/config.yaml 中设置:")
            print("  recognition:")
            print("    ocr:")
            print("      engine: 'easyocr'")
        elif len(pytesseract_results) > len(easyocr_results):
            print("\n✅ pytesseract识别效果更好，建议继续使用pytesseract")
        else:
            print("\n两种引擎识别效果相近")
        
        # 如果都没找到
        if not pytesseract_results and not easyocr_results:
            print("\n⚠️  两种引擎都未找到匹配的文本")
            print("\n可能的原因:")
            print("1. 关键词配置不正确（OCR识别到了文本，但不包含关键词）")
            print("2. 游戏界面上没有显示怪物名称")
            print("3. 怪物名称被识别成了其他字符")
            print("\n建议:")
            print("1. 查看上方'所有识别到的文本'列表")
            print("2. 找出应该是怪物名称的文本")
            print("3. 从这些文本中提取关键词，添加到 config/config.yaml 的 monster.name_keywords 中")
            print("4. 例如：如果看到'豫州劫匪50级'，可以添加'豫州劫匪'或'劫匪'作为关键词")
            print("\n💡 提示：关键词不需要完全匹配，只要文本中包含关键词即可")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
