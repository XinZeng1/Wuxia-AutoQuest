"""
调试工具：显示OCR识别到的所有文本，帮助调整关键词配置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image, ImageDraw, ImageFont
import pytesseract
from src.monster_detection.monster_detector import MonsterDetector
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


def main():
    """主函数"""
    try:
        print("=" * 60)
        print("OCR文本识别调试工具")
        print("=" * 60)
        
        # 初始化
        detector = MonsterDetector()
        config = get_config()
        
        # 截图
        print("\n正在截图...")
        screenshot = detector.screenshot.capture_full_window()
        print(f"截图尺寸: {screenshot.size}")
        
        # 保存原始截图
        screenshot_path = project_root / "debug_ocr_screenshot.png"
        screenshot.save(screenshot_path)
        print(f"原始截图已保存到: {screenshot_path}")
        
        # 预处理图像
        preprocess_mode = config.get('monster.ocr_preprocess_mode', 'light')
        print(f"\n预处理图像 (模式: {preprocess_mode})...")
        preprocessed = detector._preprocess_for_ocr(screenshot)
        
        # 保存预处理后的图像
        preprocessed_path = project_root / "debug_ocr_preprocessed.png"
        preprocessed.save(preprocessed_path)
        print(f"预处理图像已保存到: {preprocessed_path}")
        
        # 使用多种OCR配置识别
        print("\n使用多种OCR配置识别文本...")
        ocr_configs = [
            ('PSM 6 (单一文本块)', '--psm 6'),
            ('PSM 11 (稀疏文本)', '--psm 11'),
            ('PSM 12 (带OSD的稀疏文本)', '--psm 12'),
            ('PSM 3 (完全自动)', '--psm 3'),
        ]
        
        all_texts = []
        lang = config.get('recognition.ocr.lang', 'chi_sim')
        
        for config_name, config_str in ocr_configs:
            try:
                ocr_data = pytesseract.image_to_data(
                    preprocessed,
                    lang=lang,
                    config=config_str,
                    output_type=pytesseract.Output.DICT
                )
                
                texts_found = []
                n_boxes = len(ocr_data['text'])
                
                for i in range(n_boxes):
                    text = ocr_data['text'][i].strip()
                    conf = float(ocr_data['conf'][i])
                    
                    if text and conf >= 20:  # 只显示置信度>=20的文本
                        x = ocr_data['left'][i]
                        y = ocr_data['top'][i]
                        w = ocr_data['width'][i]
                        h = ocr_data['height'][i]
                        texts_found.append((text, x, y, w, h, conf))
                        all_texts.append((text, x, y, w, h, conf, config_name))
                
                print(f"\n{config_name}:")
                if texts_found:
                    for text, x, y, w, h, conf in texts_found[:20]:  # 只显示前20个
                        print(f"  '{text}' 位置({x}, {y}) 置信度: {conf:.1f}")
                else:
                    print("  未识别到文本")
            except Exception as e:
                print(f"\n{config_name} 失败: {e}")
        
        # 显示所有识别到的文本（去重）
        print("\n" + "=" * 60)
        print("所有识别到的文本（去重后，按置信度排序）:")
        print("=" * 60)
        
        unique_texts = {}
        for text, x, y, w, h, conf, config_name in all_texts:
            # 使用文本内容和位置作为key，避免完全相同的文本被去重
            text_key = f"{text}_{x}_{y}"
            if text_key not in unique_texts or conf > unique_texts[text_key][5]:
                unique_texts[text_key] = (text, x, y, w, h, conf, config_name)
        
        # 按置信度排序
        sorted_texts = sorted(unique_texts.values(), key=lambda x: x[5], reverse=True)
        
        print(f"\n共识别到 {len(sorted_texts)} 个文本块\n")
        for i, (text, x, y, w, h, conf, config_name) in enumerate(sorted_texts[:100], 1):  # 显示前100个
            # 检查是否包含数字和中文（可能是怪物名称）
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
            has_number = any(char.isdigit() for char in text)
            has_level = '级' in text or 'Lv' in text
            
            marker = ""
            if has_chinese and (has_number or has_level):
                marker = " ⭐ (可能是怪物名称)"
            
            print(f"  {i:3d}. '{text}' 置信度: {conf:5.1f} {marker}")
        
        # 检查哪些文本匹配关键词
        print("\n" + "=" * 60)
        print("匹配关键词的文本:")
        print("=" * 60)
        
        keywords = config.get('monster.name_keywords', [])
        matched_texts = []
        
        for text, x, y, w, h, conf, config_name in sorted_texts:
            matched_keywords = []
            for keyword in keywords:
                if keyword in text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                matched_texts.append((text, matched_keywords, conf))
                print(f"  '{text}' 匹配关键词: {matched_keywords} 置信度: {conf:.1f}")
        
        if not matched_texts:
            print("  没有文本匹配任何关键词")
            print(f"\n当前关键词: {keywords}")
            
            # 找出可能是怪物名称的文本（包含中文和数字/等级）
            print("\n" + "=" * 60)
            print("可能是怪物名称的文本（包含中文和数字/等级）:")
            print("=" * 60)
            
            candidate_texts = []
            for text, x, y, w, h, conf, config_name in sorted_texts:
                has_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
                has_number = any(char.isdigit() for char in text)
                has_level = '级' in text or 'Lv' in text
                
                if has_chinese and (has_number or has_level) and len(text) >= 2:
                    candidate_texts.append((text, conf))
            
            if candidate_texts:
                print("\n建议添加到关键词的文本:")
                for text, conf in candidate_texts[:20]:  # 显示前20个
                    # 提取可能的关键词（去除数字和等级）
                    import re
                    cleaned = re.sub(r'\d+级?|Lv\d+', '', text).strip()
                    if cleaned and len(cleaned) >= 2:
                        print(f"  '{text}' -> 建议关键词: '{cleaned}' (置信度: {conf:.1f})")
            else:
                print("  未找到明显的怪物名称文本")
            
            print("\n建议:")
            print("1. 查看上述'可能是怪物名称的文本'")
            print("2. 从这些文本中提取关键词（去除数字和等级部分）")
            print("3. 将关键词添加到 config/config.yaml 的 monster.name_keywords 中")
            print("4. 例如：如果看到'白虎堂堂主47级'，可以添加'白虎堂'或'堂主'作为关键词")
        
        # 在截图上标记所有识别到的文本
        print("\n生成标记图像...")
        marked_image = screenshot.copy()
        draw = ImageDraw.Draw(marked_image)
        
        # 标记匹配关键词的文本（红色）
        for text, x, y, w, h, conf, config_name in all_texts:
            # 调整坐标（因为预处理时可能放大了）
            preprocess_mode = config.get('monster.ocr_preprocess_mode', 'light')
            if preprocess_mode == 'none' or preprocess_mode == 'light':
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
            
            orig_x = int(x / scale_factor)
            orig_y = int(y / scale_factor)
            orig_w = int(w / scale_factor)
            orig_h = int(h / scale_factor)
            
            # 检查是否匹配关键词
            is_matched = False
            for keyword in keywords:
                if keyword in text:
                    is_matched = True
                    break
            
            # 绘制矩形框
            color = 'red' if is_matched else 'yellow'
            draw.rectangle(
                [orig_x, orig_y, orig_x + orig_w, orig_y + orig_h],
                outline=color,
                width=2
            )
            
            # 绘制文本（如果空间足够）
            if orig_h > 15:
                try:
                    draw.text((orig_x, orig_y - 15), text[:20], fill=color)
                except:
                    pass
        
        # 保存标记后的图像
        marked_path = project_root / "debug_ocr_marked.png"
        marked_image.save(marked_path)
        print(f"标记图像已保存到: {marked_path}")
        print("  (红色框: 匹配关键词的文本, 黄色框: 其他文本)")
        
        print("\n" + "=" * 60)
        print("调试完成")
        print("=" * 60)
        print(f"\n生成的文件:")
        print(f"  - {screenshot_path} (原始截图)")
        print(f"  - {preprocessed_path} (预处理后的图像)")
        print(f"  - {marked_path} (标记了所有识别文本的图像)")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 调试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
