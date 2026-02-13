# 技术债分析报告：tools/auto_register.py

## 1. 文件概览
- **功能**：自动发现、排序并注册 Blender 的各类组件（Operator, Panel, PropertyGroup 等）。
- **核心逻辑**：使用 `inspect` 模块遍历模块成员，识别 Blender 类，并根据依赖关系（特别是 `PropertyGroup` 的嵌套关系）进行排序。

## 2. 代码质量分析
- **优点**：
    - **自动化**：极大地减少了 `__init__.py` 中手动维护注册列表的工作量，降低了漏注册或顺序错误的风险。
    - **智能排序**：实现了复杂的依赖排序逻辑，特别是针对 `PropertyGroup` 的定义顺序和 `Panel` 的父子关系。
    - **验证机制**：提供了 `validate_classes` 函数，能在注册前检查必要的属性（如 `bl_idname`）。
- **缺点**：
    - **实现脆弱**：`_sort_by_source_order` 依赖 `inspect.getsourcelines` 获取行号来排序。这在某些打包环境（如编译为 `.pyc` 或加密脚本）中可能失效。
    - **反射开销**：大量使用 `inspect` 和反射，在插件启动时会有一定的性能开销（虽然对于目前的规模可忽略）。
    - **隐式依赖**：`_is_blender_class` 依赖命名规范（如 `ACA_PT_`）或基类名称字符串匹配，如果重构导致类名变化，注册可能失效。

## 3. 潜在风险
- **运行环境兼容性**：依赖源代码文件存在 (`inspect.getsourcefile`)。如果插件被发布为 zip 且 Python 解释器无法访问源码文件（极其罕见但在某些嵌入式 Python 环境可能发生），排序逻辑会退化。
- **基类识别限制**：`_has_base_class` 通过字符串匹配基类名称，如果使用了别名导入（`from bpy.types import Operator as Op`），可能无法正确识别。

## 4. 改进建议
1.  **增强类型检查**：尽量使用 `issubclass` 配合 `bpy.types` 中的实际类进行检查，而不是仅依赖字符串匹配基类名称。
2.  **鲁棒性提升**：为 `_sort_by_source_order` 提供回退机制，如果无法获取源代码行号，则按字母顺序或显式的 `_order` 属性排序。
3.  **缓存机制**：如果启动速度成为瓶颈，可以将计算好的注册顺序缓存到文件中。
