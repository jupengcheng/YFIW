# Chrome Manager Code Fixes

## 主要错误修复

### 1. 字符串转义错误
**位置**: 创建 Treeview 时的 style 参数
**错误**: `style=\'Accent.Treeview\'`
**修复**: `style='Accent.Treeview'`

### 2. WebSocket 导入错误
**添加错误处理**:
```python
try:
    import websocket
except ImportError:
    print("Warning: websocket-client not installed")
    websocket = None
```

### 3. CDP 连接方法错误
**修复 connect_to_cdp 方法**:
- 先访问 `/json/list` 获取目标
- 再使用 `webSocketDebuggerUrl` 连接

### 4. 代理配置错误
**修复代理解析逻辑**:
```python
if "@" in proxy_address:
    auth_part, server_part = proxy_address.split("@", 1)
    command.append(f"--proxy-server={server_part}")
```

### 5. 鼠标滚轮事件错误
**修复重复的变量赋值**

### 6. 屏幕检测错误
**简化屏幕检测逻辑**，避免复杂的回调函数

### 7. Treeview 列标题
**添加缺失的列标题设置**

## 依赖包安装
```bash
pip install pywin32 sv-ttk keyboard mouse psutil requests websocket-client
```
