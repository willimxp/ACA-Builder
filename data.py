# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy
from . import const
from . import operators

# 初始化自定义属性
def initprop():
    # 在scene中添加可全局访问的自定义数据集
    bpy.types.Scene.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_scene,
        name="古建场景属性集"
    )
    bpy.types.Object.ACA_data = bpy.props.PointerProperty(
        type=ACA_data_obj,
        name="古建构件属性集"
    )

# 销毁自定义属性
def delprop():
    del bpy.types.Scene.ACA_data
    del bpy.types.Object.ACA_data

# 对象范围的数据
# 可绑定面板参数属性
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_obj(bpy.types.PropertyGroup):
    # 模板常数
    con = const.ACA_Consts

    # 通用对象属性
    aca_obj : bpy.props.BoolProperty(
            name='是ACA对象',
            default=True
        ) # type: ignore
    aca_type : bpy.props.StringProperty(
            name='对象类型',
        ) # type: ignore
    
    # 台基对象属性
    platform_height : bpy.props.FloatProperty(
            name="台基高度",
            default=con.PLATFORM_HEIGHT, 
            min=0.01, 
            update = operators.update_platform # 绑定回调
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name="台基下出",
            default=con.PLATFORM_EXTEND, 
            min=0.01, 
            update=operators.update_platform    # 绑定回调
        ) # type: ignore

# 场景范围的数据
# 可绑定面板参数属性
# 也可做为全局变量访问
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_scene(bpy.types.PropertyGroup):
    # 模板常数
    con = const.ACA_Consts
    
    is_auto_redraw : bpy.props.BoolProperty(
            default=True,
            name="是否实时重绘"
        ) # type: ignore
    template_list : bpy.props.EnumProperty(
            name="",
            description="模板样式",
            items=[
                ("1","九檩单檐庑殿周围廊","")
            ],
            options={"ANIMATABLE"}
        ) # type: ignore