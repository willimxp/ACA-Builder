# ACA Builder 日志模块使用说明

## 📋 概述

`aca_logging` 模块为 ACA Builder 插件提供统一的日志记录功能，支持控制台和文件双输出，以及日志轮转功能。该模块已从 `__init__.py` 中独立出来，支持可配置的日志级别和路径。

## ✨ 主要优势

1. **可配置日志级别**：支持 DEBUG/INFO/WARNING/ERROR 四级日志，默认 INFO
2. **日志轮转功能**：自动归档旧日志，防止日志文件过大（默认 5MB，保留 3 个备份）
3. **双输出通道**：同时输出到控制台和文件
4. **运行时调整**：支持动态修改日志级别
5. **解耦设计**：独立模块，便于维护和复用

## 🚀 使用方法

### 在 `__init__.py` 中初始化

```python
from .tools import aca_logging

def register():
    # 从偏好设置读取日志配置
    preferences = bpy.context.preferences
    addon_main_name = __name__.split('.')[0]
    addon_prefs = preferences.addons[addon_main_name].preferences
    
    # 初始化日志记录器
    log_level = aca_logging.get_log_level_from_string(addon_prefs.log_level)
    logger = aca_logging.init_logger(
        log_level=log_level,
        use_rotating=addon_prefs.use_log_rotation
    )
    
    # 记录系统信息
    aca_logging.log_system_info(logger)
```

### 在其他模块中使用日志

```python
from .tools.aca_logging import get_logger

logger = get_logger()
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 在插件注销时清理

```python
from .tools import aca_logging

def unregister():
    # 移除日志记录器
    aca_logging.remove_logger()
```

## ⚙️ 用户配置

日志配置存储在 Blender 插件偏好设置中：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| 日志级别 | 枚举 | INFO | DEBUG/INFO/WARNING/ERROR |
| 启用日志轮转 | 布尔 | True | 自动归档旧日志文件 |

**配置路径**：编辑 > 偏好设置 > 插件 > ACA Builder > 日志设置

## 📁 日志文件

### 默认位置

```
{Blender用户目录}/scripts/addons/ACA Builder/aca_log.txt
```

### 轮转文件

当日志轮转启用时，会生成以下备份文件：

```
aca_log.txt       # 当前日志（最大 5MB）
aca_log.txt.1     # 最近备份
aca_log.txt.2     # 次近备份
aca_log.txt.3     # 最旧备份
```

当 `aca_log.txt` 达到 5MB 时，自动轮转：
- `.2` → `.3`
- `.1` → `.2`
- `aca_log.txt` → `.1`
- 新建空的 `aca_log.txt`

### 日志格式

```
YY/MM/DD HH:MM:SS [LEVEL] : message
```

**示例**：

```
26/02/10 14:30:25 [INFO] : ACA Builder 日志系统启动
26/02/10 14:30:25 [INFO] : 操作系统: Darwin 26.2.0
26/02/10 14:30:25 [INFO] : Python 版本: 3.11.0
26/02/10 14:30:25 [INFO] : Blender 版本: 4.2.0
26/02/10 14:30:25 [INFO] : 成功注册 69 个类
26/02/10 14:30:25 [DEBUG] : 类注册详情：
```

## 🔧 API 参考

### `init_logger(log_level=None, log_path=None, log_filename=None, use_rotating=True, max_bytes=5242880, backup_count=3)`

初始化 ACA 日志记录器。

**参数**：
- `log_level` (int): 日志级别，默认为 `logging.INFO`
- `log_path` (pathlib.Path): 日志文件目录，默认为 Blender 用户目录
- `log_filename` (str): 日志文件名，默认为 `aca_log.txt`
- `use_rotating` (bool): 是否启用日志轮转，默认为 `True`
- `max_bytes` (int): 单个日志文件最大字节数，默认为 5MB
- `backup_count` (int): 保留的备份文件数量，默认为 3

**返回**：
- `logging.Logger`: 配置好的日志记录器

**示例**：
```python
# 基本用法
logger = aca_logging.init_logger()

# 自定义配置
logger = aca_logging.init_logger(
    log_level=logging.DEBUG,
    use_rotating=False  # 禁用轮转，每次清空日志
)
```

---

### `get_logger()`

获取 ACA 日志记录器实例。

**返回**：
- `logging.Logger`: ACA 日志记录器实例

**示例**：
```python
from .tools.aca_logging import get_logger

