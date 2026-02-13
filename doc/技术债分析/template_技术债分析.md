# 技术债分析报告：template.py

## 1. 文件概览
- **路径**: `/Volumes/XP.T9/Blender/ACA Builder/template.py`
- **功能**: 负责 XML 模板文件的解析、加载、保存，以及资产库的管理。
- **行数**: 约 1043 行

## 2. 主要技术债

### 2.1 手动 XML 解析 (High)
代码中大量使用了 `xml.etree.ElementTree` 进行手动解析和构建 (`__readNode`, `__loadTemplateSingle`, `__saveTemplate`)。
- **易错性**: 手动处理类型转换（str 转 float/int/bool）容易出错且代码冗余。
- **维护性**: 每次新增属性都需要修改解析逻辑。

**建议**: 
- 引入序列化库（如 `marshmallow`）或使用 dataclass 配合 XML 转换库。
- 或者定义一套通用的映射机制，自动根据 PropertyGroup 的注解进行序列化/反序列化。

### 2.2 硬编码路径 (Medium)
- `xmlFileName`, `blenderFileName` 定义在文件头部，缺乏灵活性。

**建议**: 移至配置模块。

### 2.3 全局状态管理 (Medium)
- `preview_collections` 是全局变量，用于管理缩略图资源。需要小心处理生命周期，确保在插件注销时正确释放，否则可能导致 Blender 内存泄漏或崩溃。

### 2.4 异常处理宽泛 (Low)
- 多处使用了 `except Exception` 且仅打印简单的错误信息。这可能掩盖真正的错误原因。

**建议**: 捕获具体的异常类型（如 `FileNotFoundError`, `ParseError`），并提供更详细的上下文日志。

## 3. 重构计划建议
1. **自动化序列化**: 重构 XML 读写逻辑，减少手动类型转换代码。
2. **异常增强**: 改进错误处理机制。
