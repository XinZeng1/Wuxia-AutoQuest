"""
测试探索度配置是否正确
用于验证探索度文本区域配置和OCR识别
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.exploration_tracking.exploration_tracker import ExplorationTracker
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


def main():
    """测试探索度配置"""
    try:
        print("=" * 50)
        print("测试探索度配置")
        print("=" * 50)
        
        # 加载配置
        print("\n1. 加载配置...")
        config = get_config()
        exploration_config = config.exploration
        text_region = exploration_config.get('text_region', {})
        
        if not text_region:
            print("❌ 配置错误：未找到 text_region 配置")
            print("   请在 config/config.yaml 中添加 exploration.text_region 配置")
            return
        
        print(f"✅ 配置加载成功")
        print(f"   文本区域: left={text_region.get('left')}, top={text_region.get('top')}")
        print(f"   区域大小: width={text_region.get('width')}, height={text_region.get('height')}")
        
        # 初始化工具
        print("\n2. 初始化工具...")
        screenshot = Screenshot()
        tracker = ExplorationTracker()
        print("✅ 工具初始化成功")
        
        # 检查窗口配置
        print("\n3. 检查窗口配置...")
        window = config.window
        window_width = window.get('width', 0)
        window_height = window.get('height', 0)
        print(f"   窗口大小: {window_width}x{window_height}")
        
        # 检查文本区域是否在窗口范围内
        left = text_region.get('left', 0)
        top = text_region.get('top', 0)
        width = text_region.get('width', 0)
        height = text_region.get('height', 0)
        right = left + width
        bottom = top + height
        
        if left < 0 or top < 0:
            print("❌ 配置错误：文本区域坐标不能为负数")
            return
        
        if right > window_width or bottom > window_height:
            print("❌ 配置错误：文本区域超出窗口范围")
            print(f"   窗口范围: 0-{window_width} x 0-{window_height}")
            print(f"   文本区域: {left}-{right} x {top}-{bottom}")
            return
        
        print("✅ 文本区域在窗口范围内")
        
        # 截图测试
        print("\n4. 测试截图...")
        try:
            full_screenshot = screenshot.capture_full_window()
            print(f"✅ 截图成功，尺寸: {full_screenshot.size}")
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return
        
        # 检查截图尺寸和配置窗口尺寸是否匹配
        print("\n5. 检查截图尺寸...")
        screenshot_width, screenshot_height = full_screenshot.size
        print(f"   实际截图尺寸: {screenshot_width}x{screenshot_height}")
        print(f"   配置窗口尺寸: {window_width}x{window_height}")
        
        # 计算缩放比例（Retina截图可能是2x分辨率）
        scale_x = screenshot_width / window_width if window_width > 0 else 1.0
        scale_y = screenshot_height / window_height if window_height > 0 else 1.0
        
        if abs(scale_x - 1.0) > 0.1 or abs(scale_y - 1.0) > 0.1:
            print(f"   ⚠️  注意：截图尺寸与配置窗口尺寸不匹配（缩放: {scale_x:.2f}x{scale_y:.2f}）")
            print(f"   这可能是 Retina 显示器的原因（2x分辨率）")
            print(f"   检测区域坐标会自动按比例缩放")
        
        # 计算实际裁剪坐标（考虑缩放）
        actual_left = int(left * scale_x)
        actual_top = int(top * scale_y)
        actual_right = int(right * scale_x)
        actual_bottom = int(bottom * scale_y)
        
        print(f"   配置区域: ({left}, {top}) - ({right}, {bottom})")
        print(f"   实际裁剪: ({actual_left}, {actual_top}) - ({actual_right}, {actual_bottom})")
        
        # 边界检查
        if actual_left < 0:
            print(f"   ⚠️  警告：左边界 {actual_left} < 0，已调整为 0")
            actual_left = 0
        if actual_top < 0:
            print(f"   ⚠️  警告：上边界 {actual_top} < 0，已调整为 0")
            actual_top = 0
        if actual_right > screenshot_width:
            print(f"   ⚠️  警告：右边界 {actual_right} > {screenshot_width}，已调整为 {screenshot_width}")
            actual_right = screenshot_width
        if actual_bottom > screenshot_height:
            print(f"   ⚠️  警告：下边界 {actual_bottom} > {screenshot_height}，已调整为 {screenshot_height}")
            actual_bottom = screenshot_height
        
        # 检查区域是否有效
        if actual_right <= actual_left or actual_bottom <= actual_top:
            print("❌ 配置错误：检测区域无效")
            print(f"   截图范围: 0-{screenshot_width} x 0-{screenshot_height}")
            print(f"   实际裁剪区域: {actual_left}-{actual_right} x {actual_top}-{actual_bottom}")
            return
        
        # 截取文本区域
        print("\n6. 截取文本区域...")
        try:
            cropped = full_screenshot.crop((actual_left, actual_top, actual_right, actual_bottom))
            print(f"✅ 文本区域截图成功，尺寸: {cropped.size}")
            
            # 保存测试图像
            test_image_path = project_root / "test_exploration_text.png"
            cropped.save(test_image_path)
            print(f"   测试图像已保存到: {test_image_path}")
        except Exception as e:
            print(f"❌ 截取文本区域失败: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # OCR识别测试
        print("\n7. 测试OCR识别...")
        try:
            # 显示图像信息
            print(f"   图像尺寸: {cropped.size[0]}x{cropped.size[1]} 像素")
            if cropped.size[0] < 50 or cropped.size[1] < 15:
                print("   ⚠️  警告：图像可能太小，可能影响识别效果")
            
            # 识别文本（保存调试图像）
            text = tracker.ocr.recognize(cropped, save_debug=True)
            print(f"   原始识别文本: '{text}'")
            
            # 检查是否保存了调试图像
            debug_path = project_root / "ocr_debug.png"
            if debug_path.exists():
                print(f"   预处理图像已保存到: {debug_path}")
                print("   可以查看预处理后的图像来诊断问题")
            
            if not text:
                print("❌ OCR识别失败：未识别到任何文本")
                print("\n   可能的原因：")
                print("   1. 文本区域配置不正确（未包含完整文本）")
                print("   2. 文本区域太小（建议宽度>50像素，高度>20像素）")
                print("   3. OCR引擎配置问题（检查Tesseract是否安装）")
                print("   4. 图像质量不佳（模糊、对比度低等）")
                print("\n   建议：")
                print("   1. 检查 test_exploration_text.png 是否包含完整文本")
                print("   2. 检查 ocr_debug.png 查看预处理效果")
                print("   3. 尝试增大文本区域（width和height）")
                print("   4. 确保文本区域包含完整的'探索度 XX%'文字")
                return
            
            # 解析数值
            value = tracker.parse_exploration_value(text)
            
            if value is not None:
                print(f"✅ OCR识别成功！")
                print(f"   解析的探索度: {value}%")
                
                # 检查是否达到目标
                target = tracker.target
                if value >= target:
                    print(f"   探索度已达到目标: {value}% >= {target}%")
                else:
                    print(f"   探索度未达到目标: {value}% < {target}%")
            else:
                print("❌ OCR识别失败：无法解析探索度数值")
                print(f"   识别到的文本: '{text}'")
                print("   可能的原因：")
                print("   1. 文本格式不符合预期（应为'探索度 XX%'）")
                print("   2. OCR识别不准确")
                print("   3. 文本区域包含干扰信息")
                return
                
        except Exception as e:
            print(f"❌ OCR识别出错: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 总结
        print("\n" + "=" * 50)
        print("✅ 配置测试通过！")
        print("=" * 50)
        print("\n配置摘要：")
        print(f"  文本区域: ({left}, {top}) - ({right}, {bottom})")
        print(f"  区域大小: {width}x{height}")
        print(f"  当前探索度: {value}%")
        print(f"  目标探索度: {tracker.target}%")
        print(f"\n测试图像: {test_image_path}")
        print("   请检查图像是否包含完整的'探索度 XX%'文本")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
