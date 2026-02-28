# ACA Builder 多语言支持规格说明书

## 目标
为 ACA Builder 插件实现多语言支持 (i18n)，允许用户在英文和简体中文之间切换（未来可扩展其他语言）。系统应支持上下文感知的翻译和全局匹配。

## 架构

### 模块结构
- 创建一个新的包 `locale/` 来存放翻译逻辑和数据。
- `locale/i18n.py`: 负责注册、加载字典和翻译查找的核心逻辑。
- `locale/zh_HANS.py`: 包含英文到中文映射关系的字典文件。

### 集成
- 修改 `__init__.py` 以在启动时注册翻译模块。
- 修改 `operators.py`（具体为 `ACA_OT_Preferences`）以添加语言选择设置。
- 暴露一个 `T(msg_id, context=None)` 函数，供开发者用于包装需要翻译的字符串。

## 功能特性

### 1. 字典管理
- **文件**: `locale/zh_HANS.py`
- **格式**: Python 字典，键为 `(context, msg_id)` 或 `("*", msg_id)`，值为翻译后的字符串。
- **扩展性**: 支持未来添加更多语言的字典文件。

### 2. 注册
- **文件**: `locale/i18n.py`
- **逻辑**: 
    - 从 `zh_HANS.py` 加载字典。
    - 使用 `bpy.app.translations.register(__name__, translations_dict)` 进行注册。
    - 处理注销逻辑。

### 3. 翻译函数 `T()`
- **签名**: `T(msg_id, context="*")`
- **行为**:
    - 检查用户的语言偏好设置。
    - 如果是 "Follow System"（跟随系统）: 委托给 `bpy.app.translations.pgettext(msg_id, context)`。
    - 如果是 "zh_HANS"（简体中文）: 
        - 如果系统本身是中文，`pgettext` 可以工作。
        - 如果系统**不是**中文，则在已加载的字典中进行手动查找。
    - 如果是 "en_US"（英文）: 返回原始 `msg_id`（假设源代码使用英文编写）。

### 4. 用户偏好设置
- **位置**: `operators.py` 中的 `ACA_OT_Preferences`。
- **选项**:
    - `FOLLOW`: 跟随系统 (默认)
    - `zh_HANS`: 简体中文
    - `en_US`: English

## 需要创建/修改的文件
1.  `locale/i18n.py` (新建)
2.  `locale/zh_HANS.py` (新建)
3.  `operators.py` (修改 `ACA_OT_Preferences`)
4.  `__init__.py` (修改 `register` 和 `unregister`)

## 字典结构示例
```python
# locale/zh_HANS.py
data = {
    "zh_HANS": {
        ("*", "Hello"): "你好",
        ("Operator", "Hello"): "您好",
    }
}
```
