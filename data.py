# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy
from functools import partial

from .const import ACA_Consts as con
from . import utils


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

# 筛选资产目录
def p_filter(self, object:bpy.types.Object):
    # 仅返回Assets collection中的对象
    return object.users_collection[0].name == 'Assets'

def update_test(self, context:bpy.types.Context):
    utils.outputMsg("update triggered")

# 重建整体建筑
def update_building(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object 
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        # 调用营造序列
        from . import buildFloor
        buildFloor.buildFloor(buildingObj)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
        return

# 调整建筑斗口
def update_dk(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object
    dk = buildingObj.ACA_data.DK
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        # 更新DK值
        from . import acaTemplate
        acaTemplate.updateTemplateByDK(dk,buildingObj)
        from . import buildFloor
        buildFloor.buildFloor(buildingObj)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
        return

def update_platform(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        # 调用台基缩放
        from . import buildPlatform
        buildPlatform.resizePlatform(buildingObj)
    else:
        utils.outputMsg("updated platform failed, context should be buildingObj")
        return

# 仅更新柱体样式，不触发其他重建
def update_PillerStyle(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object 
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        # 调用营造序列
        from . import buildFloor
        buildFloor.buildPillers(buildingObj)
        pass
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
        return

# 更新柱体尺寸，会自动触发墙体重建
def update_piller(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        # 缩放柱形
        from . import buildFloor
        buildFloor.resizePiller(buildingObj)
    else:
        utils.outputMsg("updated piller failed, context should be pillerObj")
        return

def update_wall(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        from . import buildWall
        # 重新生成墙体
        funproxy = partial(buildWall.resetWallLayout,buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
        return
    
def update_roof(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj = context.object
    if buildingObj.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
        from . import buildRoof
        # 重新生成墙体
        funproxy = partial(buildRoof.buildRoof,buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
        return

# 对象范围的数据
# 可绑定面板参数属性
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_obj(bpy.types.PropertyGroup):
    # 通用对象属性
    aca_obj : bpy.props.BoolProperty(
            name = '是ACA对象',
            default = False
        ) # type: ignore
    aca_type : bpy.props.StringProperty(
            name = '对象类型',
        ) # type: ignore
    template_name : bpy.props.StringProperty(
            name = '模版名称'
        ) #type: ignore
    DK: bpy.props.FloatProperty(
            name = "斗口",
            min=0.01,
            update = update_dk
        ) # type: ignore
    
    # 台基对象属性
    platform_height : bpy.props.FloatProperty(
            name = "台基高度",
            min = 0.01, 
            update = update_platform # 绑定回调
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name = "台基下出",
            min = 0.01, 
            update = update_platform    # 绑定回调
        ) # type: ignore
    
    # 柱网对象属性
    x_total : bpy.props.FloatProperty(
            name = "通面阔"
        )# type: ignore
    y_total : bpy.props.FloatProperty(
            name = "通进深"
        )# type: ignore
    x_rooms : bpy.props.IntProperty(
            name = "面阔间数",
            min = 1, max = 11,step = 2,
            update= update_building
        )# type: ignore
    x_1 : bpy.props.FloatProperty(
            name = "明间宽度",
            min = 0, 
            update = update_building
        )# type: ignore
    x_2 : bpy.props.FloatProperty(
            name = "次间宽度",
            min = 0, 
            update = update_building
        )# type: ignore
    x_3 : bpy.props.FloatProperty(
            name = "梢间宽度",
            min = 0, 
            update = update_building
        )# type: ignore
    x_4 : bpy.props.FloatProperty(
            name = "尽间宽度",
            min = 0, 
            update = update_building
        )# type: ignore
    y_rooms : bpy.props.IntProperty(
            name = "进深间数",
            max = 5,
            min = 1, 
            update = update_building
        )# type: ignore
    y_1 : bpy.props.FloatProperty(
            name = "明间深度",
            min = 0, 
            update = update_building
        )# type: ignore
    y_2 : bpy.props.FloatProperty(
            name = "次间深度",
            min = 0, 
            update = update_building
        )# type: ignore
    y_3 : bpy.props.FloatProperty(
            name = "梢间深度",
            min = 0, 
            update = update_building
        )# type: ignore
    piller_net : bpy.props.StringProperty(
            name = "保存的柱网列表"
        )# type: ignore
    
    # 柱子属性
    piller_source : bpy.props.PointerProperty(
            name = "柱样式",
            type = bpy.types.Object,
            poll = p_filter,
            update = update_PillerStyle,
        )# type: ignore
    piller_height : bpy.props.FloatProperty(
            name = "柱高",
            default = 0,
            min = 0.01, 
            update = update_piller,
        )# type: ignore
    piller_diameter : bpy.props.FloatProperty(
            name = "柱径",
            default = 0,
            min = 0.01, 
            update = update_piller
        )# type: ignore
    
    # 墙体属性
    wall_layout : bpy.props.EnumProperty(
            name = "墙体布局",
            description = "墙体布局",
            items = [
                ("0","-无墙体-",""),
                ("1","默认(无廊)",""),
                ("2","周围廊",""),
                ("3","前廊",""),
                ("4","斗底槽",""),
            ],
            update = update_wall,
            options = {"ANIMATABLE"}
        ) # type: ignore
    wall_style : bpy.props.EnumProperty(
            name = "墙类型",
            items = [
                ("","",""),
                ("1","槛墙",""),
                ("2","隔扇",""),
                #("3","槛窗",""),
            ],
        ) # type: ignore
    wall_source : bpy.props.PointerProperty(
            name = "墙样式",
            type = bpy.types.Object,
            poll = p_filter,
            update = update_wall
        )# type: ignore 
    
    # 隔扇属性
    door_height : bpy.props.FloatProperty(
            name="中槛高度",
        )# type: ignore 
    door_num : bpy.props.IntProperty(
            name="隔扇数量",
            default=4, max=4,
        )# type: ignore 
    gap_num : bpy.props.IntProperty(
            name="抹头数量",
            default=5,min=2,max=6
        )# type: ignore 
    is_with_wall: bpy.props.BoolProperty(
            default=False,
            name="添加槛墙"
        )# type: ignore 
    lingxin_source:bpy.props.PointerProperty(
            name = "棂心",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    
    # 斗栱属性
    dg_piller_source:bpy.props.PointerProperty(
            name = "柱头斗栱",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    dg_fillgap_source:bpy.props.PointerProperty(
            name = "补间斗栱",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    dg_corner_source:bpy.props.PointerProperty(
            name = "转角斗栱",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    dg_extend : bpy.props.FloatProperty(
            name="斗栱挑檐",    # 令拱出跳距离
            default=0.45,
            min=0.0,
        )# type: ignore 
    dg_height : bpy.props.FloatProperty(
            name="斗栱高度",    # 取挑檐桁下皮高度
            default=0.99,
            min=0.0,
        )# type: ignore 
    
    # 屋顶属性
    rafter_count : bpy.props.IntProperty(
            name="椽架数量",
            default=8,
            min=0,max=10,
            update = update_roof,
        )# type: ignore 
    rafter_fb_gap : bpy.props.FloatProperty(
            name="前后檐椽当"
        )# type: ignore 

# 场景范围的数据
# 可绑定面板参数属性
# 也可做为全局变量访问
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_scene(bpy.types.PropertyGroup):
    from . import acaTemplate
    is_auto_redraw : bpy.props.BoolProperty(
            default = True,
            name = "是否实时重绘"
        ) # type: ignore
    template : bpy.props.EnumProperty(
            name = "模版样式",
            description = "模板样式",
            items = acaTemplate.getTemplateList(),
            options = {"ANIMATABLE"}
        ) # type: ignore