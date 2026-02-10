# 测试文件：验证自动注册功能
# 使用方法：在Blender的Text Editor中运行此脚本

import sys
import os

# 添加插件路径到sys.path（如果需要）
addon_path = os.path.dirname(__file__)
if addon_path not in sys.path:
    sys.path.insert(0, addon_path)

# 导入模块
from . import auto_register
from . import data, panel, operators

def test_auto_register():
    """测试自动注册功能"""
    
    print("=" * 60)
    print("开始测试自动注册功能")
    print("=" * 60)
    
    # 获取自动发现的类
    classes = auto_register.auto_register_classes(data, panel, operators)
    
    print(f"\n✓ 成功发现 {len(classes)} 个类\n")
    
    # 打印详细信息
    info = auto_register.get_registration_info(classes)
    print(info)
    
    # 验证类
    print("\n" + "=" * 60)
    print("验证类的有效性")
    print("=" * 60)
    
    is_valid, errors = auto_register.validate_classes(classes)
    
    if is_valid:
        print("\n✓ 所有类都符合Blender注册要求")
    else:
        print(f"\n✗ 发现 {len(errors)} 个问题:")
        for error in errors:
            print(f"  - {error}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    test_auto_register()
