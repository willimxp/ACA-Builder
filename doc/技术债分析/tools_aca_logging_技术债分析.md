# 技术债分析报告：tools/aca_logging.py

## 1. 文件概览
- **功能**：提供统一的日志配置和管理功能，封装了 Python 标准库 `logging`，支持文件轮转和控制台输出。
- **依赖**：`logging`, `pathlib`, `bpy`。

## 2. 代码质量分析
- **优点**：
    - **封装良好**：隐藏了 `logging` 的复杂配置，提供了简单的 API (`init_logger`, `get_logger`)。
    - **功能实用**：支持日志轮转 (`RotatingFileHandler`)，防止日志无限增长。
    - **环境感知**：能自动检测 Blender 用户目录并设置日志路径。
    - **动态调整**：支持运行时修改日志级别 (`update_log_level`)。
- **缺点**：
    - **全局状态**：依赖 `logging.getLogger("ACA")` 单例模式，虽然是标准做法，但在多插件共存时需确保名称唯一性（目前 "ACA" 较通用，有冲突风险）。
    - **硬编码**：默认日志文件名 `aca_log.txt` 和 logger name `ACA` 被硬编码在常量中。

## 3. 潜在风险
- **名称冲突**：`LOGGER_NAME = "ACA"` 过于简短，如果用户安装了其他也使用 "ACA" 为 Logger Name 的插件，配置会相互干扰。建议改为 `ACA_BUILDER`。
- **权限问题**：直接写入 `bpy.utils.resource_path('USER')` 下的 `scripts/addons` 目录。在某些系统配置下（如管理员安装的 Blender），该目录可能不可写。

## 4. 改进建议
1.  **重命名 Logger**：将 `LOGGER_NAME` 改为 `ACA_BUILDER` 或 `aca.builder` 以避免冲突。
2.  **错误处理**：在 `init_logger` 中增加对文件写入权限的检查，如果默认路径不可写，降级到临时目录 (`tempfile`)。
3.  **配置持久化**：目前日志级别是硬编码默认值的，建议读取插件的 `AddonPreferences` 来设置默认日志级别。
