"""
快速诊断战斗检测区域配置
直接截图并显示裁剪区域，帮助定位问题
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.core.config import get_config
from PIL import Image, ImageDraw, ImageFont

def main():
    """诊断战斗检测区域"""
    try:
        print("=" * 60)
        print("战斗检测区域诊断工具")
        print("=" * 60)
        
        # 加载配置
        config = get_config()
        window = config.window
        window_width = window.get('width', 674)
        window_height = window.get('height', 316)
        
        combat_config = config.get('combat', {})
        detection_region = combat_config.get('detection_region', {})
        left = detection_region.get('left', 600)
        top = detection_region.get('top', 40)
        width = detection_region.get('width', 60)
        height = detection_region.get('height', 20)
        
        print(f"\n配置信息:")
        print(f"  窗口大小: {window_width}x{window_height}")
        print(f"  检测区域: left={left}, top={top}, width={width}, height={height}")
        print(f"  检测区域范围: ({left}, {top}) - ({left + width}, {top + height})")
        
        # 检查配置是否在窗口范围内
        if left + width > window_width:
            print(f"\n⚠️  警告：检测区域右边界 {left + width} 超出窗口宽度 {window_width}")
        if top + height > window_height:
            print(f"⚠️  警告：检测区域下边界 {top + height} 超出窗口高度 {window_height}")
        
        # 截图
        print(f"\n正在截图...")
        screenshot = Screenshot()
        full_screenshot = screenshot.capture_full_window()
        screenshot_width, screenshot_height = full_screenshot.size
        
        print(f"实际截图尺寸: {screenshot_width}x{screenshot_height}")
        
        # 计算缩放
        scale_x = screenshot_width / window_width if window_width > 0 else 1.0
        scale_y = screenshot_height / window_height if window_height > 0 else 1.0
        
        print(f"缩放比例: {scale_x:.2f}x{scale_y:.2f}")
        
        # 计算实际裁剪坐标
        actual_left = int(left * scale_x)
        actual_top = int(top * scale_y)
        actual_right = int((left + width) * scale_x)
        actual_bottom = int((top + height) * scale_y)
        
        print(f"\n实际裁剪坐标:")
        print(f"  配置坐标: ({left}, {top}) - ({left + width}, {top + height})")
        print(f"  实际坐标: ({actual_left}, {actual_top}) - ({actual_right}, {actual_bottom})")
        print(f"  裁剪大小: {actual_right - actual_left}x{actual_bottom - actual_top}")
        
        # 边界检查
        if actual_left < 0:
            print(f"  ⚠️  左边界 {actual_left} < 0，调整为 0")
            actual_left = 0
        if actual_top < 0:
            print(f"  ⚠️  上边界 {actual_top} < 0，调整为 0")
            actual_top = 0
        if actual_right > screenshot_width:
            print(f"  ⚠️  右边界 {actual_right} > {screenshot_width}，调整为 {screenshot_width}")
            actual_right = screenshot_width
        if actual_bottom > screenshot_height:
            print(f"  ⚠️  下边界 {actual_bottom} > {screenshot_height}，调整为 {screenshot_height}")
            actual_bottom = screenshot_height
        
        # 裁剪区域
        print(f"\n正在裁剪检测区域...")
        cropped = full_screenshot.crop((actual_left, actual_top, actual_right, actual_bottom))
        
        # 保存裁剪图像
        cropped_path = project_root / "debug_combat_region_cropped.png"
        cropped.save(cropped_path)
        print(f"✅ 裁剪区域已保存到: {cropped_path}")
        print(f"   图像尺寸: {cropped.size[0]}x{cropped.size[1]}")
        
        # 在完整截图上标记检测区域
        marked = full_screenshot.copy()
        draw = ImageDraw.Draw(marked)
        
        # 绘制检测区域框（红色）
        draw.rectangle(
            [(actual_left, actual_top), (actual_right, actual_bottom)],
            outline="red",
            width=3
        )
        
        # 添加标签
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        
        label = f"检测区域 ({left},{top})"
        draw.text(
            (actual_left, max(0, actual_top - 25)),
            label,
            fill="red",
            font=font
        )
        
        # 保存标记图像
        marked_path = project_root / "debug_combat_region_marked.png"
        marked.save(marked_path)
        print(f"✅ 标记图像已保存到: {marked_path}")
        print(f"   红色框标记了检测区域的位置")
        
        print(f"\n" + "=" * 60)
        print("诊断完成！")
        print("=" * 60)
        print(f"\n请检查以下文件：")
        print(f"  1. {cropped_path} - 裁剪的检测区域（应该包含'认输'文字）")
        print(f"  2. {marked_path} - 完整截图（红色框标记检测区域）")
        print(f"\n如果裁剪区域不包含'认输'文字，请：")
        print(f"  1. 查看 {marked_path}，确认红色框的位置")
        print(f"  2. 根据'认输'文字的实际位置，调整 config.yaml 中的 detection_region")
        print(f"  3. 坐标是相对于游戏窗口的（不是屏幕坐标）")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
