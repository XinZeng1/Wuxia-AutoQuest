"""
测试截图功能
用于调试截图问题
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)

def main():
    """测试截图"""
    try:
        print("=" * 50)
        print("测试截图功能")
        print("=" * 50)
        
        # 加载配置
        print("\n1. 加载配置...")
        config = get_config()
        window = config.window
        print(f"窗口配置: {window}")
        
        # 初始化截图工具
        print("\n2. 初始化截图工具...")
        screenshot = Screenshot()
        
        # 截图
        print("\n3. 开始截图...")
        img = screenshot.capture_full_window()
        
        if img is None:
            print("❌ 截图失败：返回None")
            return
        
        print(f"✅ 截图成功！")
        print(f"   图像尺寸: {img.size}")
        print(f"   图像模式: {img.mode}")
        
        # 保存测试图像
        test_image_path = project_root / "test_screenshot.png"
        img.save(test_image_path)
        print(f"\n4. 测试图像已保存到: {test_image_path}")
        print("   请检查图像是否正确")
        
        # 检查窗口区域
        print("\n5. 检查窗口区域...")
        print(f"   窗口位置: ({window.get('x', 0)}, {window.get('y', 0)})")
        print(f"   窗口大小: {window.get('width', 0)}x{window.get('height', 0)}")
        
        # 验证截图尺寸
        if img.size[0] != window.get('width', 0) or img.size[1] != window.get('height', 0):
            print(f"⚠️  警告：截图尺寸与配置不一致")
            print(f"   配置尺寸: {window.get('width', 0)}x{window.get('height', 0)}")
            print(f"   实际尺寸: {img.size[0]}x{img.size[1]}")
        else:
            print("✅ 截图尺寸与配置一致")
        
        print("\n" + "=" * 50)
        print("测试完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
