# 技术债分析报告：__init__.py

## 1. 文件概览
- **路径**: `/Volumes/XP.T9/Blender/ACA Builder/__init__.py`
- **功能**: 插件入口，负责类注册、属性初始化、日志配置及生命周期管理。
- **行数**: 约 105 行

## 2. 主要技术债

### 2.1 职责过重 (High)
`register` 函数不仅仅负责注册类，还承担了以下非核心职责：
- **日志系统初始化**: 读取偏好设置并配置日志。
- **环境修补**: Windows 平台下的 `chcp 65001` 编码修复。
- **全局配置修改**: 修改 `bpy.context.preferences.view.use_translate_new_dataname`。

**建议**: 将环境检测、配置加载、日志初始化等逻辑提取到专门的 `config.py` 或 `lifecycle.py` 模块中，`__init__.py` 只保留最纯粹的注册调用。

### 2.2 全局变量依赖 (Medium)
- `classes` 变量依赖于 `auto_register` 模块的立即执行结果。这使得模块在导入时就会执行代码（副作用），不利于单元测试和模块隔离。

**建议**: 将类发现逻辑封装在函数中，在 `register` 时动态调用，或者保持现状但明确注释副作用。

### 2.3 偏好设置获取重复 (Low)
- 在 `register` 函数中，多次通过 `bpy.context.preferences.addons[addon_main_name].preferences` 获取偏好设置。

**建议**: 封装一个 `get_preferences()` 辅助函数（如果在 `utils.py` 中已有，则应复用）。

### 2.4 注释清理 (Low)
- 存在一些开发过程中的注释（如 `260210` 日志迁移说明），在代码稳定后应考虑归档或精简，保留核心设计意图即可。

## 3. 重构计划建议
1. 创建 `core/lifecycle.py`，移动环境检查和配置初始化代码。
2. 保持 `__init__.py` 极简，仅作为 Blender 插件的识别入口。
