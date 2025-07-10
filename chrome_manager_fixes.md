# Chrome Manager Code Fixes

## Main Errors Found and Fixes

### 1. Invalid Escape Sequence in String Literal
**Error Location:** Line with `style=\'Accent.Treeview\'`
**Problem:** Invalid escape sequence `\'` in string literal
**Fix:** Change to `style='Accent.Treeview'`

### 2. Missing Import for websocket-client
**Problem:** Code imports `websocket` but doesn't handle if the module isn't installed
**Fix:** Add proper import handling:
```python
try:
    import websocket
except ImportError:
    print("Warning: websocket-client not installed. Install with: pip install websocket-client")
    websocket = None
```

### 3. Proxy Configuration Error
**Problem:** Proxy parsing logic has issues with authentication
**Fix:** In `open_windows()` method, fix proxy parsing:
```python
# Fix proxy parsing
if proxy_address:
    if "@" in proxy_address:
        auth_part, server_part = proxy_address.split("@", 1)
        command.append(f"--proxy-server={server_part}")
        # Handle authentication separately if needed
    else:
        command.append(f"--proxy-server={proxy_address}")
```

### 4. CDP Connection Error Handling
**Problem:** `connect_to_cdp()` method has incorrect endpoint
**Fix:** Fix the CDP connection:
```python
def connect_to_cdp(self, port):
    try:
        # Get list of available targets first
        response = requests.get(f"http://127.0.0.1:{port}/json/list")
        targets = response.json()
        if targets:
            # Use the first available target
            ws_debugger_url = targets[0]["webSocketDebuggerUrl"]
            ws = websocket.create_connection(ws_debugger_url)
            return ws
    except Exception as e:
        print(f"连接CDP失败: {str(e)}")
        return None
```

### 5. Mouse Event Handling Error
**Problem:** Mouse wheel handling has syntax errors
**Fix:** Fix the mouse wheel event handling:
```python
# Fix mouse wheel handling
if isinstance(event, mouse.WheelEvent):
    try:
        wheel_delta = int(event.delta)
        if keyboard.is_pressed('ctrl'):
            # Zoom in/out
            if wheel_delta > 0:
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, 0)
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, 0xBB, 0)  # VK_OEM_PLUS
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, 0xBB, 0)
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, 0)
            else:
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, win32con.VK_CONTROL, 0)
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, 0xBD, 0)  # VK_OEM_MINUS
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, 0xBD, 0)
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, win32con.VK_CONTROL, 0)
        else:
            # Scroll up/down
            vk_code = win32con.VK_UP if wheel_delta > 0 else win32con.VK_DOWN
            repeat_count = min(abs(wheel_delta) * 3, 6)
            for _ in range(repeat_count):
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYDOWN, vk_code, 0)
                win32gui.PostMessage(target_hwnd, win32con.WM_KEYUP, vk_code, 0)
    except Exception as e:
        print(f"处理滚轮事件失败: {str(e)}")
```

### 6. EnumDisplayMonitors Callback Error
**Problem:** The callback function for `EnumDisplayMonitors` might not work properly
**Fix:** Simplify the screen detection:
```python
def update_screen_list(self):
    """更新屏幕列表"""
    try:
        screens = []
        
        # 简化的屏幕检测
        try:
            # 获取主屏幕信息
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # 获取虚拟屏幕信息
            virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            
            # 添加主屏幕
            screens.append({
                'name': "屏幕 1 (主屏幕)",
                'rect': (0, 0, screen_width, screen_height),
                'work_rect': (0, 0, screen_width, screen_height - 40),  # 减去任务栏高度
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
            # 使用默认屏幕
            screens = [{
                'name': "主屏幕",
                'rect': (0, 0, 1920, 1080),
                'work_rect': (0, 0, 1920, 1040),
                'monitor': None
            }]
        
        # 更新下拉框选项
        self.screen_combo['values'] = [screen['name'] for screen in screens]
        self.screens = screens
        self.screen_combo.current(0)
        
    except Exception as e:
        print(f"更新屏幕列表失败: {str(e)}")
```

## Required Dependencies

Make sure to install these packages:
```bash
pip install pywin32 sv-ttk keyboard mouse psutil requests websocket-client
```

## Summary of Changes

1. Fixed string escape sequence error
2. Added proper error handling for missing dependencies
3. Fixed proxy configuration parsing
4. Fixed CDP connection endpoint
5. Fixed mouse wheel event handling syntax
6. Simplified screen detection to avoid callback issues
7. Added proper exception handling throughout

These fixes should resolve the main syntax and runtime errors in the Chrome manager code.