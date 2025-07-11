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

# 修复：添加websocket导入错误处理
try:
    import websocket
except ImportError:
    print("Warning: websocket-client not installed. Install with: pip install websocket-client")
    websocket = None

def is_admin():
    # 检查是否具有管理员权限
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    # 以管理员权限重新运行程序
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
        
        sv_ttk.set_theme("light")  # 使用 light 主题
        
        self.window_list = None  # 先初始化为 None
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
        # 修复：连接到Chrome DevTools Protocol
        if not websocket:
            print("websocket-client not available")
            return None
            
        try:
            # 修复：先获取可用的目标列表
            response = requests.get(f"http://127.0.0.1:{port}/json/list")
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
        # 使用CDP注入指纹伪造
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