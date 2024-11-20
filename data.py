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
    bpy.types.Scene.ACA_temp = bpy.props.PointerProperty(
        type=ACA_data_template,
        name="古建场景资产集"
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

# 更新建筑，但不重设柱网
def update_building(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildFloor
        funproxy = partial(
                buildFloor.buildFloor,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
    return
    
# 更新建筑，但不重设柱网
def reset_building(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return

    # 直接调用operator，并且调用invoke，弹出确认提示
    # https://docs.blender.org/api/current/bpy.types.Operator.html#invoke-function
    bpy.ops.aca.reset_floor('INVOKE_DEFAULT')

# 更新院墙
def update_yardwall(self, context:bpy.types.Context):
    bpy.ops.aca.build_yardwall()
    return

def update_platform(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 调用台基缩放
        from . import buildPlatform
        # buildPlatform.resizePlatform(buildingObj)
        funproxy = partial(
                buildPlatform.resizePlatform,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
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
        # buildFloor.buildPillers(buildingObj)
        funproxy = partial(
                buildFloor.buildPillers,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
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
        # buildFloor.resizePiller(buildingObj)
        funproxy = partial(
                buildFloor.resizePiller,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated piller failed, context should be pillerObj")
    return

def update_wall(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        if odata.aca_type == con.ACA_TYPE_WALL:
            # 仅重新生成当前墙体
            from . import buildWall
            funproxy = partial(buildWall.buildSingleWall,
                               wallproxy=context.object)
            utils.fastRun(funproxy)
        else:
            # 重新生成墙体
            from . import buildWall
            funproxy = partial(buildWall.buildWallLayout,
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
        funproxy = partial(
            buildDougong.buildDougong,
            buildingObj=buildingObj)
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
        funproxy = partial(
            buildDougong.update_dgHeight,
            buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

def update_roof(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bData,oData = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildRoof
        # 重新生成屋顶
        funproxy = partial(
            buildRoof.buildRoof,
            buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

# 用户修改屋顶类型时的回调
def update_roofstyle(self, context:bpy.types.Context):
    buildingObj,bData,oData = utils.getRoot(context.object)
    # 庑殿、歇山不可以不做飞椽
    if bData.roof_style in (
        con.ROOF_WUDIAN,
        con.ROOF_XIESHAN,
        con.ROOF_LUDING,
    ):
        bData['use_flyrafter'] = True
    return

def update_rooftile(self, context:bpy.types.Context):
    # 确认选中为building节点
    buildingObj,bData,oData = utils.getRoot(context.object)
    if buildingObj != None:
        from . import buildRooftile
        # 重新生成屋顶
        funproxy = partial(
            buildRooftile.buildTile,
            buildingObj=buildingObj)
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
            precision=3,
            description="比例模数(m)，清官式常用0.08(二寸半)、0.096(三寸)等",
            update = update_building
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
            precision=3,
            update = update_platform # 绑定回调
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name = "台基下出",
            precision=3,
            min = 0.01, 
            update = update_platform    # 绑定回调
        ) # type: ignore
    step_net : bpy.props.StringProperty(
            name = "保存的踏跺列表"
        )# type: ignore
    
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
            precision=3,
            update = update_building
        )# type: ignore
    x_2 : bpy.props.FloatProperty(
            name = "次间宽度",
            min = 0, 
            precision=3,
            update = update_building
        )# type: ignore
    x_3 : bpy.props.FloatProperty(
            name = "梢间宽度",
            min = 0, 
            precision=3,
            update = update_building
        )# type: ignore
    x_4 : bpy.props.FloatProperty(
            name = "尽间宽度",
            min = 0, 
            precision=3,
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
            precision=3,
            update = update_building
        )# type: ignore
    y_2 : bpy.props.FloatProperty(
            name = "次间深度",
            min = 0, 
            precision=3,
            update = update_building
        )# type: ignore
    y_3 : bpy.props.FloatProperty(
            name = "梢间深度",
            min = 0, 
            precision=3,
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
    piller_height : bpy.props.FloatProperty(
            name = "柱高",
            default = 0.0,
            min = 0.01, 
            precision=3,
            update = update_building,
        )# type: ignore
    piller_diameter : bpy.props.FloatProperty(
            name = "柱径",
            default = 0.0,
            min = 0.01, 
            precision=3,
            # update = update_piller
            update = update_building,
        )# type: ignore
    use_smallfang: bpy.props.BoolProperty(
            default=False,
            name="小额枋",
            update = update_building
        )# type: ignore 
    
    
    # 墙体属性
    wall_layout : bpy.props.EnumProperty(
            name = "装修布局",
            description = "装修布局",
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
                ("0","",""),
                ("1","槛墙",""),
                ("2","隔扇",""),
                ("3","槛窗",""),
            ],
        ) # type: ignore
    wall_deepth : bpy.props.FloatProperty(
            name="墙厚度",
            default=1.0,
            min=0.1,
            max=2,
            update = update_wall
        )# type: ignore
    wall_span : bpy.props.FloatProperty(
            name="墙体顶部间隔",
            default=0,
            description='重檐时，装修不做到柱头，用走马板填充'
        )# type: ignore 
    # 隔扇属性
    door_height : bpy.props.FloatProperty(
            name="中槛高度",
            update = update_wall
        )# type: ignore 
    door_num : bpy.props.IntProperty(
            name="隔扇数量",
            default=4, max=6,step=2,min=2,
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
    dg_extend : bpy.props.FloatProperty(
            name="斗栱挑檐",    # 令拱出跳距离
            default=0.45,
            min=0.01,
            precision=3,
            update = update_dgHeight,
        )# type: ignore 
    dg_height : bpy.props.FloatProperty(
            name="斗栱高度",    # 取挑檐桁下皮高度
            default=1.0,
            precision=3,
        )# type: ignore 
    dg_scale:bpy.props.FloatVectorProperty(
            name="斗栱缩放",    # 斗栱缩放
            default=(1,1,1),
            precision=3,
        )# type: ignore 
    dg_gap:bpy.props.FloatProperty(
            name="斗栱间距",    # 斗栱间距
            default=0.99,
            precision=3,
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
                ("5","悬山卷棚顶",""),
                ('6','盝顶',''),
            ],
            #update = update_roof,
            update = update_roofstyle,
        ) # type: ignore
    rafter_count : bpy.props.IntProperty(
            name="椽架数量",
            default=8,
            min=0,max=10,
            #update = update_roof,
        )# type: ignore 
    use_flyrafter :  bpy.props.BoolProperty(
            default=True,
            name="使用飞椽",
            #update = update_roof,
        )# type: ignore 
    use_wangban :  bpy.props.BoolProperty(
            default=True,
            name="添加望板",
            #update = update_roof,
        )# type: ignore 
    qiqiao: bpy.props.IntProperty(
            name="起翘(椽径倍数)",
            default=4, 
            #update=update_roof
        )# type: ignore 
    chong: bpy.props.IntProperty(
            name="出冲(椽径倍数)",
            default=3, 
            #update=update_roof
        )# type: ignore 
    shengqi: bpy.props.IntProperty(
            name="生起(椽径倍数)",
            default=1, 
            #update=update_roof
        )# type: ignore 
    tuishan: bpy.props.FloatProperty(
            name="推山系数", 
            default=0.9,
            min=0.1,
            max=1.0,
            precision=3,
            description="庑殿顶两山坡度的调整系数，标准值为0.9，设置为1.0即不做推山"
        )# type: ignore
    shoushan: bpy.props.FloatProperty(
            name="收山尺寸", 
            default=2,
            min=0,
            max=2,
            precision=3,
            description="歇山顶的山面内返的距离(米)，建议取一桁径以上，不超过一步架"
        )# type: ignore
    luding_rafterspan:bpy.props.FloatProperty(
            name="盝顶檐步架宽", 
            default=3,
            min=0,
            max=6,
            precision=3,
            description="盝顶檐步架宽度，用于重檐时，请设置为上下层面阔/进深收分的距离"
        )# type: ignore
    juzhe : bpy.props.EnumProperty(
            name = "举折系数",
            items = [
                ("0","   举折系数：默认","[0.5,0.7,0.8,0.9]"),
                ("1","   举折系数：陡峭","[0.5,1,1.5,2]，慎用，一般用于亭子等建筑"),
                ("2","   举折系数：平缓","[0.5,0.65,0.75,0.9]"),
            ],
        ) # type: ignore
    roof_qiao_point : bpy.props.FloatVectorProperty(
        name="翼角起翘参考点",
        subtype='XYZ',
        unit='LENGTH',
        )# type: ignore 
    
    # 瓦作属性
    tile_width : bpy.props.FloatProperty(
            name="瓦垄宽度", 
            default=0.4,
            min=0.0,
            precision=3,
        )# type: ignore
    tile_width_real : bpy.props.FloatProperty(
            name="瓦垄实际宽度", 
            precision=3,
        )# type: ignore
    tile_length : bpy.props.FloatProperty(
            name="瓦片长度", 
            default=0.4,
            min=0.0,
            precision=3,
        )# type: ignore
    
    # 屋脊属性
    paoshou_count:bpy.props.IntProperty(
            name = '跑兽数量',
            default=6,
            min=0,
            max=10,
            update=update_rooftile
        )# type: ignore 
    
    # 院墙属性
    is_4_sides:bpy.props.BoolProperty(
            default = True,
            name = "是否做四面墙",
        ) # type: ignore
    yard_width :bpy.props.FloatProperty(
            name="庭院面阔",
            default=40,
            min=1,
            update=update_yardwall,
        )# type: ignore 
    yard_deepth :bpy.props.FloatProperty(
            name="庭院进深",
            default=30,
            min=1,
            update=update_yardwall,
        )# type: ignore
    yardwall_height:bpy.props.FloatProperty(
            name="院墙高度",
            default=3,
            min=1,
            update=update_yardwall,
        )# type: ignore
    yardwall_deepth:bpy.props.FloatProperty(
            name="院墙厚度",
            default=1,
            min=0.5,
            update=update_yardwall,
        )# type: ignore
    yardwall_angle:bpy.props.FloatProperty(
            name="院墙帽瓦斜率",
            default=30,
            min=0,
            max=45,
            update=update_yardwall,
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
    is_auto_redraw : bpy.props.BoolProperty(
            default = True,
            name = "是否实时重绘"
        ) # type: ignore
    is_auto_rebuild : bpy.props.BoolProperty(
            default = True,
            name = "是否实时重建"
        ) # type: ignore
    template : bpy.props.EnumProperty(
            name = "模版列表",
            description = "模板列表",
            items = getTemplateList,
            options = {"ANIMATABLE"},
        ) # type: ignore

# 全局共用的模版信息，各个建筑都进行引用
# 包括资产库资产引用等    
class ACA_data_template(bpy.types.PropertyGroup):
    # 材质对象
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
            name = "漆.土朱材质",
            type = bpy.types.Object,
        )# type: ignore 
    mat_gold:bpy.props.PointerProperty(
            name = "漆.金",
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_1:bpy.props.PointerProperty(
            name = "方砖缦地",
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_2:bpy.props.PointerProperty(
            name = "条砖竖铺",
            type = bpy.types.Object,
        )# type: ignore 
    mat_brick_3:bpy.props.PointerProperty(
            name = "条砖横铺",
            type = bpy.types.Object,
        )# type: ignore 
    mat_dust_red:bpy.props.PointerProperty(
            name = "抹灰.红",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam :bpy.props.PointerProperty(
            name = "梁枋彩画",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_alt :bpy.props.PointerProperty(
            name = "梁枋彩画.异色",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_pillerhead :bpy.props.PointerProperty(
            name = "柱头贴图",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_walkdragon :bpy.props.PointerProperty(
            name = "平板枋.行龙",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_grasscouple :bpy.props.PointerProperty(
            name = "垫板.公母草",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_dgfillboard :bpy.props.PointerProperty(
            name = "栱垫板",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_rafter : bpy.props.PointerProperty(
            name = "檐椽贴图",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_flyrafter : bpy.props.PointerProperty(
            name = "飞椽贴图",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_wangban: bpy.props.PointerProperty(
            name = "望板着色",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_cloud: bpy.props.PointerProperty(
            name = "工王云",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_tuanend: bpy.props.PointerProperty(
            name = "端头坐龙",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_ccb : bpy.props.PointerProperty(
            name = "子角梁",
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_door : bpy.props.PointerProperty(
            name = "裙板",
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_doorring : bpy.props.PointerProperty(
            name = "绦环板",
            type = bpy.types.Object,
        )# type: ignore
    mat_paint_shanhua : bpy.props.PointerProperty(
            name = "山花板",
            type = bpy.types.Object,
        )# type: ignore
    mat_geshanxin : bpy.props.PointerProperty(
            name = "三交六椀隔心",
            type = bpy.types.Object,
        )# type: ignore
    
    
    # 柱对象
    piller_source : bpy.props.PointerProperty(
            name = "柱样式",
            type = bpy.types.Object,
        )# type: ignore
    pillerbase_source : bpy.props.PointerProperty(
            name = "柱础样式",
            type = bpy.types.Object,
        )# type: ignore
    
    # 棂心对象
    lingxin_source:bpy.props.PointerProperty(
            name = "棂心",
            type = bpy.types.Object,
            poll = p_filter,
            update = update_wall
        )# type: ignore 
    
    # 斗栱对象
    dg_piller_source:bpy.props.PointerProperty(
            name = "柱头斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_fillgap_source:bpy.props.PointerProperty(
            name = "补间斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    dg_fillgap_alt_source:bpy.props.PointerProperty(
            name = "补间斗栱-异色",
            type = bpy.types.Object,
        )# type: ignore 
    dg_corner_source:bpy.props.PointerProperty(
            name = "转角斗栱",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 博缝板对象
    bofeng_source : bpy.props.PointerProperty(
            name = "博缝板",
            type = bpy.types.Object,
        )# type: ignore
    
    # 老角梁对象
    cornerbeam_source : bpy.props.PointerProperty(
            name = "老角梁",
            type = bpy.types.Object,
        )# type: ignore
    
    # 霸王拳对象
    bawangquan_source : bpy.props.PointerProperty(
            name = "霸王拳",
            type = bpy.types.Object,
        )# type: ignore
    
    # 琉璃瓦对象
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
    
    # 屋脊对象
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
    baoding_source:bpy.props.PointerProperty(
            name = "宝顶",
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
    
    # 跑兽对象
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