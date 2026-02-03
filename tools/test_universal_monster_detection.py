"""
测试通用怪物检测（不依赖关键词）

测试基于等级格式的怪物检测
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.ui_interaction.screenshot import Screenshot
from src.monster_detection.monster_detector import MonsterDetector
from src.core.logger import setup_logger, get_logger
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

setup_logger(level='DEBUG', console=True)
logger = get_logger(__name__)


def visualize_monsters(screenshot: Image.Image, monsters, window_size):
    """可视化检测到的怪物

    Args:
        screenshot: 截图（物理像素）
        monsters: 怪物列表，坐标为窗口逻辑坐标
        window_size: 窗口尺寸 (width, height)
    """
    # 转换为可绘制的图像
    vis_img = screenshot.copy()
    draw = ImageDraw.Draw(vis_img)

    # 尝试加载字体
    try:
        font = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 20)
    except:
        font = ImageFont.load_default()

    # 计算坐标转换比例（窗口逻辑坐标 -> 截图物理像素）
    window_width, window_height = window_size
    scale_x = screenshot.width / window_width
    scale_y = screenshot.height / window_height

    logger.debug(f"可视化坐标转换: 窗口({window_width}x{window_height}) -> 截图({screenshot.width}x{screenshot.height})")
    logger.debug(f"缩放因子: x={scale_x:.2f}, y={scale_y:.2f}")

    # 绘制每个怪物
    for i, (x, y, conf) in enumerate(monsters):
        # 将窗口逻辑坐标转换为截图物理像素坐标
        screenshot_x = int(x * scale_x)
        screenshot_y = int(y * scale_y)

        logger.debug(f"怪物#{i+1}: 窗口坐标({x}, {y}) -> 截图坐标({screenshot_x}, {screenshot_y})")

        # 绘制十字标记
        size = 20
        draw.line([(screenshot_x - size, screenshot_y), (screenshot_x + size, screenshot_y)], fill='red', width=3)
        draw.line([(screenshot_x, screenshot_y - size), (screenshot_x, screenshot_y + size)], fill='red', width=3)

        # 绘制圆圈
        draw.ellipse([screenshot_x - 10, screenshot_y - 10, screenshot_x + 10, screenshot_y + 10], outline='red', width=2)

        # 绘制编号和置信度
        text = f"#{i+1} ({conf:.2f})"
        draw.text((screenshot_x + 15, screenshot_y - 10), text, fill='red', font=font)

    return vis_img


def main():
    """测试通用怪物检测"""
    logger.info("=" * 60)
    logger.info("测试通用怪物检测（基于等级格式，不依赖关键词）")
    logger.info("=" * 60)

    # 初始化
    screenshot_tool = Screenshot()
    detector = MonsterDetector()

    # 确认使用OCR方法
    logger.info(f"检测方法: {detector.detection_method}")
    logger.info(f"OCR预处理模式: {detector.config.get('monster.ocr_preprocess_mode', 'light')}")
    logger.info(f"关键词列表（仅作补充）: {detector.monster_name_keywords}")

    # 截取屏幕
    logger.info("\n正在截取屏幕...")
    screenshot = screenshot_tool.capture_full_window()
    logger.info(f"截图尺寸: {screenshot.size}")

    # 检测怪物
    logger.info("\n开始检测怪物...")
    monsters = detector.detect_monsters(screenshot)

    if monsters:
        logger.info(f"\n✅ 检测到 {len(monsters)} 个怪物:")
        for i, (x, y, conf) in enumerate(monsters):
            logger.info(f"  怪物 #{i+1}: 位置({x}, {y}), 置信度: {conf:.3f}")

        # 可视化
        logger.info("\n生成可视化图像...")
        window_size = screenshot_tool.get_window_size()
        vis_img = visualize_monsters(screenshot, monsters, window_size)

        # 保存结果
        output_path = Path(__file__).parent.parent / "monster_detection_result.png"
        vis_img.save(output_path)
        logger.info(f"✅ 可视化结果已保存到: {output_path}")

        # 显示图像（可选）
        try:
            import cv2
            vis_array = np.array(vis_img)
            vis_bgr = cv2.cvtColor(vis_array, cv2.COLOR_RGB2BGR)
            cv2.imshow("Monster Detection Result", vis_bgr)
            logger.info("\n按任意键关闭窗口...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except Exception as e:
            logger.warning(f"无法显示图像: {e}")

    else:
        logger.warning("\n⚠️  未检测到任何怪物")
        logger.info("\n可能的原因:")
        logger.info("1. 屏幕上没有怪物")
        logger.info("2. 怪物名称格式不符合预期（没有等级信息）")
        logger.info("3. OCR识别失败")
        logger.info("\n建议:")
        logger.info("- 确保游戏窗口可见且包含怪物")
        logger.info("- 检查 config.yaml 中的窗口配置")
        logger.info("- 尝试调整 monster.ocr_preprocess_mode")

    logger.info("\n" + "=" * 60)


if __name__ == "__main__":
    main()
