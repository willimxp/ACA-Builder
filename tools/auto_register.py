# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：自动类注册工具，用于自动发现和注册Blender类

import inspect
import bpy
from typing import List, Type, Tuple

def get_classes_from_module(module) -> List[Type]:
    """
    从模块中自动提取Blender类
    
    Args:
        module: Python模块对象
        
    Returns:
        List[Type]: Blender类列表
    """
    classes = []
    
    for name, obj in inspect.getmembers(module):
        if not inspect.isclass(obj):
            continue
        
        # 跳过导入的外部类
        if obj.__module__ != module.__name__:
            continue
        
        # 检查是否是Blender类型
        if _is_blender_class(obj):
            classes.append(obj)
    
    return classes

def _is_blender_class(cls) -> bool:
    """
    判断是否是Blender类
    
    Args:
        cls: 类对象
        
    Returns:
        bool: 是否是Blender类
    """
    # 检查是否有 bl_idname 属性（最常见的Blender类标识）
    if hasattr(cls, 'bl_idname'):
        return True
    
    # 检查是否有 bl_label 属性
    if hasattr(cls, 'bl_label'):
        return True
    
    # 检查是否有 bl_rna 属性（已注册的类）
    if hasattr(cls, 'bl_rna'):
        return True
    
    # 检查类名是否符合Blender类命名规范
    class_name = cls.__name__
    if any([
        class_name.startswith('ACA_PT_'),  # Panel
        class_name.startswith('ACA_OT_'),  # Operator
        class_name.startswith('ACA_UL_'),  # UIList
        class_name.startswith('ACA_MT_'),  # Menu
        class_name.startswith('ACA_HT_'),  # Header
    ]):
        return True
    
    # 检查是否是PropertyGroup（通过检查基类名称）
    try:
        base_names = [base.__name__ for base in cls.__bases__]
        if 'PropertyGroup' in base_names:
            return True
    except:
        pass
    
    return False

def sort_classes_by_dependency(classes: List[Type]) -> List[Type]:
    """
    按依赖关系排序类（PropertyGroup需要先注册）
    
    注册顺序：
    1. PropertyGroup（数据类）- 按在源文件中的定义顺序
    2. AddonPreferences（插件偏好设置）
    3. UIList（UI列表）
    4. Operator（操作符）
    5. Menu（菜单）
    6. Panel（面板）
    7. Header（头部）
    
    Args:
        classes: 类列表
        
    Returns:
        List[Type]: 排序后的类列表
    """
    property_groups = []
    addon_prefs = []
    ui_lists = []
    operators = []
    menus = []
    panels = []
    headers = []
    others = []
    
    for cls in classes:
        class_name = cls.__name__
        
        # 通过类名前缀和基类名称判断类型（递归检查所有基类）
        if _is_property_group(cls):
            property_groups.append(cls)
        elif _has_base_class(cls, 'AddonPreferences'):
            addon_prefs.append(cls)
        elif class_name.startswith('ACA_UL_') or _has_base_class(cls, 'UIList'):
            ui_lists.append(cls)
        elif class_name.startswith('ACA_OT_') or _has_base_class(cls, 'Operator'):
            operators.append(cls)
        elif class_name.startswith('ACA_MT_') or _has_base_class(cls, 'Menu'):
            menus.append(cls)
        elif class_name.startswith('ACA_PT_') or _has_base_class(cls, 'Panel'):
            panels.append(cls)
        elif class_name.startswith('ACA_HT_') or _has_base_class(cls, 'Header'):
            headers.append(cls)
        else:
            others.append(cls)
    
    # PropertyGroup按模块和定义顺序排序
    # 这很重要，因为有些PropertyGroup可能依赖其他PropertyGroup
    property_groups = _sort_by_source_order(property_groups)
    
    # Panel按父子关系排序（父Panel必须先注册）
    panels = _sort_panels_by_dependency(panels)
    
    # 按依赖顺序组合
    return (property_groups + addon_prefs + ui_lists + 
            operators + menus + others + panels + headers)

def _is_property_group(cls) -> bool:
    """递归检查类是否是PropertyGroup或其子类"""
    return _has_base_class(cls, 'PropertyGroup')

def _has_base_class(cls, base_class_name: str) -> bool:
    """
    递归检查类是否继承自指定的基类（通过基类名称判断）
    
    Args:
        cls: 要检查的类
        base_class_name: 基类名称（如 'PropertyGroup', 'Panel'等）
        
    Returns:
        bool: 如果类继承自指定基类则返回True
    """
    try:
        # 检查所有基类（包括间接基类）
        for base in cls.__mro__[1:]:  # 跳过自己，检查所有父类
            if base.__name__ == base_class_name:
                return True
        return False
    except:
        return False

