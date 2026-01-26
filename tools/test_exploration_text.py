"""
探索度文字截图和识别测试工具
用于验证探索度文本区域配置是否正确
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import messagebox, scrolledtext
from PIL import Image, ImageTk, ImageDraw, ImageFont
from src.ui_interaction.screenshot import Screenshot
from src.exploration_tracking.exploration_tracker import ExplorationTracker
from src.core.config import get_config
from src.core.logger import setup_logger

# 设置日志
setup_logger(level="INFO", console=True)


class ExplorationTextTester:
    """探索度文字测试工具"""
    
    def __init__(self):
        """初始化测试工具"""
        try:
            self.config = get_config()
            self.screenshot = Screenshot()
            self.tracker = ExplorationTracker()
        except Exception as e:
            print(f"初始化失败: {e}")
            raise
        
        self.root = tk.Tk()
        self.root.title("探索度文字测试工具")
        self.root.geometry("800x700")
        
        # 截图图像
        self.cropped_image = None
        self.tk_image = None
        
        self._setup_ui()
        self._test_recognition()
    
    def _setup_ui(self):
        """设置UI"""
        # 创建主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 配置信息显示
        config_frame = tk.LabelFrame(main_frame, text="当前配置", padx=10, pady=10)
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.config_text = tk.Text(config_frame, height=4, wrap=tk.WORD)
        self.config_text.pack(fill=tk.X)
        self.config_text.config(state=tk.DISABLED)
        
        # 截图显示区域
        image_frame = tk.LabelFrame(main_frame, text="探索度文本区域截图", padx=10, pady=10)
        image_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 画布用于显示图像
        self.canvas = tk.Canvas(image_frame, bg="white", width=400, height=100)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 识别结果
        result_frame = tk.LabelFrame(main_frame, text="OCR识别结果", padx=10, pady=10)
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.result_text = scrolledtext.ScrolledText(result_frame, height=6, wrap=tk.WORD)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        
        # 按钮框架
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 重新测试按钮
        btn_test = tk.Button(
            button_frame,
            text="重新测试",
            command=self._test_recognition,
            bg="#4CAF50",
            fg="white",
            width=12
        )
        btn_test.pack(side=tk.LEFT, padx=5)
        
        # 保存截图按钮
        btn_save = tk.Button(
            button_frame,
            text="保存截图",
            command=self._save_screenshot,
            bg="#2196F3",
            fg="white",
            width=12
        )
        btn_save.pack(side=tk.LEFT, padx=5)
        
        # 调整配置按钮
        btn_adjust = tk.Button(
            button_frame,
            text="调整配置",
            command=self._show_adjust_dialog,
            bg="#FF9800",
            fg="white",
            width=12
        )
        btn_adjust.pack(side=tk.LEFT, padx=5)
        
        # 关闭按钮
        btn_close = tk.Button(
            button_frame,
            text="关闭",
            command=self.root.destroy,
            width=12
        )
        btn_close.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        self.status_label = tk.Label(
            main_frame,
            text="准备就绪",
            fg="gray",
            anchor=tk.W
        )
        self.status_label.pack(fill=tk.X, pady=(5, 0))
    
    def _update_config_display(self):
        """更新配置显示"""
        region = self.tracker.get_exploration_text_region()
        config_info = f"""文本区域配置:
  左边界: {region['left']} 像素
  上边界: {region['top']} 像素
  宽度: {region['width']} 像素
  高度: {region['height']} 像素
