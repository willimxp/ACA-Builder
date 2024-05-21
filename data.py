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
    return

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

# 更新建筑，但不重设柱网
def update_building(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildFloor
        buildFloor.buildFloor(buildingObj)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
    
    return
    
# 更新建筑，但不重设柱网
def reset_building(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 调用营造序列
        from . import buildFloor
        buildFloor.resetFloor(buildingObj)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
    return

# 调整建筑斗口
def update_dk(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        dk = buildingObj.ACA_data.DK
        from . import buildFloor
        buildFloor.buildFloor(buildingObj)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
    return

def update_platform(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 调用台基缩放
        from . import buildPlatform
        buildPlatform.resizePlatform(buildingObj)
    else:
        utils.outputMsg("updated platform failed, context should be buildingObj")
    return

# 仅更新柱体样式，不触发其他重建
def update_PillerStyle(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
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
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 缩放柱形
        from . import buildFloor
        buildFloor.resizePiller(buildingObj)
    else:
        utils.outputMsg("updated piller failed, context should be pillerObj")
    return

def update_wall(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildWall
        if odata.aca_type == con.ACA_TYPE_WALL:
            # 仅重新生成当前墙体
            funproxy = partial(buildWall.buildSingleWall,
                               wallproxy=context.object)
            utils.fastRun(funproxy)
        else:
            # 重新生成墙体
            funproxy = partial(buildWall.resetWallLayout,
                               buildingObj=buildingObj)
            utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

# 刷新斗栱布局
def update_dougong(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildDougong
        # 重新生成屋顶
        funproxy = partial(buildDougong.buildDougong,buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

# 刷新斗栱布局
def update_dgHeight(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildDougong
        # 重新生成屋顶
        funproxy = partial(buildDougong.update_dgHeight,buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

def update_roof(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildRoof
        # 重新生成屋顶
        funproxy = partial(buildRoof.buildRoof,buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

def hide_platform(self, context:bpy.types.Context):
    utils.hideLayer(context,'台基',self.is_showPlatform)

def hide_pillers(self, context:bpy.types.Context):
    utils.hideLayer(context,'柱网',self.is_showPillers)

def hide_walls(self, context:bpy.types.Context):
    utils.hideLayer(context,'墙体',self.is_showWalls)

def hide_dougong(self, context:bpy.types.Context):
    utils.hideLayer(context,'斗栱',self.is_showDougong)

def hide_BPW(self, context:bpy.types.Context):
    utils.hideLayer(context,'梁椽望',self.is_showBPW)

def hide_tiles(self, context:bpy.types.Context):
    utils.hideLayer(context,'瓦作',self.is_showTiles)

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
            default=0.0,
            min=0.03,
            max=0.18,
            step=0.01,
            update = update_dk
        ) # type: ignore
    is_showPlatform: bpy.props.BoolProperty(
            default = True,
            name = "是否显示台基",
            update=hide_platform
        ) # type: ignore
    is_showPillers: bpy.props.BoolProperty(
            default = True,
            name = "是否显示柱网",
            update=hide_pillers
        ) # type: ignore
    is_showWalls: bpy.props.BoolProperty(
            default = True,
            name = "是否显示墙体",
            update=hide_walls
        ) # type: ignore
    is_showDougong: bpy.props.BoolProperty(
            default = True,
            name = "是否显示斗栱",
            update=hide_dougong
        ) # type: ignore
    is_showBPW: bpy.props.BoolProperty(
            default = True,
            name = "是否显示梁椽望",
            update=hide_BPW
        ) # type: ignore
    is_showTiles: bpy.props.BoolProperty(
            default = True,
            name = "是否显示瓦作",
            update=hide_tiles
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
            update= reset_building
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
            update = reset_building
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
    wall_net : bpy.props.StringProperty(
            name = "保存的墙体列表"
        )# type: ignore
    fang_net : bpy.props.StringProperty(
            name = "保存的枋列表"
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
            default = 0.0,
            min = 0.01, 
            update = update_piller,
        )# type: ignore
    piller_diameter : bpy.props.FloatProperty(
            name = "柱径",
            default = 0.0,
            min = 0.01, 
            update = update_piller
        )# type: ignore
    use_smallfang: bpy.props.BoolProperty(
            default=False,
            name="小额枋",
            update = update_building
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
                ("3","槛窗",""),
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
            update = update_wall
        )# type: ignore 
    door_num : bpy.props.IntProperty(
            name="隔扇数量",
            default=4, max=4,
            update = update_wall
        )# type: ignore 
    gap_num : bpy.props.IntProperty(
            name="抹头数量",
            default=5,min=2,max=6,
            update = update_wall
        )# type: ignore 
    use_topwin: bpy.props.BoolProperty(
            default=False,
            name="添加横披窗",
            update = update_wall
        )# type: ignore 
    use_KanWall: bpy.props.BoolProperty(
            default=False,
            name="添加槛墙"
        )# type: ignore 
    lingxin_source:bpy.props.PointerProperty(
            name = "棂心",
            type = bpy.types.Object,
            poll = p_filter,
            update = update_wall
        )# type: ignore 
    
    # 斗栱属性
    use_dg :  bpy.props.BoolProperty(
            default=False,
            name="使用斗栱",
            update=update_roof
        )# type: ignore 
    use_pingbanfang: bpy.props.BoolProperty(
            default=True,
            name="使用平板枋",
            update=update_roof
        )# type: ignore 
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
            min=0.01,
        )# type: ignore 
    dg_height : bpy.props.FloatProperty(
            name="斗栱高度",    # 取挑檐桁下皮高度
            default=0.99,
            min=0.01,
            update = update_dgHeight,
        )# type: ignore 
    dg_scale:bpy.props.FloatVectorProperty(
            name="斗栱缩放",    # 斗栱缩放
            default=(1,1,1),
        )# type: ignore 
    dg_gap:bpy.props.FloatProperty(
            name="斗栱间距",    # 斗栱间距
            default=0.99,
            min=0.1,
            update=update_dougong,
        )# type: ignore 
    
    # 屋顶属性
    roof_style : bpy.props.EnumProperty(
            name = "屋顶类型",
            items = [
                ("","",""),
                ("1","庑殿顶",""),
                ("2","歇山顶",""),
                ("3","悬山顶",""),
                ("4","硬山顶",""),
            ],
            update = update_roof,
        ) # type: ignore
    rafter_count : bpy.props.IntProperty(
            name="椽架数量",
            default=8,
            min=0,max=10,
            update = update_roof,
        )# type: ignore 
    use_flyrafter :  bpy.props.BoolProperty(
            default=True,
            name="添加飞椽",
            update = update_roof,
        )# type: ignore 
    use_wangban :  bpy.props.BoolProperty(
            default=True,
            name="添加望板",
            update = update_roof,
        )# type: ignore 
    qiqiao: bpy.props.IntProperty(
            name="起翘(椽径倍数)",
            default=4, 
            update=update_roof
        )# type: ignore 
    chong: bpy.props.IntProperty(
            name="出冲(椽径倍数)",
            default=3, 
            update=update_roof
        )# type: ignore 
    shengqi: bpy.props.IntProperty(
            name="生起(椽径倍数)",
            default=1, 
            update=update_roof
        )# type: ignore 
    roof_qiao_point : bpy.props.FloatVectorProperty(
        name="翼角起翘参考点",
        subtype='XYZ',
        unit='LENGTH',
        )# type: ignore 
    
    # 博缝板
    bofeng_source : bpy.props.PointerProperty(
            name = "博缝板",
            type = bpy.types.Object,
        )# type: ignore
    
    # 瓦作属性
    tile_width : bpy.props.FloatProperty(
            name="瓦垄宽度", 
            default=0.4,
            min=0.0,
        )# type: ignore
    tile_width_real : bpy.props.FloatProperty(
            name="瓦垄实际宽度", 
        )# type: ignore
    tile_length : bpy.props.FloatProperty(
            name="瓦片长度", 
            default=0.4,
            min=0.0,
        )# type: ignore
    flatTile_source:bpy.props.PointerProperty(
            name = "板瓦",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    circularTile_source:bpy.props.PointerProperty(
            name = "筒瓦",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    eaveTile_source:bpy.props.PointerProperty(
            name = "瓦当",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    dripTile_source:bpy.props.PointerProperty(
            name = "滴水",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    
    # 屋脊属性
    ridgeTop_source:bpy.props.PointerProperty(
            name = "正脊筒",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    ridgeBack_source:bpy.props.PointerProperty(
            name = "垂脊兽后",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    ridgeFront_source:bpy.props.PointerProperty(
            name = "垂脊兽前",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    ridgeEnd_source:bpy.props.PointerProperty(
            name = "端头盘子",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    chiwen_source:bpy.props.PointerProperty(
            name = "螭吻",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    chuishou_source:bpy.props.PointerProperty(
            name = "垂兽",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    taoshou_source:bpy.props.PointerProperty(
            name = "套兽",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_0_source:bpy.props.PointerProperty(
            name = "仙人",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_1_source:bpy.props.PointerProperty(
            name = "龙",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_2_source:bpy.props.PointerProperty(
            name = "凤",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_3_source:bpy.props.PointerProperty(
            name = "狮子",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_4_source:bpy.props.PointerProperty(
            name = "海马",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_5_source:bpy.props.PointerProperty(
            name = "天马",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_6_source:bpy.props.PointerProperty(
            name = "狎鱼",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_7_source:bpy.props.PointerProperty(
            name = "狻猊",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_8_source:bpy.props.PointerProperty(
            name = "獬豸",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_9_source:bpy.props.PointerProperty(
            name = "斗牛",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    paoshou_10_source:bpy.props.PointerProperty(
            name = "行什",
            type = bpy.types.Object,
            poll = p_filter
        )# type: ignore 
    
    mat_wood:bpy.props.PointerProperty(
            name = "木材材质",
            type = bpy.types.Object,
        )# type: ignore 
    mat_rock:bpy.props.PointerProperty(
            name = "石材材质",
            type = bpy.types.Object,
        )# type: ignore 
    mat_stone:bpy.props.PointerProperty(
            name = "石头材质",
            type = bpy.types.Object,
        )# type: ignore 
    mat_red:bpy.props.PointerProperty(
            name = "红漆材质",
            type = bpy.types.Object,
        )# type: ignore 


# 使用动态enumproperty时，必须声明全局变量持久化返回的回调数据
# https://docs.blender.org/api/current/bpy.props.html
# Warning
# There is a known bug with using a callback, 
# Python must keep a reference to the strings 
# returned by the callback or Blender will 
# misbehave or even crash.
templateList = []
def getTemplateList(self, context):
    from . import acaTemplate
    global templateList
    templateList = acaTemplate.getTemplateList()
    return templateList

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
            name = "模版",
            description = "模板样式",
            items = getTemplateList,
            options = {"ANIMATABLE"},
        ) # type: ignore