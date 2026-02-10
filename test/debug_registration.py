"""
调试类注册顺序的脚本
用于验证自动注册是否按正确顺序排列PropertyGroup
"""

import inspect
from typing import List, Type

def analyze_property_groups():
    """分析data.py中的PropertyGroup定义顺序"""
    from . import data
    
    # 获取所有PropertyGroup类
    property_groups = []
    for name in dir(data):
        obj = getattr(data, name)
        if inspect.isclass(obj):
            base_names = [base.__name__ for base in obj.__bases__]
            if 'PropertyGroup' in base_names or any(base.__name__.startswith('ACA_data_') for base in obj.__bases__):
                try:
                    source_file = inspect.getsourcefile(obj)
                    source_lines = inspect.getsourcelines(obj)
                    line_number = source_lines[1] if source_lines else 0
                    property_groups.append({
                        'name': obj.__name__,
                        'line': line_number,
                        'file': source_file
                    })
                except:
                    pass
    
    # 按行号排序
    property_groups.sort(key=lambda x: x['line'])
    
    print("\n" + "="*80)
    print("PropertyGroup 定义顺序（按源文件行号）")
    print("="*80)
    for idx, pg in enumerate(property_groups, 1):
        print(f"{idx:2d}. 第 {pg['line']:4d} 行: {pg['name']}")
    
    # 检查CollectionProperty依赖
    print("\n" + "="*80)
    print("CollectionProperty 依赖关系检查")
    print("="*80)
    
    dependencies = {
        'ACA_data_obj': [
            ('combo_children', 'ACA_id_list'),
            ('step_list', 'ACA_data_taduo'),
            ('railing_list', 'ACA_data_railing'),
            ('maindoor_list', 'ACA_data_maindoor'),
            ('wall_list', 'ACA_data_wall_common'),
            ('window_list', 'ACA_data_door_common'),
            ('geshan_list', 'ACA_data_geshan'),
        ]
    }
    
    pg_dict = {pg['name']: pg['line'] for pg in property_groups}
    
    for class_name, deps in dependencies.items():
        class_line = pg_dict.get(class_name, -1)
        print(f"\n{class_name} (第 {class_line} 行) 依赖:")
        for prop_name, dep_class in deps:
            dep_line = pg_dict.get(dep_class, -1)
            status = "✅" if dep_line < class_line else "❌"
            print(f"  {status} {prop_name}: {dep_class} (第 {dep_line} 行)")

if __name__ == "__main__":
    analyze_property_groups()
