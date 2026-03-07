# ACA Builder 多语言支持规格说明书

## 目标
为 ACA Builder 插件实现多语言支持 (i18n)，允许用户在英文和简体中文之间切换。系统支持上下文感知的翻译、全局匹配以及特定资源的双向翻译。

## 架构

### 模块结构
- **包路径**: `locale/`
- `locale/i18n.py`: 核心逻辑模块。负责加载字典、注册翻译、语言设置缓存、正向/反向查找逻辑以及动态切换时的 UI 刷新。
- `locale/zh_HANS.py`: 字典数据模块。包含所有翻译条目，采用 `(context, msg_id): translated_text` 的结构。

### 集成方式
- **全局函数**: 暴露 `_(msg_id, context="*")` 作为翻译入口。
- **静态字段**: 对于 `bpy.props` 的 `name` 和 `description` 属性，通过 `_()` 包装以支持动态刷新。
- **EnumProperty**: 枚举项的显示文本通过 `_()` 包装，内部键（Identifier）保持不变以确保逻辑兼容。
- **资产资源**: 对于来自 XML（如 `template.xml`, `assetsIndex.xml`）的中文键值，通过特定上下文（`template`, `assetsIndex`）实现 `en_US` 模式下的反向翻译。

## 功能特性

### 1. 字典管理与上下文
- **上下文规范**:
    - `"*"`: 通用上下文。
    - `"template"`: 对应 `template.xml` 中的模板名称。
    - `"assetsIndex"`: 对应 `assetsIndex.xml` 中的资产样式（如斗栱样式）。
- **映射规则**: 源代码通常使用英文作为 `msg_id`。对于 XML 资源，内部键为中文，翻译字典中则以英文作为 `msg_id`，中文作为翻译值，以实现双向映射。

### 2. 翻译函数 `_()` 查找逻辑
- **签名**: `_(msg_id, context="*")`
- **分发行为**:
    1. **获取语言偏好**: 检查插件偏好设置中的 `language`。
    2. **en_US (英文)**: 
        - 若上下文为 `"template"` 或 `"assetsIndex"`，执行**反向查找**（通过中文翻译值找英文 `msg_id`），以便在英文界面显示英文名称。
        - 其他情况直接返回原始 `msg_id`。
    3. **zh_HANS (简体中文)**: 
        - 优先在手动字典中执行**正向查找**。
        - 若未命中，回退到 `bpy.app.translations.pgettext`。
    4. **FOLLOW (跟随系统)**: 
        - 委托给 `bpy.app.translations.pgettext(msg_id, context)`。

### 3. 动态语言切换 (`update_language`)
- **触发机制**: 偏好设置中 `language` 属性的 `update` 回调。
- **处理流程**:
    1. 设置全局语言缓存。
    2. 注销当前插件的所有类和自定义属性（`data.delprop()`）。
    3. 依次执行 `importlib.reload()`：重新加载 `data`, `panel`, `operators` 模块，从而触发静态字段中的 `_()` 重新计算。
    4. 重新发现并注册所有类。
    5. 重新初始化自定义属性（`data.initprop()`）。
    6. 强制刷新所有区域的 UI 绘制。

### 4. 启动性能优化
- **位置**: `__init__.py` 的 `register()`。
- **策略**: 仅当用户显式将语言设置为 `zh_HANS` 时，才在启动期间触发一次 `update_language` 流程，确保界面静态文本正确汉化。对于默认情况，避免不必要的模块重载。

## 字典结构示例

```python
# locale/zh_HANS.py
data = {
    "zh_HANS": {
        # 通用条目
        ("*", "Paint Style"): "彩画风格",
        
        # 资源条目 (支持反向翻译)
        ("template", "3-Bay Hip Roof"): "三间庑殿",
        ("assetsIndex", "Doukou Single Ang"): "斗口单昂",
    }
}
```

## 相关文件
1.  [i18n.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/locale/i18n.py): 核心查找与刷新逻辑。
2.  [zh_HANS.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/locale/zh_HANS.py): 翻译字典。
3.  [data.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/data.py): 属性定义的国际化应用。
4.  [operators.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/operators.py): 偏好设置与 UI 逻辑。
5.  [template.py](file:///Volumes/XP.T9/Blender/ACA%20Builder/template.py): 动态资源（如斗栱列表、模板列表）的翻译。
