import os
import pandas as pd
import numpy as np
import customtkinter as ctk
from tkinter import filedialog, messagebox

# --- 核心计算函数 ---
def calculate_features(file_path):
    try:
        # 读取 Excel 文件，自动寻找包含数据的 Sheet
        df = pd.read_excel(file_path)
        
        # 兼容不同的中英文表头，防止操作员用错模板
        disp_col = next((col for col in df.columns if '位移' in col or 'disp' in col.lower()), None)
        force_col = next((col for col in df.columns if '力' in col or 'force' in col.lower()), None)
        
        if not disp_col or not force_col:
            return None, "Error: Excel missing 'Displacement(位移)' or 'Force(力值)' column."

        disp = df[disp_col].values
        force = df[force_col].values
        
        # 寻找最大力 (压入最深点，用于区分下压和回弹)
        max_idx = np.argmax(force)
        
        # 如果曲线数据太短或者转折点不明显，则报错
        if max_idx < 5 or max_idx > len(force) - 5:
            return None, "Error: Curve data is incomplete or corrupted."

        # 分离下压(Loading)与回弹(Unloading)曲线
        load_disp = disp[:max_idx+1]
        load_force = force[:max_idx+1]
        
        unload_disp = disp[max_idx:]
        unload_force = force[max_idx:]

        # --- 特征 1: Loading Slope (下压刚度) ---
        max_force = force[max_idx]
        # 截取最大力 20% 到 80% 之间的线性区间
        valid_load = np.where((load_force > max_force * 0.2) & (load_force < max_force * 0.8))[0]
        if len(valid_load) > 2:
            slope, _ = np.polyfit(load_disp[valid_load], load_force[valid_load], 1)
            loading_stiffness = abs(slope)
        else:
            loading_stiffness = 0.0

        # --- 特征 2: Hysteresis Area (迟滞环面积/损耗能量) ---
        work_done = np.trapz(load_force, load_disp)
        energy_returned = abs(np.trapz(unload_force, unload_disp))
        hysteresis_area = work_done - energy_returned

        return (loading_stiffness, hysteresis_area), "Success"

    except Exception as e:
        error_msg = str(e)
        if 'xlrd' in error_msg.lower() or '.xls' in error_msg.lower():
            return None, (
                "This tool does not support the old .xls format.\n\n"
                "Please open your file in Excel and save it as "
                "\".xlsx\" (Excel Workbook), then try again."
            )
        return None, f"Error reading file: {error_msg}"


# --- 图形界面 (GUI) 逻辑 ---
class DelamJudgeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 主窗口设置
        self.title("Apple Logo Delam Auto-Judge Tool v2.0")
        self.geometry("550x450")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # 顶部标题
        self.lbl_title = ctk.CTkLabel(self, text="Logo Delam Inspection", font=("Helvetica", 24, "bold"))
        self.lbl_title.pack(pady=(20, 10))

        # --- 阈值设置区域 (Threshold Settings) ---
        self.frame_settings = ctk.CTkFrame(self)
        self.frame_settings.pack(pady=10, padx=20, fill="x")
        
        # 标题栏
        ctk.CTkLabel(self.frame_settings, text="Pass/Fail Threshold Settings", font=("Helvetica", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=5)

        # 1. Slope 阈值输入
        ctk.CTkLabel(self.frame_settings, text="Min Loading Slope (>):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_slope = ctk.CTkEntry(self.frame_settings, width=100)
        self.entry_slope.insert(0, "7.0") # 默认值 7.0
        self.entry_slope.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # 2. Area 阈值输入
        ctk.CTkLabel(self.frame_settings, text="Max Hysteresis Area (<):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
        self.entry_area = ctk.CTkEntry(self.frame_settings, width=100)
        self.entry_area.insert(0, "0.145") # 默认值 0.145
        self.entry_area.grid(row=2, column=1, padx=10, pady=5, sticky="w")

        # --- 上传与判定按钮 ---
        self.btn_upload = ctk.CTkButton(self, text="Select Excel Data & Judge", command=self.process_file, font=("Helvetica", 16, "bold"), height=45, fg_color="#0A84FF")
        self.btn_upload.pack(pady=15)

        # --- 结果显示区 ---
        self.lbl_result = ctk.CTkLabel(self, text="Ready", font=("Helvetica", 48, "bold"), text_color="gray")
        self.lbl_result.pack(pady=(10, 0))

        # 具体计算数值显示区
        self.lbl_details = ctk.CTkLabel(self, text="Please select a file to begin.", font=("Helvetica", 14), text_color="lightgray")
        self.lbl_details.pack(pady=5)

    def process_file(self):
        # 1. 获取用户输入的最新阈值
        try:
            current_threshold_slope = float(self.entry_slope.get())
            current_threshold_area = float(self.entry_area.get())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numeric values for thresholds.")
            return

        # 2. 弹出文件选择框，仅支持 .xlsx
        file_path = filedialog.askopenfilename(filetypes=[("Excel Files", "*.xlsx")])
        if not file_path:
            return

        # 检查是否为旧版 .xls 格式
        if file_path.lower().endswith('.xls') and not file_path.lower().endswith('.xlsx'):
            messagebox.showerror(
                "Unsupported Format",
                "This tool does not support the old .xls format.\n\n"
                "Please open your file in Excel and save it as \".xlsx\" (Excel Workbook), then try again."
            )
            return

        # UI 更新为计算中
        self.lbl_result.configure(text="Processing...", text_color="yellow")
        self.update()

        # 3. 调用核心算法计算特征
        result, msg = calculate_features(file_path)

        # 错误处理
        if result is None:
            messagebox.showerror("Data Error", msg)
            self.lbl_result.configure(text="ERROR", text_color="gray")
            self.lbl_details.configure(text="")
            return

        slope, area = result

        # 4. 判定逻辑 (根据 UI 上的输入值打分)
        score = 0
        if slope > current_threshold_slope:
            score += 1
        if area < current_threshold_area:
            score += 1

        # 5. 更新判定结果到 UI
        if score == 2:
            self.lbl_result.configure(text="PASS", text_color="#34C759") # 苹果绿
        else:
            self.lbl_result.configure(text="FAIL", text_color="#FF3B30") # 苹果红

        # 显示具体数值对比
        filename_only = os.path.basename(file_path)
        detail_text = f"File: {filename_only}\n\n" \
                      f"Actual Slope: {slope:.2f}  (Req: > {current_threshold_slope})\n" \
                      f"Actual Area: {area:.4f}  (Req: < {current_threshold_area})"
        
        self.lbl_details.configure(text=detail_text)

# 启动应用
if __name__ == "__main__":
    app = DelamJudgeApp()
    app.mainloop()