logger = get_logger()
logger.info("获取记录器成功")
```

---

### `remove_logger()`

移除 ACA 日志记录器的所有处理器。

**说明**：
在插件注销时调用，清理资源。

**示例**：
```python
def unregister():
    aca_logging.remove_logger()
```

---

### `update_log_level(log_level)`

运行时动态更新日志级别。

**参数**：
- `log_level` (int): 新的日志级别（如 `logging.DEBUG`）

**示例**：
```python
# 切换到 DEBUG 级别
aca_logging.update_log_level(logging.DEBUG)

# 切换回 INFO 级别
aca_logging.update_log_level(logging.INFO)
```

---

### `log_system_info(logger=None)`

记录系统和环境信息到日志。

**参数**：
- `logger` (logging.Logger): 日志记录器，默认使用 ACA 日志记录器

**记录内容**：
- ACA Builder 日志系统启动标记
- 操作系统信息
- Python 版本
- Blender 版本

**示例**：
```python
aca_logging.log_system_info()
```

**输出示例**：
```
==================================================
ACA Builder 日志系统启动
操作系统: Darwin 26.2.0
Python 版本: 3.11.0
Blender 版本: 4.2.0
==================================================
```

---

### `get_log_level_from_string(level_name)`

将字符串转换为 logging 级别常量。

**参数**：
- `level_name` (str): 日志级别名称 ('DEBUG', 'INFO', 'WARNING', 'ERROR')

**返回**：
- `int`: logging 模块定义的日志级别

**示例**：
```python
level = aca_logging.get_log_level_from_string('DEBUG')  # 返回 10
level = aca_logging.get_log_level_from_string('INFO')   # 返回 20
```

---

### `get_default_log_path()`

获取默认日志文件路径。

**返回**：
- `pathlib.Path`: 默认日志目录路径

**示例**：
```python
log_path = aca_logging.get_default_log_path()
print(log_path)  # /Users/xxx/Library/Application Support/Blender/4.2/scripts/addons/ACA Builder
```

---

### 常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `LOGGER_NAME` | "ACA" | 日志记录器名称 |
| `DEFAULT_LOG_LEVEL` | `logging.INFO` | 默认日志级别 |
| `DEFAULT_LOG_FILENAME` | "aca_log.txt" | 默认日志文件名 |
| `DEFAULT_MAX_BYTES` | 5242880 (5MB) | 默认单个日志文件最大字节数 |
| `DEFAULT_BACKUP_COUNT` | 3 | 默认保留的备份文件数量 |
| `LOG_LEVELS` | 列表 | 日志级别映射，用于 UI 显示 |

## 🐛 故障排除

### 问题1：日志文件没有生成

**原因**：日志目录不存在或权限不足

**解决方法**：
```python
# 手动检查路径
log_path = aca_logging.get_default_log_path()
print(f"日志路径: {log_path}")
print(f"路径存在: {log_path.exists()}")
print(f"路径可写: {os.access(log_path.parent, os.W_OK)}")
```

### 问题2：日志级别设置不生效

**原因**：可能使用了旧的日志记录器实例

**解决方法**：
```python
# 确保使用 get_logger() 获取记录器
logger = aca_logging.get_logger()
# 而不是
logger = logging.getLogger("ACA")  # 虽然效果相同，但不推荐
```

### 问题3：日志轮转导致磁盘空间不足

**原因**：备份文件过多或单个文件过大

**解决方法**：
```python
# 减少备份数量
logger = aca_logging.init_logger(
    backup_count=1,  # 只保留 1 个备份
    max_bytes=1024*1024  # 1MB
)
```

### 问题4：中文乱码

**原因**：日志文件编码问题

**解决方法**：
模块已默认使用 UTF-8 编码，确保终端也使用 UTF-8：
```python
# Windows 系统
import os
os.system("chcp 65001")  # 设置 UTF-8 编码
```

## 📁 文件位置

- **主模块**：`tools/aca_logging.py`
- **使用说明**：`doc/aca_logging使用说明.md`
- **需求文档**：`doc/日志模块需求文档.md`

## 📄 版本历史

| 版本 | 日期 | 修改内容 |
|------|------|----------|
| 1.0 | 260210 | 初始版本，从 `__init__.py` 独立 |
| 1.1 | 260210 | 移动到 `tools/` 目录 |
