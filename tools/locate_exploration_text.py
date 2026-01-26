"""
探索度文本定位工具
用于帮助用户找到探索度文本在屏幕上的位置
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from src.ui_interaction.screenshot import Screenshot
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志（静默模式）
setup_logger(level="ERROR", console=False)


class ExplorationTextLocator:
    """探索度文本定位工具"""
    
    def __init__(self):
        """初始化定位工具"""
        try:
            self.config = get_config()
            self.screenshot = Screenshot()
        except Exception as e:
            print(f"初始化配置失败: {e}")
            raise
        
        self.root = tk.Tk()
        self.root.title("探索度文本定位工具")
        
        # 截图
        self.screenshot_img = None
        self.tk_image = None
        self.canvas = None
        self.scale_factor = 1.0  # 缩放因子
        
        # 选择区域
        self.start_x = None
        self.start_y = None
        self.rect_id = None
        self.selected_region = None
        
        self._setup_ui()
        # 延迟截图，确保窗口已显示
        self.root.after(100, self._capture_screenshot)
    
    def _setup_ui(self):
        """设置UI"""
        # 创建画布
        self.canvas = tk.Canvas(self.root, cursor="cross")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 绑定鼠标事件
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        
        # 创建按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 重新截图按钮
        btn_refresh = tk.Button(
            button_frame,
            text="重新截图",
            command=self._capture_screenshot
        )
        btn_refresh.pack(side=tk.LEFT, padx=5)
        
        # 确认按钮
        btn_confirm = tk.Button(
            button_frame,
            text="确认选择",
            command=self._confirm_selection,
            bg="#4CAF50",
            fg="white"
        )
        btn_confirm.pack(side=tk.LEFT, padx=5)
        
        # 取消按钮
        btn_cancel = tk.Button(
            button_frame,
            text="取消",
            command=self._cancel,
            bg="#f44336",
            fg="white"
        )
        btn_cancel.pack(side=tk.LEFT, padx=5)
        
        # 说明标签
        label = tk.Label(
            button_frame,
            text="提示：在截图上拖拽选择探索度文本区域",
            fg="gray"
        )
        label.pack(side=tk.LEFT, padx=10)
    
    def _capture_screenshot(self):
        """截取屏幕"""
        try:
            print("开始截图...")
            # 截图
            img = self.screenshot.capture_full_window()
            if img is None:
                raise ValueError("截图返回None")
            
            print(f"截图成功，尺寸: {img.size}")
            self.screenshot_img = img
            
            # 调整大小以适应窗口（保持宽高比）
            # 获取窗口可用大小
            self.root.update_idletasks()
            max_width = self.root.winfo_screenwidth() - 100
            max_height = self.root.winfo_screenheight() - 200
            
            img_width, img_height = img.size
            print(f"原始尺寸: {img_width}x{img_height}, 最大尺寸: {max_width}x{max_height}")
            
            if img_width == 0 or img_height == 0:
                raise ValueError(f"截图尺寸无效: {img_width}x{img_height}")
            
            scale = min(max_width / img_width, max_height / img_height, 1.0)
            self.scale_factor = scale
            
            if scale < 1.0:
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                print(f"缩放图像: {new_width}x{new_height} (缩放因子: {scale:.2f})")
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            else:
                print("图像不需要缩放")
            
            # 转换为Tkinter图像
            print("转换图像格式...")
            self.tk_image = ImageTk.PhotoImage(img)
            
            # 显示在画布上
            print("显示图像...")
            self.canvas.delete("all")
            self.canvas.config(width=img.width, height=img.height)
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)
            
            # 更新窗口大小
            self.root.update_idletasks()
            
            # 清除之前的选择
            self.selected_region = None
            self.rect_id = None
            
            print("截图完成")
            
        except Exception as e:
            error_msg = f"截图失败: {e}\n\n请检查：\n1. 窗口配置是否正确\n2. 游戏窗口是否可见\n3. 窗口区域是否在屏幕范围内"
            print(error_msg)
            import traceback
            traceback.print_exc()
            messagebox.showerror("错误", error_msg)
    
    def _on_click(self, event):
        """鼠标按下事件"""
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        
        # 删除之前的矩形
        if self.rect_id:
            self.canvas.delete(self.rect_id)
    
    def _on_drag(self, event):
        """鼠标拖拽事件"""
        if self.start_x is None or self.start_y is None:
            return
        
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        # 删除之前的矩形
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        
        # 绘制新矩形
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, cur_x, cur_y,
            outline="red", width=2
        )
    
    def _on_release(self, event):
        """鼠标释放事件"""
        if self.start_x is None or self.start_y is None:
            return
        
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)
        
        # 确保坐标顺序正确
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)
        
        # 计算实际区域（考虑截图缩放）
        if self.screenshot_img:
            orig_width, orig_height = self.screenshot_img.size
            # 使用缩放因子计算
            scale_x = orig_width / (orig_width * self.scale_factor) if self.scale_factor > 0 else 1.0
            scale_y = orig_height / (orig_height * self.scale_factor) if self.scale_factor > 0 else 1.0
            
            # 如果图像被缩放，需要反向缩放坐标
            if self.scale_factor < 1.0:
                scale_x = 1.0 / self.scale_factor
                scale_y = 1.0 / self.scale_factor
            else:
                scale_x = 1.0
                scale_y = 1.0
            
            self.selected_region = {
                'left': int(left * scale_x),
                'top': int(top * scale_y),
                'width': int((right - left) * scale_x),
                'height': int((bottom - top) * scale_y)
            }
            
            print(f"选择区域: {self.selected_region}")
    
    def _confirm_selection(self):
        """确认选择"""
        if not self.selected_region:
            messagebox.showwarning("警告", "请先选择区域")
            return
        
        region = self.selected_region
        
        # 显示选择结果
        result = f"""已选择探索度文本区域：