"""
        self.config_text.config(state=tk.NORMAL)
        self.config_text.delete("1.0", tk.END)
        self.config_text.insert("1.0", config_info)
        self.config_text.config(state=tk.DISABLED)
    
    def _capture_text_region(self):
        """截取探索度文本区域"""
        try:
            # 获取完整截图
            full_screenshot = self.screenshot.capture_full_window()
            
            # 获取文本区域配置
            region = self.tracker.get_exploration_text_region()
            
            # 裁剪文本区域
            left = region['left']
            top = region['top']
            right = left + region['width']
            bottom = top + region['height']
            
            # 检查边界
            img_width, img_height = full_screenshot.size
            if left < 0 or top < 0 or right > img_width or bottom > img_height:
                raise ValueError(
                    f"文本区域超出截图范围！\n"
                    f"截图尺寸: {img_width}x{img_height}\n"
                    f"文本区域: ({left}, {top}) - ({right}, {bottom})"
                )
            
            # 裁剪
            self.cropped_image = full_screenshot.crop((left, top, right, bottom))
            
            # 在图像上绘制边框（用于可视化）
            draw = ImageDraw.Draw(self.cropped_image)
            draw.rectangle(
                [(0, 0), (self.cropped_image.width - 1, self.cropped_image.height - 1)],
                outline="red",
                width=2
            )
            
            return True
            
        except Exception as e:
            self.status_label.config(text=f"截图失败: {e}", fg="red")
            messagebox.showerror("错误", f"截图失败:\n{e}")
            return False
    
    def _display_image(self):
        """显示截图"""
        if self.cropped_image is None:
            return
        
        try:
            # 调整图像大小以适应画布（保持宽高比）
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            
            if canvas_width <= 1 or canvas_height <= 1:
                # 如果画布还没初始化，使用默认大小
                canvas_width = 400
                canvas_height = 100
            
            img_width, img_height = self.cropped_image.size
            scale = min(
                canvas_width / img_width,
                canvas_height / img_height,
                1.0  # 不放大
            )
            
            if scale < 1.0:
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                display_image = self.cropped_image.resize(
                    (new_width, new_height),
                    Image.Resampling.LANCZOS
                )
            else:
                display_image = self.cropped_image
            
            # 转换为Tkinter图像
            self.tk_image = ImageTk.PhotoImage(display_image)
            
            # 清除画布并显示图像
            self.canvas.delete("all")
            self.canvas.config(width=display_image.width, height=display_image.height)
            self.canvas.create_image(
                display_image.width // 2,
                display_image.height // 2,
                image=self.tk_image
            )
            
        except Exception as e:
            print(f"显示图像失败: {e}")
    
    def _test_recognition(self):
        """测试OCR识别"""
        self.status_label.config(text="正在测试...", fg="blue")
        self.root.update()
        
        try:
            # 更新配置显示
            self._update_config_display()
            
            # 截取文本区域
            if not self._capture_text_region():
                return
            
            # 显示截图
            self._display_image()
            
            # OCR识别
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, "正在识别...\n")
            self.root.update()
            
            # 识别文本
            text = self.tracker.recognize_exploration_text(self.cropped_image)
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, f"原始识别文本: {text}\n\n")
            
            # 解析数值
            value = self.tracker.parse_exploration_value(text)
            if value is not None:
                self.result_text.insert(tk.END, f"解析的探索度: {value}%\n\n")
                self.result_text.insert(tk.END, "✅ 识别成功！\n")
                self.status_label.config(text="识别成功", fg="green")
            else:
                self.result_text.insert(tk.END, "❌ 无法解析探索度数值\n\n")
                self.result_text.insert(tk.END, "可能的原因：\n")
                self.result_text.insert(tk.END, "1. 文本区域配置不正确\n")
                self.result_text.insert(tk.END, "2. OCR识别失败\n")
                self.result_text.insert(tk.END, "3. 文本格式不符合预期\n")
                self.status_label.config(text="识别失败", fg="red")
            
            # 显示图像信息
            img_info = f"\n截图信息:\n"
            img_info += f"  尺寸: {self.cropped_image.size[0]}x{self.cropped_image.size[1]}\n"
            img_info += f"  模式: {self.cropped_image.mode}\n"
            self.result_text.insert(tk.END, img_info)
            
        except Exception as e:
            error_msg = f"测试失败: {e}"
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert(tk.END, error_msg)
            self.status_label.config(text=error_msg, fg="red")
            messagebox.showerror("错误", error_msg)
            import traceback
            traceback.print_exc()
    
    def _save_screenshot(self):
        """保存截图"""
        if self.cropped_image is None:
            messagebox.showwarning("警告", "没有可保存的截图")
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
                initialfile="exploration_text.png"
            )
            
            if filename:
                self.cropped_image.save(filename)
                messagebox.showinfo("成功", f"截图已保存到:\n{filename}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
    
    def _show_adjust_dialog(self):
        """显示调整配置对话框"""
        dialog = tk.Toplevel(self.root)
        dialog.title("调整配置")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 获取当前配置
        region = self.tracker.get_exploration_text_region()
        
        # 创建输入框
        tk.Label(dialog, text="左边界:").grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        entry_left = tk.Entry(dialog, width=10)
        entry_left.insert(0, str(region['left']))
        entry_left.grid(row=0, column=1, padx=10, pady=10)
        
        tk.Label(dialog, text="上边界:").grid(row=1, column=0, padx=10, pady=10, sticky=tk.W)
        entry_top = tk.Entry(dialog, width=10)
        entry_top.insert(0, str(region['top']))
        entry_top.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(dialog, text="宽度:").grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)
        entry_width = tk.Entry(dialog, width=10)
        entry_width.insert(0, str(region['width']))
        entry_width.grid(row=2, column=1, padx=10, pady=10)
        
        tk.Label(dialog, text="高度:").grid(row=3, column=0, padx=10, pady=10, sticky=tk.W)
        entry_height = tk.Entry(dialog, width=10)
        entry_height.insert(0, str(region['height']))
        entry_height.grid(row=3, column=1, padx=10, pady=10)
        
        def save_config():
            """保存配置"""
            try:
                left = int(entry_left.get())
                top = int(entry_top.get())
                width = int(entry_width.get())
                height = int(entry_height.get())
                
                if width <= 0 or height <= 0:
                    raise ValueError("宽度和高度必须大于0")
                
                # 更新配置
                self.tracker.set_exploration_text_region(left, top, width, height)
                
                # 保存到配置文件
                import yaml
                config_path = project_root / "config" / "config.yaml"
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                
                if 'exploration' not in config:
                    config['exploration'] = {}
                
                config['exploration']['text_region'] = {
                    'left': left,
                    'top': top,
                    'width': width,
                    'height': height
                }
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
                
                messagebox.showinfo("成功", "配置已保存")
                dialog.destroy()
                self._test_recognition()  # 重新测试
                
            except ValueError as e:
                messagebox.showerror("错误", f"无效的输入: {e}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
        
        # 按钮
        btn_frame = tk.Frame(dialog)
        btn_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text="保存", command=save_config, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
    
    def run(self):
        """运行工具"""
        self.root.mainloop()


def main():
    """主函数"""
    try:
        print("=" * 50)
        print("探索度文字测试工具")
        print("=" * 50)
        print("\n功能：")
        print("1. 根据配置截取探索度文本区域")
        print("2. 显示截图结果")
        print("3. 测试OCR识别")
        print("4. 验证配置是否正确")
        print("=" * 50 + "\n")
        
        tester = ExplorationTextTester()
        tester.run()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n工具启动失败: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")


if __name__ == "__main__":
    main()
