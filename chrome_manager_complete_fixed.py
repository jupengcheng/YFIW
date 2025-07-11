import tkinter as tk
from tkinter import ttk, messagebox
import os
import subprocess
import win32gui
import win32process
import win32con
import win32api
import win32com.client
import json
from typing import List, Dict, Optional
import math
import ctypes
from ctypes import wintypes
import threading
import time
import sys
import keyboard
import mouse
import webbrowser
import sv_ttk
import requests
import psutil

# 修复1：添加websocket导入错误处理
try:
    import websocket
except ImportError:
    print("Warning: websocket-client not installed. Install with: pip install websocket-client")
    websocket = None

def is_admin():
    """检查是否具有管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """以管理员权限重新运行程序"""
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

class ChromeManager:
    def __init__(self):
        if not is_admin():
            if messagebox.askyesno("权限不足", "需要管理员权限才能运行同步功能。\n是否以管理员身份重新启动程序？"):
                run_as_admin()
                sys.exit()
                
        self.root = tk.Tk()
        self.root.title("NoBiggie社区Chrome多窗口管理器 V1.0")
        
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "app.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"设置图标失败: {str(e)}")
        
        last_position = self.load_window_position()
        if last_position:
            self.root.geometry(last_position)
        
        sv_ttk.set_theme("light")
        
        self.window_list = None
        self.windows = []
        self.master_window = None
        self.shortcut_path = self.load_settings().get('shortcut_path', '')
        self.shell = win32com.client.Dispatch("WScript.Shell")
        self.select_all_var = tk.StringVar(value="全部选择")
        
        self.is_syncing = False
        self.sync_button = None
        self.mouse_hook_id = None
        self.keyboard_hook = None
        self.hook_thread = None
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.sync_windows = []
        
        self.chrome_drivers = {}
        self.debug_ports = {}
        self.base_debug_port = 9222
        self.window_configs = {}
        
        self.DWMWA_BORDER_COLOR = 34
        self.DWM_MAGIC_COLOR = 0x00FF0000
        
        self.popup_mappings = {}
        self.popup_monitor_thread = None
        
        self.mouse_threshold = 3
        self.last_mouse_position = (0, 0)
        self.last_move_time = 0
        self.move_interval = 0.016
        
        self.shortcut_hook = None
        self.current_shortcut = None
        
        # 从设置中加载快捷键
        settings = self.load_settings()
        if 'sync_shortcut' in settings:
            self.set_shortcut(settings['sync_shortcut'])
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 创建界面
        self.create_widgets()  
        self.create_styles()   
        
        self.root.update()
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        self.root.geometry(f"{current_width}x{current_height}")
        self.root.resizable(False, False)

    def connect_to_cdp(self, port):
        """修复2：连接到Chrome DevTools Protocol"""
        if not websocket:
            print("websocket-client not available")
            return None
            
        try:
            # 修复：先获取可用的目标列表
            response = requests.get(f"http://127.0.0.1:{port}/json/list", timeout=5)
            targets = response.json()
            if targets:
                # 使用第一个可用目标
                ws_debugger_url = targets[0]["webSocketDebuggerUrl"]
                ws = websocket.create_connection(ws_debugger_url)
                return ws
        except Exception as e:
            print(f"连接CDP失败: {str(e)}")
            return None

    def spoof_fingerprint(self, ws):
        """使用CDP注入指纹伪造"""
        if not ws:
            return
        try:
            # 伪造User-Agent
            ws.send(json.dumps({"id": 1, "method": "Network.setUserAgentOverride", "params": {"userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}}))
            # 伪造navigator.webdriver
            ws.send(json.dumps({"id": 2, "method": "Page.addScriptToEvaluateOnNewDocument", "params": {"source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"}}))
            # 伪造navigator.plugins
            ws.send(json.dumps({"id": 3, "method": "Page.addScriptToEvaluateOnNewDocument", "params": {"source": "Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });"}}))
            # 伪造navigator.languages
            ws.send(json.dumps({"id": 4, "method": "Page.addScriptToEvaluateOnNewDocument", "params": {"source": "Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });"}}))
            # 伪造WebGL
            ws.send(json.dumps({"id": 5, "method": "Page.addScriptToEvaluateOnNewDocument", "params": {"source": "const getParameter = WebGLRenderingContext.prototype.getParameter; WebGLRenderingContext.prototype.getParameter = function(parameter) { if (parameter === 37445) { return 'Intel Open Source Technology Center'; } if (parameter === 37446) { return 'Mesa DRI Intel(R) HD Graphics 630 (KBL GT2)'; } return getParameter(parameter); };"}}))
            # 伪造Canvas
            ws.send(json.dumps({"id": 6, "method": "Page.addScriptToEvaluateOnNewDocument", "params": {"source": "HTMLCanvasElement.prototype.toDataURL = function () { return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQYV2NgYGBgAAAABQABh6FO1AAAAAElFTkSuQmCC'; };"}}))
            print("指纹伪造成功")
        except Exception as e:
            print(f"指纹伪造失败: {str(e)}")

    def create_styles(self):
        style = ttk.Style()
        
        default_font = ('Microsoft YaHei UI', 9)
        
        style.configure('Small.TEntry',
            padding=(4, 0),
            font=default_font
        )
                
        style.configure('TButton', font=default_font)
        style.configure('TLabel', font=default_font)
        style.configure('TEntry', font=default_font)
        style.configure('Treeview', font=default_font)
        style.configure('Treeview.Heading', font=default_font)
        style.configure('TLabelframe.Label', font=default_font)
        style.configure('TNotebook.Tab', font=default_font)
        
        if self.window_list:
            self.window_list.tag_configure("master", 
                background="#0d6efd",
                foreground='white'
            )
        
        # 链接样式
        style.configure('Link.TLabel',
            foreground='#0d6efd',
            cursor='hand2',
            font=('Microsoft YaHei UI', 9, 'underline')
        )

    def create_widgets(self):
        """创建界面元素"""
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.X, padx=10, pady=5)
        
        upper_frame = ttk.Frame(main_frame)
        upper_frame.pack(fill=tk.X)
        
        arrange_frame = ttk.LabelFrame(upper_frame, text="自定义排列")
        arrange_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(3, 0))
        
        manage_frame = ttk.LabelFrame(upper_frame, text="窗口管理")
        manage_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        button_frame = ttk.Frame(manage_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="导入窗口", command=self.import_windows, style='Accent.TButton').pack(side=tk.LEFT, padx=2)
        select_all_label = ttk.Label(button_frame, textvariable=self.select_all_var, style='Link.TLabel')
        select_all_label.pack(side=tk.LEFT, padx=5)
        select_all_label.bind('<Button-1>', self.toggle_select_all)
        ttk.Button(button_frame, text="自动排列", command=self.auto_arrange_windows).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="关闭选中", command=self.close_selected_windows).pack(side=tk.LEFT, padx=2)
        
        self.sync_button = ttk.Button(
            button_frame, 
            text="▶ 开始同步",
            command=self.toggle_sync,
            style='Accent.TButton'
        )
        self.sync_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="快捷键",
            command=self.show_shortcut_dialog,
            style='Accent.TButton'
        ).pack(side=tk.LEFT, padx=5)
        
        # 在 button_frame 中添加屏幕选择下拉框
        screen_frame = ttk.Frame(button_frame)
        screen_frame.pack(side=tk.LEFT, padx=2)
        ttk.Label(screen_frame, text="屏幕:").pack(side=tk.LEFT)
        
        # 创建屏幕选择下拉框
        self.screen_var = tk.StringVar()
        self.screen_combo = ttk.Combobox(
            screen_frame, 
            textvariable=self.screen_var,
            width=8,
            state="readonly"
        )
        self.screen_combo.pack(side=tk.LEFT)
        
        # 获取并设置屏幕列表
        self.update_screen_list()
        
        list_frame = ttk.Frame(manage_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # 修复3：创建窗口列表
        self.window_list = ttk.Treeview(list_frame, 
            columns=("select", "number", "title", "master", "hwnd", "proxy", "fingerprint"),
            show="headings", 
            height=4
        )
        self.window_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 修复4：添加列标题
        self.window_list.heading("select", text="选择")
        self.window_list.heading("number", text="编号")
        self.window_list.heading("title", text="标题")
        self.window_list.heading("master", text="主控")
        self.window_list.heading("hwnd", text="")
        self.window_list.heading("proxy", text="代理信息")
        self.window_list.heading("fingerprint", text="指纹信息")
        
        self.window_list.column("select", width=40, anchor="center")
        self.window_list.column("number", width=40, anchor="center")
        self.window_list.column("title", width=200)
        self.window_list.column("master", width=40, anchor="center")
        self.window_list.column("hwnd", width=0, stretch=False)  # 隐藏hwnd列
        self.window_list.column("proxy", width=150, anchor="center")
        self.window_list.column("fingerprint", width=100, anchor="center")
        
        self.window_list.tag_configure("master", background="lightblue")
        
        self.window_list.bind('<Button-1>', self.on_click)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.window_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.window_list.configure(yscrollcommand=scrollbar.set)
        
        # 继续创建其他控件...
        self.create_remaining_widgets()

    def create_remaining_widgets(self):
        """创建其余界面元素"""
        # 获取main_frame引用
        main_frame = self.root.winfo_children()[0]
        upper_frame = main_frame.winfo_children()[0]
        arrange_frame = upper_frame.winfo_children()[0]
        
        params_frame = ttk.Frame(arrange_frame)
        params_frame.pack(fill=tk.X, padx=5, pady=2)
        
        left_frame = ttk.Frame(params_frame)
        left_frame.pack(side=tk.LEFT, padx=(0, 5))
        right_frame = ttk.Frame(params_frame)
        right_frame.pack(side=tk.LEFT)
        
        ttk.Label(left_frame, text="起始X坐标").pack(anchor=tk.W)
        self.start_x = ttk.Entry(left_frame, width=8, style='Small.TEntry')
        self.start_x.pack(fill=tk.X, pady=(0, 2))
        self.start_x.insert(0, "0")
        
        ttk.Label(left_frame, text="窗口宽度").pack(anchor=tk.W)
        self.window_width = ttk.Entry(left_frame, width=8, style='Small.TEntry')
        self.window_width.pack(fill=tk.X, pady=(0, 2))
        self.window_width.insert(0, "500")
        
        ttk.Label(left_frame, text="水平间距").pack(anchor=tk.W)
        self.h_spacing = ttk.Entry(left_frame, width=8, style='Small.TEntry')
        self.h_spacing.pack(fill=tk.X, pady=(0, 2))
        self.h_spacing.insert(0, "0")
        
        ttk.Label(right_frame, text="起始Y坐标").pack(anchor=tk.W)
        self.start_y = ttk.Entry(right_frame, width=8, style='Small.TEntry')
        self.start_y.pack(fill=tk.X, pady=(0, 2))
        self.start_y.insert(0, "0")
        
        ttk.Label(right_frame, text="窗口高度").pack(anchor=tk.W)
        self.window_height = ttk.Entry(right_frame, width=8, style='Small.TEntry')
        self.window_height.pack(fill=tk.X, pady=(0, 2))
        self.window_height.insert(0, "400")
        
        ttk.Label(right_frame, text="垂直间距").pack(anchor=tk.W)
        self.v_spacing = ttk.Entry(right_frame, width=8, style='Small.TEntry')
        self.v_spacing.pack(fill=tk.X, pady=(0, 2))
        self.v_spacing.insert(0, "0")
        
        bottom_frame = ttk.Frame(arrange_frame)
        bottom_frame.pack(fill=tk.X, padx=5, pady=2)
        
        row_frame = ttk.Frame(bottom_frame)
        row_frame.pack(side=tk.LEFT)
        ttk.Label(row_frame, text="每行窗口数").pack(anchor=tk.W)
        self.windows_per_row = ttk.Entry(row_frame, width=8, style='Small.TEntry')
        self.windows_per_row.pack(pady=(2, 0))
        self.windows_per_row.insert(0, "5")
        
        ttk.Button(bottom_frame, text="自定义排列", 
            command=self.custom_arrange_windows,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT, pady=(15, 0))
        
        # 创建底部标签框架
        bottom_frame = ttk.Frame(self.root)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(5, 0))
        
        self.tab_control = ttk.Notebook(bottom_frame)
        self.tab_control.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 创建各个选项卡
        self.create_tabs()
        
        # 创建底部信息
        self.create_footer()

    def create_tabs(self):
        """创建选项卡"""
        # 打开窗口选项卡
        open_window_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(open_window_tab, text="打开窗口")
        
        input_frame = ttk.Frame(open_window_tab)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(input_frame, text="快捷方式目录:").pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(input_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.path_entry.insert(0, self.shortcut_path)
        
        numbers_frame = ttk.Frame(input_frame)
        numbers_frame.pack(pady=5, padx=10, fill=tk.X)
        ttk.Label(numbers_frame, text="窗口编号:").pack(side=tk.LEFT)
        self.numbers_entry = ttk.Entry(numbers_frame)
        self.numbers_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        settings = self.load_settings()
        if 'last_window_numbers' in settings:
            self.numbers_entry.insert(0, settings['last_window_numbers'])
            
        self.numbers_entry.bind('<Return>', lambda e: self.open_windows())
        
        ttk.Button(
            numbers_frame,
            text="打开窗口",
            command=self.open_windows
        ).pack(side=tk.LEFT)
        
        # 批量打开网页选项卡
        url_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(url_tab, text="批量打开网页")
        
        url_frame = ttk.Frame(url_tab)
        url_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(url_frame, text="网址:").pack(side=tk.LEFT)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.url_entry.insert(0, "www.google.com")
        
        self.url_entry.bind('<Return>', lambda e: self.batch_open_urls())
        
        ttk.Button(url_frame, text="批量打开", command=self.batch_open_urls).pack(side=tk.LEFT, padx=5)
        
        # 窗口配置选项卡
        config_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(config_tab, text="窗口配置")

        config_frame = ttk.Frame(config_tab)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 代理设置
        proxy_frame = ttk.LabelFrame(config_frame, text="代理设置")
        proxy_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(proxy_frame, text="代理地址: ").grid(row=0, column=0, sticky="w", padx=5, pady=2)
        self.proxy_entry = ttk.Entry(proxy_frame, width=40)
        self.proxy_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # 指纹设置
        fingerprint_frame = ttk.LabelFrame(config_frame, text="指纹设置")
        fingerprint_frame.pack(fill=tk.X, padx=5, pady=5)

        self.enable_fingerprint_var = tk.BooleanVar()
        ttk.Checkbutton(fingerprint_frame, text="启用指纹伪造", variable=self.enable_fingerprint_var).pack(anchor="w", padx=5, pady=2)

        # 应用配置按钮
        ttk.Button(config_frame, text="应用到选中窗口", command=self.apply_window_config).pack(pady=10)
        
        # 替换图标选项卡
        icon_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(icon_tab, text="替换图标")
        
        icon_frame = ttk.Frame(icon_tab)
        icon_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(icon_frame, text="图标目录:").pack(side=tk.LEFT)
        self.icon_path_entry = ttk.Entry(icon_frame)
        self.icon_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(icon_frame, text="窗口编号:").pack(side=tk.LEFT, padx=(10, 0))
        self.icon_window_numbers = ttk.Entry(icon_frame, width=15)
        self.icon_window_numbers.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Label(icon_frame, text="示例: 1-5,7,9-12").pack(side=tk.LEFT)
        ttk.Button(icon_frame, text="替换图标", command=self.set_taskbar_icons).pack(side=tk.LEFT, padx=5)

    def create_footer(self):
        """创建底部信息"""
        footer_frame = ttk.Frame(self.root)
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        author_frame = ttk.Frame(footer_frame)
        author_frame.pack(side=tk.RIGHT)

        ttk.Label(author_frame, text="Compiled by Devilflasher").pack(side=tk.LEFT)

        ttk.Label(author_frame, text="  ").pack(side=tk.LEFT)

        twitter_label = ttk.Label(
            author_frame, 
            text="Twitter",
            cursor="hand2",
            font=("Arial", 9)
        )
        twitter_label.pack(side=tk.LEFT)
        twitter_label.bind("<Button-1>", lambda e: webbrowser.open("https://x.com/DevilflasherX"))

        ttk.Label(author_frame, text="  ").pack(side=tk.LEFT)

        telegram_label = ttk.Label(
            author_frame, 
            text="Telegram",
            cursor="hand2",
            font=("Arial", 9)
        )
        telegram_label.pack(side=tk.LEFT)
        telegram_label.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/devilflasher0"))

    def parse_window_numbers(self, numbers_str: str) -> List[int]:
        """解析窗口编号字符串"""
        if not numbers_str.strip():
            return list(range(1, 49))
            
        result = []
        parts = numbers_str.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                result.extend(range(start, end + 1))
            else:
                result.append(int(part))
        return sorted(list(set(result)))

    def open_windows(self):
        """修复5：打开Chrome窗口"""
        path = self.path_entry.get()
        numbers = self.numbers_entry.get()
        
        if not path or not numbers:
            messagebox.showwarning("警告", "请输入快捷方式路径和窗口编号！")
            return
            
        try:
            window_numbers = self.parse_window_numbers(numbers)
            
            for num in window_numbers:
                user_data_dir = os.path.join(path, f"Data\\{num}")
                if not os.path.exists(user_data_dir):
                    os.makedirs(user_data_dir)

                chrome_exe_path = self.find_chrome_executable()
                if not chrome_exe_path:
                    messagebox.showerror("错误", "未找到Chrome浏览器可执行文件！")
                    return

                command = [chrome_exe_path, f"--user-data-dir={user_data_dir}"]
                command.append(f"--remote-debugging-port={self.base_debug_port + num}")

                # 加载窗口配置
                window_config = {}
                config_file = os.path.join(user_data_dir, "window_config.json")
                if os.path.exists(config_file):
                    try:
                        with open(config_file, "r", encoding="utf-8") as f:
                            window_config = json.load(f)
                    except Exception as e:
                        print(f"加载窗口 {num} 配置失败: {e}")

                # 修复：添加代理参数
                proxy_address = window_config.get("proxy", "")
                if proxy_address:
                    if "@" in proxy_address:
                        auth_part, server_part = proxy_address.split("@", 1)
                        command.append(f"--proxy-server={server_part}")
                    else:
                        command.append(f"--proxy-server={proxy_address}")

                subprocess.Popen(command)
                time.sleep(1)
                
                # 尝试连接CDP并进行指纹伪造
                enable_fingerprint = window_config.get("fingerprint", False)
                if enable_fingerprint and websocket:
                    try:
                        debug_port = self.base_debug_port + num
                        ws = self.connect_to_cdp(debug_port)
                        if ws:
                            self.spoof_fingerprint(ws)
                            ws.close()
                    except Exception as cdp_e:
                        print(f"CDP连接或指纹伪造失败: {cdp_e}")

                time.sleep(0.5)
            
            self.save_settings()
            
        except Exception as e:
            messagebox.showerror("错误", f"打开窗口失败: {str(e)}")

    def find_chrome_executable(self):
        """查找Chrome可执行文件路径"""
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google\\Chrome\\Application\\chrome.exe")
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def update_screen_list(self):
        """修复6：更新屏幕列表"""
        try:
            screens = []
            
            # 简化的屏幕检测
            try:
                screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                
                virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
                virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
                virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
                virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
                
                # 添加主屏幕
                screens.append({
                    'name': "屏幕 1 (主屏幕)",
                    'rect': (0, 0, screen_width, screen_height),
                    'work_rect': (0, 0, screen_width, screen_height - 40),
                    'monitor': None
                })
                
                # 如果有多个屏幕，添加第二个屏幕
                if virtual_width > screen_width:
                    screens.append({
                        'name': "屏幕 2",
                        'rect': (screen_width, 0, virtual_width, screen_height),
                        'work_rect': (screen_width, 0, virtual_width, screen_height - 40),
                        'monitor': None
                    })
                
            except Exception as e:
                print(f"获取屏幕信息失败: {str(e)}")
                screens = [{
                    'name': "主屏幕",
                    'rect': (0, 0, 1920, 1080),
                    'work_rect': (0, 0, 1920, 1040),
                    'monitor': None
                }]
            
            self.screen_combo['values'] = [screen['name'] for screen in screens]
            self.screens = screens
            if screens:
                self.screen_combo.current(0)
            
        except Exception as e:
            print(f"更新屏幕列表失败: {str(e)}")

    def load_settings(self) -> dict:
        """加载设置"""
        try:
            with open('settings.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}

    def save_settings(self):
        """保存设置"""
        try:
            settings = {
                'shortcut_path': self.path_entry.get() if hasattr(self, 'path_entry') else '',
                'window_position': self.root.geometry(),
                'last_window_numbers': self.numbers_entry.get() if hasattr(self, 'numbers_entry') else '',
                'arrange_params': {
                    'start_x': self.start_x.get() if hasattr(self, 'start_x') else '0',
                    'start_y': self.start_y.get() if hasattr(self, 'start_y') else '0',
                    'window_width': self.window_width.get() if hasattr(self, 'window_width') else '500',
                    'window_height': self.window_height.get() if hasattr(self, 'window_height') else '400',
                    'h_spacing': self.h_spacing.get() if hasattr(self, 'h_spacing') else '0',
                    'v_spacing': self.v_spacing.get() if hasattr(self, 'v_spacing') else '0',
                    'windows_per_row': self.windows_per_row.get() if hasattr(self, 'windows_per_row') else '5'
                },
                'sync_shortcut': self.current_shortcut
            }
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存设置失败: {str(e)}")

    def load_window_position(self):
        """加载窗口位置"""
        try:
            settings = self.load_settings()
            return settings.get('window_position')
        except:
            return None

    def run(self):
        """运行程序"""
        self.root.mainloop()

    def on_closing(self):
        """窗口关闭事件"""
        try:
            self.stop_sync()
            if self.shortcut_hook:
                keyboard.clear_all_hotkeys()
                keyboard.unhook_all()
                self.shortcut_hook = None
            self.save_settings()
        except Exception as e:
            print(f"程序关闭时出错: {str(e)}")
        finally:
            self.root.destroy()

    # 这里继续添加其他方法...