左边界: {region['left']}
上边界: {region['top']}
宽度: {region['width']}
高度: {region['height']}

请将以下代码添加到配置中，或直接修改 exploration_tracker.py：
"""
        
        code = f"""tracker.set_exploration_text_region(
    left={region['left']},
    top={region['top']},
    width={region['width']},
    height={region['height']}
)"""
        
        # 创建结果窗口
        result_window = tk.Toplevel(self.root)
        result_window.title("选择结果")
        result_window.geometry("500x300")
        
        text_widget = tk.Text(result_window, wrap=tk.WORD)
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert("1.0", result + code)
        text_widget.config(state=tk.DISABLED)
        
        # 保存到配置文件
        save_frame = tk.Frame(result_window)
        save_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def save_to_config():
            """保存到配置文件"""
            config_path = project_root / "config" / "config.yaml"
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                if 'exploration' not in config:
                    config['exploration'] = {}
                
                config['exploration']['text_region'] = region
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                messagebox.showinfo("成功", f"已保存到配置文件: {config_path}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
        
        btn_save = tk.Button(
            save_frame,
            text="保存到配置文件",
            command=save_to_config,
            bg="#2196F3",
            fg="white"
        )
        btn_save.pack(side=tk.LEFT, padx=5)
        
        btn_close = tk.Button(
            save_frame,
            text="关闭",
            command=result_window.destroy
        )
        btn_close.pack(side=tk.LEFT, padx=5)
    
    def _cancel(self):
        """取消"""
        self.root.destroy()
    
    def run(self):
        """运行工具"""
        self.root.mainloop()


def main():
    """主函数"""
    try:
        print("=" * 50)
        print("探索度文本定位工具")
        print("=" * 50)
        print("\n提示：如果窗口显示白屏，请先运行 test_screenshot.py 测试截图功能")
        print("=" * 50 + "\n")
        
        locator = ExplorationTextLocator()
        locator.run()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n工具启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")


if __name__ == "__main__":
    main()
