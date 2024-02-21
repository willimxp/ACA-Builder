# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy
from . import const

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

# 修改数据时，触发的回调
def update_platform(self, context):
    # 0、数据初始化（常量、场景参数、对象参数）
    # 0.1、载入常量列表
    con = const.ACA_Consts
    # 0.2、从当前场景中载入数据集
    scnData : ACA_data_scene = context.scene.ACA_data
    # 0.3、从当前场景中载入数据集
    if context.object != None:
        objData : ACA_data_obj = context.object.ACA_data

    if scnData.is_auto_redraw:
        # 重绘
        pf_obj = bpy.context.object
        pf_extend = objData.platform_extend
        pf_obj.dimensions= (
            pf_extend * 2 + scnData.x_total,
            pf_extend * 2 + scnData.y_total,
            objData.platform_height
        )
        pf_obj.location.z = objData.platform_height /2
        bpy.ops.object.transform_apply(
            scale=True,
            rotation=True,
            location=False,
            isolate_users=True) # apply多用户对象时可能失败，所以要加上这个强制单用户
        

# 修改数据时，自动调用重绘
def update_piller(self, context):
    dataset : ACA_data_scene = context.scene.ACA_data

    if dataset.is_auto_redraw:
        # 重绘
        bpy.ops.aca.build_piller()

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
            default=1, min=0.01, 
            update=update_platform
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name="台基下出",
            default=1, min=0.01, 
            update=update_platform
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
    x_rooms : bpy.props.IntProperty(
            name="面阔间数",
            default=3, min=1, max=11,step=2,
            update=update_piller
        ) # type: ignore
    x_1 : bpy.props.FloatProperty(
            name="明间宽度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    x_2 : bpy.props.FloatProperty(
            name="次间宽度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    x_3 : bpy.props.FloatProperty(
            name="梢间宽度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    x_4 : bpy.props.FloatProperty(
            name="尽间宽度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    x_total : bpy.props.FloatProperty(
            name="通面阔"
        ) # type: ignore
    y_rooms : bpy.props.IntProperty(
            name="进深间数",
            default=3, min=1, 
            update=update_piller
        ) # type: ignore
    y_1 : bpy.props.FloatProperty(
            name="明间深度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    y_2 : bpy.props.FloatProperty(
            name="次间深度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    y_3 : bpy.props.FloatProperty(
            name="梢间深度",
            default=3, min=0, 
            update=update_piller
        ) # type: ignore
    y_total : bpy.props.FloatProperty(
            name="通进深"
        ) # type: ignore
    piller_net : bpy.props.StringProperty(
                name="保存的柱网列表"
        ) # type: ignore
