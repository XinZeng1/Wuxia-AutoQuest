
import mss
import numpy as np
import cv2


import mss
import numpy as np
import cv2

import Quartz.CoreGraphics as CG
import numpy as np
import cv2

def capture_mac_retina(region):
    """
    修正版：处理字节对齐和颜色空间转换，防止乱码
    """
    # 1. 创建坐标区域
    rect = CG.CGRectMake(region['left'], region['top'], region['width'], region['height'])
    
    # 2. 截取图像
    image_ref = CG.CGWindowListCreateImage(rect, CG.kCGWindowListOptionOnScreenOnly, CG.kCGNullWindowID, CG.kCGWindowImageDefault)
    
    if not image_ref:
        return None

    # 3. 获取关键元数据
    width = CG.CGImageGetWidth(image_ref)
    height = CG.CGImageGetHeight(image_ref)
    bytes_per_row = CG.CGImageGetBytesPerRow(image_ref) # 关键：获取系统实际的每行字节数
    
    # 4. 提取原始字节数据
    data_provider = CG.CGImageGetDataProvider(image_ref)
    data = CG.CGDataProviderCopyData(data_provider)
    
    # 5. 将数据转为 numpy 数组
    # 先转成包含填充字节的矩阵
    img_np = np.frombuffer(data, dtype=np.uint8).reshape((height, bytes_per_row))
    
    # 6. 切除右侧的填充字节 (Padding)
    # 每个像素 4 字节，实际需要的宽度是 width * 4
    actual_data_width = width * 4
    img_np = img_np[:, :actual_data_width].reshape((height, width, 4))
    
    # 7. 颜色空间转换
    # Quartz 默认通常是 BGRA，我们需要转为 BGR 供 OpenCV 使用
    # 注意：如果颜色还是不对，尝试 cv2.COLOR_RGBA2BGR
    return cv2.cvtColor(img_np, cv2.COLOR_BGRA2BGR)

def preprocess_for_mac_ocr(img):
    # 1. 既然是 Retina，图像本身像素已经很多，我们先转灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. 【核心微调：对比度拉伸】
    # 将图像中最亮的部分变纯白，最暗的部分变纯黑，强制拉开差距
    # 这能有效抵消 Mac 字体边缘的模糊感
    xp = [0, 64, 128, 192, 255]
    fp = [0, 16, 128, 240, 255] # 这是一个 S 曲线，压制灰色，增强黑白
    x = np.arange(256)
    table = np.interp(x, xp, fp).astype('uint8')
    gray = cv2.LUT(gray, table)
    
    # 3. 【增强锐化】使用更强劲的拉普拉斯算子
    # 专门对付 Mac 的平滑渲染，强制勾勒文字边缘
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    
    # 4. 【二值化逻辑】改用自适应阈值，处理 UI 背景明暗不均的问题
    binary = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 15, 4
    )
    
    # 5. 【降噪】去除二值化产生的微小杂点
    kernel_clean = np.ones((1,1), np.uint8)
    processed = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_clean)
    
    return processed


if __name__ == "__main__":

    left = 100 
    top = 400
    width = 674
    height = 316

    region = {
        'left': left,
        'top': top,
        'width': width,
        'height': height
    }
    # get_optimized_screenshot(region)

        # 运行这个片段
    # region = {"top": 100, "left": 100, "width": 400, "height": 200}
    img = capture_mac_retina(region)
    processed = preprocess_for_mac_ocr(img)

    cv2.imwrite("mac_debug_raw.png", img)      # 原始图
    cv2.imwrite("mac_debug_final.png", processed)  # 处理后的图