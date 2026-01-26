"""
分析模板图像质量，帮助用户改进模板
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from PIL import Image
from src.core.config import get_config


def analyze_template(template_path: str):
    """分析模板图像"""
    print("=" * 60)
    print("模板图像质量分析")
    print("=" * 60)
    
    template = cv2.imread(str(template_path))
    if template is None:
        print(f"❌ 无法加载模板: {template_path}")
        return
    
    # 基本信息
    h, w = template.shape[:2]
    print(f"\n模板尺寸: {w}x{h} 像素")
    
    # 转换为灰度
    if len(template.shape) == 3:
        gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
    else:
        gray = template
    
    # 统计信息
    mean_brightness = np.mean(gray)
    std_brightness = np.std(gray)
    min_brightness = np.min(gray)
    max_brightness = np.max(gray)
    contrast = std_brightness / (mean_brightness + 1e-5)
    
    print(f"\n亮度统计:")
    print(f"  平均值: {mean_brightness:.2f}")
    print(f"  标准差: {std_brightness:.2f}")
    print(f"  范围: {min_brightness} - {max_brightness}")
    print(f"  对比度: {contrast:.4f}")
    
    # 评估
    print(f"\n质量评估:")
    
    issues = []
    suggestions = []
    
    # 尺寸检查
    if w < 30 or h < 30:
        issues.append("模板尺寸过小（<30像素）")
        suggestions.append("建议模板尺寸至少 50x50 像素")
    elif w > 200 or h > 200:
        issues.append("模板尺寸过大（>200像素）")
        suggestions.append("建议模板尺寸不超过 150x150 像素")
    else:
        print("  ✅ 模板尺寸合适")
    
    # 对比度检查
    if contrast < 0.1:
        issues.append("对比度过低")
        suggestions.append("模板应该包含清晰的边缘和特征")
    elif contrast > 1.5:
        issues.append("对比度过高，可能包含过多噪声")
        suggestions.append("检查模板是否包含不必要的背景")
    else:
        print("  ✅ 对比度合适")
    
    # 亮度检查
    if mean_brightness < 50:
        issues.append("图像过暗")
        suggestions.append("确保模板清晰可见")
    elif mean_brightness > 200:
        issues.append("图像过亮")
        suggestions.append("检查模板是否过度曝光")
    else:
        print("  ✅ 亮度合适")
    
    # 背景检查
    # 计算边缘密度（边缘越多，特征越明显）
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (w * h)
    
    print(f"  边缘密度: {edge_density:.4f}")
    if edge_density < 0.05:
        issues.append("边缘特征不明显")
        suggestions.append("模板应该包含清晰的怪物特征（轮廓、颜色等）")
    elif edge_density > 0.3:
        issues.append("边缘过多，可能包含复杂背景")
        suggestions.append("尝试裁剪模板，只保留怪物图标部分")
    else:
        print("  ✅ 边缘特征合适")
    
    # 输出问题和建议
    if issues:
        print(f"\n⚠️  发现的问题:")
        for issue in issues:
            print(f"   - {issue}")
        
        print(f"\n💡 改进建议:")
        for suggestion in suggestions:
            print(f"   - {suggestion}")
    else:
        print("\n✅ 模板质量良好")
    
    # 保存分析结果图像
    output_path = project_root / "template_analysis.png"
    
    # 创建分析图像
    analysis_img = template.copy()
    if len(analysis_img.shape) == 2:
        analysis_img = cv2.cvtColor(analysis_img, cv2.COLOR_GRAY2BGR)
    
    # 绘制边缘
    edges_colored = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
    edges_colored[edges > 0] = [0, 255, 0]  # 绿色边缘
    
    # 合并图像
    combined = np.hstack([analysis_img, edges_colored])
    
    cv2.imwrite(str(output_path), combined)
    print(f"\n分析结果图像已保存到: {output_path}")
    print("  (左侧: 原始模板, 右侧: 边缘检测结果)")


def main():
    """主函数"""
    config = get_config()
    template_path = project_root / "templates" / "monster.png"
    
    if not template_path.exists():
        print(f"❌ 模板文件不存在: {template_path}")
        print(f"请确保模板文件存在于: {project_root / 'templates'}")
        return
    
    analyze_template(template_path)


if __name__ == "__main__":
    main()
