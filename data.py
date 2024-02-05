# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy

# 初始化自定义属性
def initprop():
    # 在scene中添加可全局访问的自定义数据集
    bpy.types.Scene.ACA_data = bpy.props.PointerProperty(
            type=ACA_data_scene,
            name="中国古建筑数据集"
    )
    bpy.types.Object.aca_obj = bpy.props.BoolProperty(default=True)
    bpy.types.Object.aca_type = bpy.props.StringProperty()

# 销毁自定义属性
def delprop():
    del bpy.types.Scene.ACA_data
    del bpy.types.Object.aca_obj
    del bpy.types.Object.aca_type

# 修改数据时，触发的回调
def update_platform(self, context):
    dataset : ACA_data_scene = context.scene.ACA_data

    if dataset.is_auto_redraw:
        # 重绘
        bpy.ops.aca.build_platform()

# 修改数据时，自动调用重绘
def update_piller(self, context):
    dataset : ACA_data_scene = context.scene.ACA_data

    if dataset.is_auto_redraw:
        # 重绘
        bpy.ops.aca.build_piller()

# 场景范围的数据
# 可绑定面板参数属性
# 也可做为全局变量访问
class ACA_data_scene(bpy.types.PropertyGroup):
    is_auto_redraw : bpy.props.BoolProperty(
            default=True,
            name="是否实时重绘"
        )
    platform_height: bpy.props.FloatProperty(
        name="台基高度",
        default=1,
        min=0,
        update=update_platform
    )
    platform_extend: bpy.props.FloatProperty(
        name="台基下出",
        default=1,
        min=0,
        update=update_platform
    )
    x_rooms : bpy.props.IntProperty(
            name="面阔间数",
            default=3, min=1, max=11,step=2,
            update=update_piller
        )
    x_1 : bpy.props.FloatProperty(
        name="明间宽度",
        default=3, min=0, 
        update=update_piller
    )
    x_2 : bpy.props.FloatProperty(
        name="次间宽度",
        default=3, min=0, 
        update=update_piller
    )
    x_3 : bpy.props.FloatProperty(
        name="梢间宽度",
        default=3, min=0, 
        update=update_piller
    )
    x_4 : bpy.props.FloatProperty(
        name="尽间宽度",
        default=3, min=0, 
        update=update_piller
    )
    x_total : bpy.props.FloatProperty(
        name="通面阔"
    )
    y_rooms : bpy.props.IntProperty(
            name="进深间数",
            default=3, min=1, 
            update=update_piller
        )
    y_1 : bpy.props.FloatProperty(
        name="明间深度",
        default=3, min=0, 
        update=update_piller
    )
    y_2 : bpy.props.FloatProperty(
        name="次间深度",
        default=3, min=0, 
        update=update_piller
    )
    y_3 : bpy.props.FloatProperty(
        name="梢间深度",
        default=3, min=0, 
        update=update_piller
    )
    y_total : bpy.props.FloatProperty(
        name="通进深"
    )
    piller_net : bpy.props.StringProperty(
            name="保存的柱网列表"
    )