def _sort_panels_by_dependency(panels: List[Type]) -> List[Type]:
    """
    按父子关系排序Panel（父Panel必须先注册）
    
    Args:
        panels: Panel类列表
        
    Returns:
        List[Type]: 排序后的Panel列表
    """
    # 分离顶级Panel和子Panel
    root_panels = []
    child_panels = []
    
    for panel in panels:
        if hasattr(panel, 'bl_parent_id') and panel.bl_parent_id:
            child_panels.append(panel)
        else:
            root_panels.append(panel)
    
    # 顶级Panel按源文件定义顺序排序
    root_panels = _sort_by_source_order(root_panels)
    
    # 子Panel按源文件定义顺序排序
    child_panels = _sort_by_source_order(child_panels)
    
    # 顶级Panel在前，子Panel在后
    return root_panels + child_panels

def _sort_by_source_order(classes: List[Type]) -> List[Type]:
    """
    按源文件中的定义顺序排序类
    
    Args:
        classes: 类列表
        
    Returns:
        List[Type]: 排序后的类列表
    """
    def get_sort_key(cls):
        try:
            import inspect
            source_file = inspect.getsourcefile(cls)
            source_lines = inspect.getsourcelines(cls)
            line_number = source_lines[1] if source_lines else 0
            return (source_file or '', line_number)
        except:
            return ('', 0)
    
    return sorted(classes, key=get_sort_key)

def auto_register_classes(*modules) -> Tuple[Type, ...]:
    """
    自动注册多个模块中的类
    
    使用示例:
        from . import panel, operators, data
        from .tools import auto_register
        
        classes = auto_register.auto_register_classes(data, panel, operators)
    
    Args:
        *modules: 要扫描的模块列表
        
    Returns:
        Tuple[Type, ...]: 所有需要注册的类（按依赖顺序排序）
    """
    all_classes = []
    
    # 从每个模块中提取类
    for module in modules:
        classes = get_classes_from_module(module)
        all_classes.extend(classes)
    
    # 去重（使用集合，然后转回列表）
    unique_classes = list(set(all_classes))
    
    # 按依赖关系排序
    sorted_classes = sort_classes_by_dependency(unique_classes)
    
    return tuple(sorted_classes)

def get_registration_info(classes: Tuple[Type, ...]) -> str:
    """
    获取类注册信息（用于调试和日志）
    
    Args:
        classes: 类元组
        
    Returns:
        str: 格式化的注册信息
    """
    info_lines = [f"共发现 {len(classes)} 个类需要注册:\n"]
    
    # 按类型分组统计
    type_counts = {}
    for cls in classes:
        base_type = _get_class_type(cls)
        type_counts[base_type] = type_counts.get(base_type, 0) + 1
    
    info_lines.append("类型统计:")
    for type_name, count in sorted(type_counts.items()):
        info_lines.append(f"  {type_name}: {count}个")
    
    info_lines.append("\n详细列表:")
    for i, cls in enumerate(classes, 1):
        class_type = _get_class_type(cls)
        info_lines.append(f"  {i:3d}. {cls.__name__:45s} ({class_type})")
    
    return "\n".join(info_lines)

def _get_class_type(cls) -> str:
    """获取类的类型名称"""
    class_name = cls.__name__
    
    # 通过类名前缀和基类名称判断类型（使用递归检查）
    if _is_property_group(cls):
        return "PropertyGroup"
    elif class_name.startswith('ACA_PT_') or _has_base_class(cls, 'Panel'):
        return "Panel"
    elif class_name.startswith('ACA_OT_') or _has_base_class(cls, 'Operator'):
        return "Operator"
    elif class_name.startswith('ACA_UL_') or _has_base_class(cls, 'UIList'):
        return "UIList"
    elif class_name.startswith('ACA_MT_') or _has_base_class(cls, 'Menu'):
        return "Menu"
    elif class_name.startswith('ACA_HT_') or _has_base_class(cls, 'Header'):
        return "Header"
    elif _has_base_class(cls, 'AddonPreferences'):
        return "AddonPreferences"
    
    return "Unknown"

def validate_classes(classes: Tuple[Type, ...]) -> Tuple[bool, List[str]]:
    """
    验证类是否符合Blender注册要求
    
    Args:
        classes: 类元组
        
    Returns:
        Tuple[bool, List[str]]: (是否全部有效, 错误信息列表)
    """
    errors = []
    
    for cls in classes:
        class_name = cls.__name__
        
        # 检查Panel/Operator/Menu是否有必需属性（使用递归检查）
        is_panel = class_name.startswith('ACA_PT_') or _has_base_class(cls, 'Panel')
        is_operator = class_name.startswith('ACA_OT_') or _has_base_class(cls, 'Operator')
        is_menu = class_name.startswith('ACA_MT_') or _has_base_class(cls, 'Menu')
        
        if is_panel or is_operator or is_menu:
            if not hasattr(cls, 'bl_idname'):
                errors.append(f"{cls.__name__} 缺少 bl_idname 属性")
            if not hasattr(cls, 'bl_label'):
                errors.append(f"{cls.__name__} 缺少 bl_label 属性")
    
    return len(errors) == 0, errors
