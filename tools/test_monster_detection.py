"""
测试怪物检测功能
用于验证怪物模板和检测配置是否正确
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.monster_detection.monster_detector import MonsterDetector
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


def main():
    """测试怪物检测"""
    try:
        print("=" * 50)
        print("测试怪物检测功能")
        print("=" * 50)
        
        # 加载配置
        print("\n1. 加载配置...")
        config = get_config()
        threshold = config.get('recognition.template_match_threshold', 0.6)
        print(f"✅ 配置加载成功")
        print(f"   模板匹配置信度阈值: {threshold}")
        
        # 初始化工具
        print("\n2. 初始化工具...")
        screenshot = Screenshot()
        detector = MonsterDetector()
        print("✅ 工具初始化成功")
        
        # 检查模板文件
        print("\n3. 检查模板文件...")
        template_path = project_root / "templates" / detector.monster_template
        if template_path.exists():
            print(f"✅ 模板文件存在: {template_path}")
            from PIL import Image
            template_img = Image.open(template_path)
            print(f"   模板尺寸: {template_img.size}")
        else:
            print(f"❌ 模板文件不存在: {template_path}")
            print("   请确保怪物模板文件存在于 templates/ 目录")
            print("   可以从游戏中截图一个怪物图标保存为 templates/monster.png")
            return
        
        # 截图测试
        print("\n4. 测试截图...")
        try:
            full_screenshot = screenshot.capture_full_window()
            print(f"✅ 截图成功，尺寸: {full_screenshot.size}")
            
            # 保存测试图像
            test_image_path = project_root / "test_monster_detection.png"
            full_screenshot.save(test_image_path)
            print(f"   测试图像已保存到: {test_image_path}")
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return
        
        # 怪物检测测试
        print("\n5. 测试怪物检测...")
        try:
            monsters = detector.detect_monsters(full_screenshot)
            
            if monsters:
                print(f"✅ 检测到 {len(monsters)} 个怪物！")
                print("\n   怪物位置详情：")
                for i, monster in enumerate(monsters):
                    x, y, confidence = monster
                    print(f"   怪物{i+1}: 位置({x}, {y}), 置信度: {confidence:.3f}")
                
                # 在截图上标记怪物位置（可选）
                try:
                    from PIL import ImageDraw
                    marked_image = full_screenshot.copy()
                    draw = ImageDraw.Draw(marked_image)
                    for x, y, conf in monsters:
                        # 绘制一个红色圆圈标记怪物位置
                        draw.ellipse([x-10, y-10, x+10, y+10], outline="red", width=2)
                    
                    marked_path = project_root / "test_monster_detection_marked.png"
                    marked_image.save(marked_path)
                    print(f"\n   标记图像已保存到: {marked_path}")
                    print("   可以查看标记图像确认检测位置是否正确")
                except Exception as e:
                    print(f"   标记图像保存失败: {e}")
            else:
                print("❌ 未检测到任何怪物")
                print("\n   可能的原因：")
                print("   1. 模板文件不匹配（模板图像与实际怪物图标不一致）")
                print("   2. 置信度阈值过高（当前阈值: {:.2f}）".format(threshold))
                print("   3. 地图上确实没有怪物")
                print("\n   建议：")
                print("   1. 检查 test_monster_detection.png 确认地图上是否有怪物")
                print("   2. 检查 templates/monster.png 是否与游戏中的怪物图标一致")
                print("   3. 尝试降低阈值（在 config.yaml 中设置 recognition.template_match_threshold）")
                print("   4. 重新截图一个更清晰的怪物模板")
                return
                
        except FileNotFoundError as e:
            print(f"❌ 模板文件未找到: {e}")
            return
        except Exception as e:
            print(f"❌ 怪物检测出错: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # 总结
        print("\n" + "=" * 50)
        print("✅ 怪物检测测试通过！")
        print("=" * 50)
        print(f"\n检测到 {len(monsters)} 个怪物")
        print(f"模板文件: {template_path}")
        print(f"置信度阈值: {threshold}")
        print(f"\n测试图像: {test_image_path}")
        if Path(project_root / "test_monster_detection_marked.png").exists():
            print(f"标记图像: {project_root / 'test_monster_detection_marked.png'}")
        
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
