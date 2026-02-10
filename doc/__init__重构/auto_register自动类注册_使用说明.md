# 自动类注册功能使用说明

## 📋 概述

自动类注册功能会自动扫描指定模块中的所有Blender类，无需手动维护类列表。这大大简化了插件的维护工作。

## ✨ 主要优势

1. **自动发现类**：无需手动列举每个类
2. **减少维护成本**：新增类时无需修改`__init__.py`
3. **智能排序**：按依赖关系自动排序（PropertyGroup在前）
4. **类型安全**：自动验证类的有效性
5. **调试友好**：提供详细的注册信息

## 🚀 使用方法

### 在`__init__.py`中使用

```python
from .tools import auto_register
from . import data, panel, operators

# 自动获取所有需要注册的类
classes = auto_register.auto_register_classes(data, panel, operators)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
```

### 打印注册信息（调试用）

```python
# 方法1：直接打印
print(auto_register.get_registration_info(classes))

# 方法2：记录到日志
logger = logging.getLogger("ACA")
logger.info(f"成功注册 {len(classes)} 个类")
logger.debug(auto_register.get_registration_info(classes))
```

## 📊 注册顺序

类会按以下顺序自动排序，确保依赖关系正确：

1. **PropertyGroup** - 数据类（按源文件定义顺序，处理CollectionProperty依赖）
2. **AddonPreferences** - 插件偏好设置
3. **UIList** - UI列表
4. **Operator** - 操作符
5. **Menu** - 菜单
6. **Panel** - 面板（父Panel先注册，子Panel后注册）
7. **Header** - 头部

### 关键特性

- **PropertyGroup继承链**：使用MRO检查，支持多级继承（如`ACA_data_maindoor` → `ACA_data_door_common` → `ACA_data_wall_common` → `PropertyGroup`）
- **CollectionProperty依赖**：按源文件行号排序，确保被引用的类先注册
- **Panel父子关系**：检查`bl_parent_id`，父Panel先于子Panel注册

## ✅ 类验证

自动注册会验证类是否符合Blender要求：

```python
is_valid, errors = auto_register.validate_classes(classes)
if not is_valid:
    for error in errors:
        print(error)
```

常见验证检查：
- Panel/Operator/Menu 必须有 `bl_idname`
- Panel/Operator/Menu 必须有 `bl_label`

## 📝 新增类的步骤

### 之前的方式（需要修改3个地方）

1. 在模块中定义类（如`operators.py`）
2. 在`__init__.py`中导入模块
3. **手动添加类到`classes`元组** ⚠️

### 现在的方式（只需1步）

1. 在模块中定义类（如`operators.py`）✓
2. ~~在`__init__.py`中导入模块~~ 已导入
3. ~~手动添加类到`classes`元组~~ **自动完成** ✓

## 🔧 API参考

### `auto_register_classes(*modules)`

从多个模块中自动提取并注册所有Blender类。

**参数**：
- `*modules`: 要扫描的模块列表

**返回**：
- `Tuple[Type, ...]`: 按依赖顺序排序的类元组

**示例**：
```python
classes = auto_register.auto_register_classes(data, panel, operators)
```

---

### `get_registration_info(classes)`

获取类注册的详细信息（用于调试）。

**参数**：
- `classes`: 类元组

**返回**：
- `str`: 格式化的注册信息

**示例**：
```python
info = auto_register.get_registration_info(classes)
print(info)
```

输出示例：
```
共发现 69 个类需要注册:

类型统计:
  Operator: 43个
  Panel: 11个
  PropertyGroup: 14个
  UIList: 1个

详细列表:
    1. ACA_id_list                               (PropertyGroup)
    2. ACA_data_taduo                            (PropertyGroup)
    ...
```

---

### `validate_classes(classes)`

验证类是否符合Blender注册要求。

**参数**：
- `classes`: 类元组

**返回**：
- `Tuple[bool, List[str]]`: (是否全部有效, 错误信息列表)

**示例**：
```python
is_valid, errors = auto_register.validate_classes(classes)
if not is_valid:
    for error in errors:
        print(f"错误: {error}")
```

## ⚙️ 高级配置

### 排除特定类

如果需要排除某些类不参与自动注册，可以添加特殊标记：

```python
class MyClass(bpy.types.Operator):
    """这个类不会被自动注册"""
    _exclude_from_auto_register = True
    # ...
```

然后修改`auto_register.py`中的`_is_blender_class()`函数：

```python
def _is_blender_class(cls) -> bool:
    # 排除标记的类
    if hasattr(cls, '_exclude_from_auto_register'):
        return False
    # ... 其他判断
```

### 自定义排序规则

如果需要自定义类的注册顺序，修改`sort_classes_by_dependency()`函数：

```python
def sort_classes_by_dependency(classes):
    # 添加自定义排序逻辑
    priority_classes = []  # 优先注册的类
    normal_classes = []    # 普通类
    
    for cls in classes:
        if hasattr(cls, '_register_priority'):
            priority_classes.append(cls)
        else:
            normal_classes.append(cls)
    
    return priority_classes + normal_classes
```

## 🐛 故障排除

### 问题1：ImportError: cannot import name 'auto_register'

**原因**：`auto_register.py`已移动到`tools/`目录，导入路径错误

**解决方法**：
将导入语句从：
```python
from . import auto_register  # 错误
```
改为：
```python
from .tools import auto_register  # 正确
```

### 问题2：CollectionProperty注册失败

**原因**：被引用的PropertyGroup类尚未注册

**解决方法**：
- 确保`auto_register.py`中的`_sort_property_groups_by_source_order()`正常工作
- 检查类定义顺序，被引用的类应该在前

### 问题3：Panel注册失败：parent not found

**原因**：子Panel的父Panel尚未注册

**解决方法**：
- 确保`auto_register.py`中的`_sort_panels_by_dependency()`正常工作
- 检查`bl_parent_id`指向的父Panel是否存在

### 问题4：某些类没有被发现

**原因**：类可能不符合Blender类的判断条件

**解决方法**：
1. 确保类继承自Blender基类（如`bpy.types.Operator`）
2. 确保类有`bl_idname`或`bl_label`属性
3. 检查类名是否符合ACA命名规范（如`ACA_OT_`、`ACA_PT_`等）
4. 运行测试脚本检查：`test/test_auto_register.py`

## 📁 文件位置

- **主模块**：`tools/auto_register.py`
- **测试脚本**：`test/test_auto_register.py`
- **调试工具**：`test/debug_registration.py`

## 📄 许可证

与ACA Builder项目保持一致
