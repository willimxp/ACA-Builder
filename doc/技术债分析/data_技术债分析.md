# 技术债分析报告：data.py

## 1. 文件概览
- **路径**: `/Volumes/XP.T9/Blender/ACA Builder/data.py`
- **功能**: 定义 Blender 属性组 (PropertyGroup)，即数据模型。
- **行数**: 约 1252 行

## 2. 主要技术债

### 2.1 UI 与数据强耦合 (High)
`ACA_data_obj` 等类中，`bpy.props` 的定义包含了大量的 UI 相关参数：
- `name`: 属性名称（显示在面板上）
- `description`: 工具提示
- `min`, `max`, `soft_min`, `soft_max`: UI 限制
- `update`: 回调函数

这使得数据层直接决定了 UI 的表现和行为，违反了 MVC 分层原则。

**建议**: 虽然 Blender API 鼓励这种模式，但对于复杂项目，建议尽量简化 Property 定义，复杂的 UI 逻辑（如动态范围）在 Panel 的 `draw` 方法中处理。

### 2.2 巨大的数据类 (High)
`ACA_data_obj` 类包含了数百个属性，涵盖了台基、柱网、斗栱、屋顶、瓦作等所有构件的参数。这违反了单一职责原则，使得该类难以维护。

**建议**: 
- 使用组合模式 (`PointerProperty`) 将属性分组。例如：
    - `ACA_data_obj.roof_props` (指向 `ACA_data_roof`)
    - `ACA_data_obj.dougong_props` (指向 `ACA_data_dougong`)
- 这样可以将属性分散到多个小的 PropertyGroup 类中。

### 2.3 类型注解缺失 (Medium)
- 大量使用了 `# type: ignore`，这表明类型检查器（如 MyPy 或 VSCode Pylance）无法正确推断 Blender 的 Property 类型。这会降低代码补全的准确性，并掩盖潜在的类型错误。

**建议**: 使用 `typing` 模块或伪造的类型存根（Type Stubs）来辅助类型检查，减少对 ignore 的依赖。

### 2.4 硬编码的枚举值 (Low)
- 枚举属性（如 `roof_style`）直接在代码中定义了列表。

**建议**: 将枚举定义提取到 `const.py` 或专门的 `enums.py` 中。

## 3. 重构计划建议
1. **数据结构拆分**: 将 `ACA_data_obj` 拆分为多个子属性组。
2. **枚举提取**: 将所有 EnumProperty 的 items 提取到常量文件。
