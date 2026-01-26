"""
测试基于怪物名称的检测功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PIL import Image, ImageDraw, ImageFont
from src.monster_detection.monster_detector import MonsterDetector
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


def main():
    """主函数"""
    try:
        print("=" * 60)
        print("测试基于怪物名称的检测功能")
        print("=" * 60)
        
        # 初始化
        detector = MonsterDetector()
        config = get_config()
        
        # 检查检测方法
        detection_method = config.get('monster.detection_method', 'name')
        print(f"\n当前检测方法: {detection_method}")
        
        if detection_method != 'name':
            print("\n⚠️  当前配置使用的是模板匹配方法")
            print("要使用名称检测，请在 config/config.yaml 中设置:")
            print("  monster:")
            print("    detection_method: 'name'")
            print("\n继续测试名称检测方法...")
        
        # 截图
        print("\n正在截图...")
        screenshot = detector.screenshot.capture_full_window()
        print(f"截图尺寸: {screenshot.size}")
        
        # 保存截图
        screenshot_path = project_root / "test_monster_name_screenshot.png"
        screenshot.save(screenshot_path)
        print(f"截图已保存到: {screenshot_path}")
        
        # 使用名称检测
        print("\n使用名称检测方法检测怪物...")
        monsters = detector.detect_monsters(screenshot, method='name')
        
        if monsters:
            print(f"\n✅ 检测到 {len(monsters)} 个怪物:")
            for i, (x, y, conf) in enumerate(monsters):
                print(f"  怪物{i+1}: 位置({x}, {y}), 置信度: {conf:.3f}")
            
            # 在截图上标记检测到的怪物
            marked_image = screenshot.copy()
            draw = ImageDraw.Draw(marked_image)
            
            for i, (x, y, conf) in enumerate(monsters):
                # 绘制标记
                radius = 15
                draw.ellipse(
                    [x - radius, y - radius, x + radius, y + radius],
                    outline='red',
                    width=3
                )
                # 绘制编号
                try:
                    draw.text((x - radius, y - radius - 20), f"{i+1}", fill='red')
                except:
                    pass
            
            # 保存标记后的图像
            marked_path = project_root / "test_monster_name_marked.png"
            marked_image.save(marked_path)
            print(f"\n标记后的图像已保存到: {marked_path}")
        else:
            print("\n❌ 未检测到任何怪物")
            print("\n可能的原因:")
            print("1. 屏幕上没有显示怪物名称")
            print("2. OCR无法识别怪物名称文本")
            print("3. 怪物名称不包含配置的关键词")
            print("\n建议:")
            print("1. 检查 config/config.yaml 中的 monster.name_keywords 配置")
            print("2. 确保游戏界面上显示了怪物名称")
            print("3. 尝试调整OCR语言设置")
        
        # 显示配置的关键词
        keywords = config.get('monster.name_keywords', [])
        print(f"\n当前配置的怪物名称关键词: {keywords}")
        print("\n如果检测不到，可以添加更多关键词到配置中")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
