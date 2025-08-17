# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构
#   绑定面板控件
#   触发控件数据更新

import bpy
import time 
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

    # 用于模板缩略图控件的载入
    from . import template
    bpy.types.Scene.image_browser_items = bpy.props.CollectionProperty(
        type=TemplateThumbItem)
    bpy.types.Scene.image_browser_enum = bpy.props.EnumProperty(
        name="Images",
        items=template.getThumbEnum,
        update=updateSelectedTemplate,
    )
    return

# 销毁自定义属性
def delprop():
    del bpy.types.Scene.ACA_data
    del bpy.types.Object.ACA_data
    
    # 用于模板缩略图控件的载入
    del bpy.types.Scene.image_browser_items
    del bpy.types.Scene.image_browser_enum

# # 筛选资产目录
# def p_filter(self, object:bpy.types.Object):
#     # 仅返回Assets collection中的对象
#     return object.users_collection[0].name == 'Assets'

# 更新建筑，但不重设柱网
def update_building(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return

    # 根据数据集合，找到对应的建筑
    # 在panel中指定bData时，指向context.object,
    # 在panel中指定为mData时，指向主建筑
    buildingObj = self.id_data
    if buildingObj != None:
        bpy.ops.aca.update_building(buildingName=buildingObj.name)
    else:
        utils.popMessageBox("更新建筑失败")
    return
    
# 更新建筑，但不重设柱网
def reset_building(self, context:bpy.types.Context):
    # 这里是重要修改，无论自动开关是否开启，都应该立即执行
    # # 判断自动重建开关
    # isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    # if not isRebuild:
    #     return

    # 根据数据集合，找到对应的建筑
    # 在panel中指定bData时，指向context.object,
    # 在panel中指定为mData时，指向主建筑
    buildingObj = self.id_data

    if buildingObj != None:
        # 直接调用operator，并且调用invoke，弹出确认提示
        # https://docs.blender.org/api/current/bpy.types.Operator.html#invoke-function
        bpy.ops.aca.reset_floor('INVOKE_DEFAULT',
            buildingName = buildingObj.name)
    else:
        utils.popMessageBox("重设柱网失败")

# 更新院墙
def update_yardwall(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    bpy.ops.aca.build_yardwall()
    return

def update_platform(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 从self属性找到对应的Object，用self.id_data
    # https://blender.stackexchange.com/questions/145245/how-to-access-object-instance-from-property-instance-in-update-callback
    refObj = self.id_data
    
    # 调用台基缩放
    from . import buildPlatform
    # buildPlatform.resizePlatform(buildingObj)
    funproxy = partial(
            buildPlatform.resizePlatform,
            buildingObj=refObj)
    utils.fastRun(funproxy)

    return

# 仅更新柱体样式，不触发其他重建
def update_PillerStyle(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
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
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return

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

def update_topwin(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 联动计算door_height
    dk = self.DK
    # pd = con.PILLER_D_EAVE*dk

    # # use_topwin与topwin_height联动
    # # 最初设计让用户勾选use_topwin
    # # 后来设计用户直接输入topwin_height，如果输入0就自动不使用横披窗
    # if self.topwin_height < 0.0001:
    #     self.use_topwin = False
    # else:
    #     self.use_topwin = True

    # # 从柱高开始倒推
    # doorHeight = self.piller_height
    # # 大额枋
    # doorHeight -= con.EFANG_LARGE_H*dk
    # # 小额枋和由额垫板
    # if self.use_smallfang:
    #     doorHeight -= (con.EFANG_SMALL_H*dk
    #                    + con.BOARD_YOUE_H*dk)
    # # 下槛和上槛
    # doorHeight -= (con.KAN_DOWN_HEIGHT*pd  # 下槛
    #                + con.KAN_UP_HEIGHT*pd   # 中槛
    #               )
    # # 中槛和横披窗
    # if self.use_topwin:
    #     doorHeight -= (con.KAN_MID_HEIGHT*pd
    #                    + self.topwin_height)
    # # 走马板
    # if self.wall_span > 0.00001:
    #     doorHeight -= self.wall_span
    
    # # 计算中槛中心Z高度
    # midkan_z = (con.KAN_DOWN_HEIGHT*pd
    #             + doorHeight
    #             + con.KAN_MID_HEIGHT*pd/2)
    # # 存入door_height
    # self['door_height'] = midkan_z

    # 250225 因为需要同时考虑外檐装修和內檐装修
    # 所以以上通过檐柱高倒推无法满足內檐装修的计算
    # 所以，固定为与穿插枋下皮对齐
    # (简化处理，上槛中线对齐大额枋底皮)
    # 上槛和穿插枋高度可能不同，存在误差
    self['door_height'] = (self.piller_height
                -con.EFANG_LARGE_H*dk)

    # 继续调用墙体更新
    update_wall(self, context)
    return

def update_wall(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 从self属性找到对应的Object，用self.id_data
    # https://blender.stackexchange.com/questions/145245/how-to-access-object-instance-from-property-instance-in-update-callback
    refObj = self.id_data

    from . import buildWall
    # 更新全局的墙体
    if self.aca_type == con.ACA_TYPE_BUILDING:
        funproxy = partial(buildWall.buildWallLayout,
                         buildingObj=refObj)
    # 更新个体的墙体
    elif self.aca_type in (
                con.ACA_TYPE_WALL,              # 槛墙
                con.ACA_WALLTYPE_WINDOW,        # 槛窗
                con.ACA_WALLTYPE_GESHAN,        # 隔扇
                con.ACA_WALLTYPE_BARWINDOW,     # 直棂窗
                con.ACA_WALLTYPE_MAINDOOR,      # 板门
                con.ACA_WALLTYPE_FLIPWINDOW,    # 支摘窗
            ):
        funproxy = partial(buildWall.updateWall,
                                wallObj=refObj)
    utils.fastRun(funproxy)

    return

# 刷新斗栱布局
def update_dougong(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 确认选中为building节点
    buildingObj,bData,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 250813 禁用以下处理
        # 1、在重檐建筑中，如果修改上檐斗栱，导致重檐抬升计算错误
        # 2、因为这里抢先用上檐柱头科替换掉了aData.dg_piller_source
        # 从而导致buildCombo.__getDoubleEaveLift时获取了错误的dg_extend
        # 3、同时，在buildDougong.__buildDougong中已经调用了updateDougongData，
        # 所以，这里直接禁用掉，目前看起来没有问题
        # 以观后效
        # -------------
        # # 初始化斗栱数据，避免跨建筑时公用的aData干扰
        # from . import template
        # template.updateDougongData(buildingObj)
        
        # 241125 修改斗栱时，涉及到柱高的变化，最好是全屋更新
        from . import build
        funproxy = partial(
                build.updateBuilding,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated dougong failed, context.object should be buildingObj")
    return

def update_juzhe(self, context:bpy.types.Context):
    # 如果为3-自定义屋架高度时，不触发刷新
    if self.juzhe != '3':
        update_roof(self,context)
    return

def update_roof(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 手动将操作添加到撤销栈
    bpy.ops.ed.undo_push(message="Float Property Update")
    
    # 确认选中为building节点
    buildingObj,bData,oData = utils.getRoot(context.object)
    if buildingObj != None:
        from . import build
        # 重新生成屋顶
        funproxy = partial(
            build.resetRoof,
            buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated platform failed, context.object should be buildingObj")
    return

# 用户修改屋顶类型时的回调
def update_roofstyle(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    buildingObj,bData,oData = utils.getRoot(context.object)
    # 庑殿、歇山不可以不做飞椽
    if bData.roof_style in (
        con.ROOF_WUDIAN,
        con.ROOF_XIESHAN,
        con.ROOF_XIESHAN_JUANPENG,
        con.ROOF_LUDING,
    ):
        bData['use_flyrafter'] = True
    return

def update_rooftile(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
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
        utils.outputMsg(
            "updated rooftile failed, context.object should be buildingObj")
    return

# 显示/隐藏台基层
def hide_platform(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_BASE,
        self.is_showPlatform)

# 显示/隐藏柱网层
def hide_pillers(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_PILLER,
        self.is_showPillers)

# 显示/隐藏装修层
def hide_walls(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_WALL,
        self.is_showWalls)

# 显示/隐藏斗栱层
def hide_dougong(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_DOUGONG,
        self.is_showDougong)

# 显示/隐藏梁架层
def hide_beam(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_BEAM,
        self.is_showBeam)

# 显示/隐藏椽架层
def hide_rafter(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_RAFTER,
        self.is_showRafter)

# 显示/隐藏瓦作层
def hide_tiles(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_TILE,
        self.is_showTiles)
    utils.hideLayer(
        buildingObj,con.COLL_NAME_BOARD,
        self.is_showTiles)

# 使用动态enumproperty时，必须声明全局变量持久化返回的回调数据
# https://docs.blender.org/api/current/bpy.props.html
# Warning
# There is a known bug with using a callback, 
# Python must keep a reference to the strings 
# returned by the callback or Blender will 
# misbehave or even crash.
dougongList = []
def getDougongList(self, context):
    from . import template
    global dougongList
    dougongList = template.getDougongList()
    return dougongList

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
    combo_type : bpy.props.StringProperty(
            name = '组合类型',
            default = 'combo_main',
        ) # type: ignore
    template_name : bpy.props.StringProperty(
            name = '模板名称'
        ) #type: ignore
    root_location : bpy.props.FloatVectorProperty(
            name = '根节点位移',
        ) # type: ignore
    root_rotation : bpy.props.FloatVectorProperty(
            name = '根节点旋转',
        ) # type: ignore
    DK: bpy.props.FloatProperty(
            name = "斗口",
            default=0.0,
            min=0.016,
            max=0.16,
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
    is_showBeam: bpy.props.BoolProperty(
            default = True,
            name = "是否显示梁架",
            update=hide_beam
        ) # type: ignore
    is_showRafter: bpy.props.BoolProperty(
            default = True,
            name = "是否显示椽望",
            update=hide_rafter
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
            update = update_platform, # 绑定回调
            description="一般为柱高的1/5，或2柱径",
        ) # type: ignore
    platform_extend : bpy.props.FloatProperty(
            name = "台基下出",
            precision=3,
            min = 0.01, 
            update = update_platform,    # 绑定回调
            description="檐柱的2.4倍，或上出檐的3/4~4/5",
        ) # type: ignore
    step_net : bpy.props.StringProperty(
            name = "保存的踏跺列表"
        )# type: ignore
    use_terrace: bpy.props.BoolProperty(
            default = False,
            name = "是否有月台",
        ) # type: ignore
    
    # 柱网对象属性
    x_total : bpy.props.FloatProperty(
            name = "通面阔",
            precision=3,
        )# type: ignore
    y_total : bpy.props.FloatProperty(
            name = "通进深",
            precision=3,
        )# type: ignore
    x_rooms : bpy.props.IntProperty(
            name = "面阔间数",
            min = 1, 
            # max = 11,
            step = 2,
            update= reset_building,
            description="必须为奇数，建议最多不超过11间",
        )# type: ignore
    x_1 : bpy.props.FloatProperty(
            name = "明间宽度",
            min = 0, 
            precision=3,
            update = update_building,
            description="常取7攒斗栱，且一般柱不越间广（柱高小于明间宽度）",
        )# type: ignore
    x_2 : bpy.props.FloatProperty(
            name = "次间宽度",
            min = 0, 
            precision=3,
            update = update_building,
            description="常取6攒斗栱",
        )# type: ignore
    x_3 : bpy.props.FloatProperty(
            name = "梢间宽度",
            min = 0, 
            precision=3,
            update = update_building,
            description="可以与次间宽度相同",
        )# type: ignore
    x_4 : bpy.props.FloatProperty(
            name = "尽间宽度",
            min = 0, 
            precision=3,
            update = update_building,
            description="如果做四面廊，一般取2攒斗栱",
        )# type: ignore
    y_rooms : bpy.props.IntProperty(
            name = "进深间数",
            #max = 5,
            min = 1, 
            update = reset_building,
            description="根据通进深的需要，以及是否做前后廊，可以为偶数",
        )# type: ignore
    y_1 : bpy.props.FloatProperty(
            name = "明间深度",
            min = 0, 
            precision=3,
            update = update_building,
            description="需综合考虑步架进行设计",
        )# type: ignore
    y_2 : bpy.props.FloatProperty(
            name = "次间深度",
            min = 0, 
            precision=3,
            update = update_building,
            description="需综合考虑步架进行设计",
        )# type: ignore
    y_3 : bpy.props.FloatProperty(
            name = "梢间深度",
            min = 0, 
            precision=3,
            update = update_building,
            description="需综合考虑步架进行设计",
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
            name = "檐柱高",
            default = 0.0,
            min = 0.01, 
            precision=3,
            update = update_building,
            description="有斗拱的取57-60斗口，无斗拱的取面阔的8/10",
        )# type: ignore
    piller_diameter : bpy.props.FloatProperty(
            name = "檐柱径",
            default = 0.0,
            min = 0.01, 
            precision=3,
            # update = update_piller
            update = update_building,
            description="有斗拱的取6斗口，无斗拱的取1/10柱高",
        )# type: ignore
    use_smallfang: bpy.props.BoolProperty(
            default=False,
            name="双重额枋",
            update = update_building,
            description="同时使用大额枋、由额垫板、小额枋的三件套连接两根柱",
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
    wall_depth : bpy.props.FloatProperty(
            name="墙厚度",
            default=1.0,
            precision=3,
            min=0.1,
            max=2,
            update = update_wall
        )# type: ignore
    wall_span : bpy.props.FloatProperty(
            name="走马板高度",
            default=0,
            min=0,
            precision=3,
            description='重檐时，装修不做到柱头，用走马板填充，输入0则不做走马板',
            update = update_wall,
        )# type: ignore 
    doorFrame_width_per : bpy.props.FloatProperty(
            name="门口宽比",
            default=1,
            max=1,
            min=0.1,
            precision=3,
            description='开间中的门口/窗口宽度比例，小于1则开间的部分做余塞板，不可大于1',
            update = update_wall,
        )# type: ignore 
    doorFrame_height : bpy.props.FloatProperty(
            name="门口高度",
            default=3,
            min=0.1,
            precision=3,
            description='开间中的门口高度，小于柱高的空间将自动布置横披窗/迎风板',
            update = update_wall,
        )# type: ignore 
    # 隔扇属性
    door_num : bpy.props.IntProperty(
            name="隔扇数量",
            default=4, max=6,step=2,min=2,
            update = update_wall,
            description="一般做4扇隔扇",
        )# type: ignore 
    gap_num : bpy.props.IntProperty(
            name="抹头数量",
            default=5,min=2,max=6,
            update = update_wall,
            description="2~6抹头都可以，根据需要自由设置",
        )# type: ignore 
    use_topwin: bpy.props.BoolProperty(
            default=True,
            name="添加横披窗",
            description="在隔扇上方的固定窗户,仅在金柱加高的內檐装修中有效",
            update = update_topwin,
        )# type: ignore 
    door_height : bpy.props.FloatProperty(
            name="中槛高度",
            precision=3,
            update = update_wall,
            description="中槛中线到台面上皮的高度",
        )# type: ignore 
    door_ding_num : bpy.props.IntProperty(
            name="门钉数量",
            default=5,
            min=0,max=9,
            update = update_wall,
            description="门钉的路数，最大9路，取0时不做门钉",
        )# type: ignore 
    topwin_height : bpy.props.FloatProperty(
            name="横披窗高度",
            default=0,
            precision=3,
            update = update_topwin,
            description="横披窗（棂心）的高度，输入0则不做横披窗",
        )# type: ignore 
    use_KanWall: bpy.props.BoolProperty(
            default=False,
            name="添加槛墙"
        )# type: ignore 
    paint_style : bpy.props.EnumProperty(
            name = "彩画样式",
            description = "可以切换清和玺等彩画样式",
            items = [
                ("0","清-和玺彩画",""),
                ("1","酱油色",""),
                ("2","白模",""),
            ],
            update = update_building,
            options = {"ANIMATABLE"}
        ) # type: ignore
    
    # 斗栱属性
    use_dg :  bpy.props.BoolProperty(
            default=False,
            name="使用斗栱",
            update=update_dougong,
            description="小式建筑可以不使用斗栱，大梁直接坐在柱头",
        )# type: ignore 
    use_pingbanfang: bpy.props.BoolProperty(
            default=True,
            name="使用平板枋",
            update=update_dougong,
            description="在柱头和斗栱之间的一层垫板，明清式建筑一般都会使用",
        )# type: ignore 
    dg_style : bpy.props.EnumProperty(
            name = "斗栱类型",
            description = "根据建筑等级的不同，斗栱有严格的限制",
            items = getDougongList,
            options = {"ANIMATABLE"},
            update=update_dougong,
            default=0,
        ) # type: ignore
    dg_extend : bpy.props.FloatProperty(
            name="斗栱挑檐",    # 令拱出跳距离
            default=0.45,
            description = "斗栱出跳由斗栱模板预先定义，不可修改",
            min=0.01,
            precision=3,
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
    dk_scale:bpy.props.FloatProperty(
            name="斗口放大",    # 斗栱间距
            description = "为了模仿唐宋建筑风格，可以放大斗栱",
            default=1,
            precision=3,
            min=1,
            max=2.5,
            update=update_dougong,
        )# type: ignore 
    dg_gap:bpy.props.FloatProperty(
            name="斗栱间距",    # 斗栱间距
            description = "一般取11斗口",
            default=0.99,
            precision=3,
            min=0.1,
            update=update_dougong,
        )# type: ignore 
    
    # 屋顶属性
    roof_style : bpy.props.EnumProperty(
            name = "屋顶类型",
            items = [
                ("0","",""),
                ("1","庑殿顶",""),
                ("2","歇山顶",""),
                ("3","悬山顶",""),
                ("4","硬山顶",""),
                ('5',"盝顶",""),
                ("6","悬山卷棚顶",""),
                ('7',"硬山卷棚顶",""),
                ('8','歇山卷棚顶',""),
            ],
            #update = update_roof,
            update = update_roofstyle,
            description="请选择一种屋顶样式",
        ) # type: ignore
    use_double_eave: bpy.props.BoolProperty(
            default=False,
            name="使用重檐",
            update = update_roof,
            description="使用重檐形式的屋顶",
        )# type: ignore 
    use_hallway : bpy.props.BoolProperty(
            default=False,
            name="做廊步架",
            update = update_building,
            description="在前后廊和周围廊做法时，升高金柱到下金桁高度",
        )# type: ignore 
    rafter_count : bpy.props.IntProperty(
            name="步架数量",
            default=8,
            min=2,max=9,
            update = update_roof,
            description="以通进深除以22斗口来估算，过大过小会有很多潜在问题",
        )# type: ignore 
    use_flyrafter :  bpy.props.BoolProperty(
            default=True,
            name="使用飞椽",
            update = update_roof,
            description="小式的硬山、悬山可以不做飞椽，但四坡面必须使用飞椽做翼角",
        )# type: ignore 
    use_wangban :  bpy.props.BoolProperty(
            default=True,
            name="添加望板",
            update = update_roof,
            description="可以不做望板，更直观的查看屋顶结构",
        )# type: ignore 
    qiqiao: bpy.props.FloatProperty(
            name="起翘(椽径倍数)",
            default=4, 
            min=0,
            update=update_roof,
            description="常做4椽起翘，也可以视情况适当增加",
        )# type: ignore 
    chong: bpy.props.FloatProperty(
            name="出冲(椽径倍数)",
            default=3,
            min=0, 
            update=update_roof,
            description="常做3椽出冲，也可以视情况适当增加",
        )# type: ignore 
    use_pie: bpy.props.BoolProperty(
            name="使用撇",
            default=True,
            update=update_roof,
            description="翼角翘飞椽可以选择是否做官式的撇向做法，起翘夸张的非官式做法建议关闭",
    )# type: ignore
    shengqi: bpy.props.IntProperty(
            name="生起(椽径倍数)",
            default=1, 
            update=update_roof
        )# type: ignore 
    liangtou: bpy.props.FloatProperty(
            name="梁头位置", 
            default=0.4,
            min=0,
            max=1.0,
            precision=3,
            update = update_roof,
            description="老梁头压挑檐桁的尺度，建议在0.5左右，可根据起翘形态适当调整"
        )# type: ignore
    tuishan: bpy.props.FloatProperty(
            name="推山系数", 
            default=0.9,
            min=0.1,
            max=1.0,
            precision=3,
            update = update_roof,
            description="庑殿顶两山坡度的调整系数，标准值为0.9，设置为1.0即不做推山"
        )# type: ignore
    shoushan: bpy.props.FloatProperty(
            name="收山尺寸", 
            default=2,
            min=0,
            max=2,
            precision=3,
            update = update_roof,
            description="歇山顶的山花板从檐檩中向内移动的距离(米)，一般为1檩径(4斗口)，最大不超过檐步架"
        )# type: ignore
    luding_rafterspan:bpy.props.FloatProperty(
            name="盝顶檐步架宽", 
            default=3,
            min=0.01,
            max=6,
            precision=3,
            update = update_roof,
            description="盝顶檐步架宽度，用于重檐时，请设置为上下层面阔/进深收分的距离"
        )# type: ignore
    juzhe : bpy.props.EnumProperty(
            name = "举折系数",
            items = [
                ("0","   举折系数：默认","[0.5,0.7,0.8,0.9]"),
                ("1","   举折系数：陡峭","[0.5,1,1.5,2]，慎用，一般用于亭子等建筑"),
                ("2","   举折系数：平缓","[0.5,0.65,0.75,0.9]"),
                ("3","   举折系数：按屋架高度推算","根据输入屋架高度，进行举折计算")
            ],
            description="决定了屋面坡度的曲率",
            update = update_juzhe,
        ) # type: ignore
    roof_height:bpy.props.FloatProperty(
            name="屋架高度", 
            default=3,
            min=0.01,
            max=10,
            precision=3,
            update = update_roof,
            description="从正心桁到脊桁的垂直高度"
        )# type: ignore
    roof_qiao_point : bpy.props.FloatVectorProperty(
        name="翼角起翘参考点",
        subtype='XYZ',
        unit='LENGTH',
        )# type: ignore 
    
    # 瓦作属性
    # 250616 添加瓦作缩放因子
    tile_scale:bpy.props.FloatProperty(
            name="瓦作缩放",    # 瓦作缩放
            default=1.0,
            min=0.5,max=2.0,
            precision=2,
            description="放大或缩小瓦作的比例，默认1.0",
            update = update_building,
        )# type: ignore
    tile_color : bpy.props.EnumProperty(
            name = "瓦面颜色",
            items = [
                ("0","黄琉璃",""),
                ("1","绿琉璃",""),
                ("2","灰琉璃",""),
                ("3","蓝琉璃",""),
                ("4","紫琉璃",""),
            ],
        ) # type: ignore
    tile_alt_color : bpy.props.EnumProperty(
            name = "剪边颜色",
            items = [
                ("0","黄琉璃",""),
                ("1","绿琉璃",""),
                ("2","灰琉璃",""),
                ("3","蓝琉璃",""),
                ("4","紫琉璃",""),
            ],
        ) # type: ignore
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
            update=update_rooftile,
            description="包括骑鸡仙人的数量",
        )# type: ignore 
    
    # 院墙属性
    is_4_sides:bpy.props.BoolProperty(
            default = True,
            name = "是否做四面墙",
            description="同时生成四面合围的墙体，转角处将做45度拼接",
        ) # type: ignore
    yard_width :bpy.props.FloatProperty(
            name="庭院面阔",
            default=40,
            precision=3,
            min=1,
            description="围墙的长度",
            update=update_yardwall,
        )# type: ignore 
    yard_depth :bpy.props.FloatProperty(
            name="庭院进深",
            default=30,
            precision=3,
            min=1,
            description="仅在四面合围墙体时设置",
            update=update_yardwall,
        )# type: ignore
    yardwall_height:bpy.props.FloatProperty(
            name="院墙高度",
            default=3,
            precision=3,
            min=1,
            description="院墙高度，不含帽瓦",
            update=update_yardwall,
        )# type: ignore
    yardwall_depth:bpy.props.FloatProperty(
            name="院墙厚度",
            default=1,
            precision=3,
            min=0.5,
            description="院墙厚度，不含帽瓦",
            update=update_yardwall,
        )# type: ignore
    yardwall_angle:bpy.props.FloatProperty(
            name="院墙帽瓦斜率",
            default=30,
            precision=3,
            min=0,
            max=45,
            description="帽瓦斜率，一般可维持30度",
            update=update_yardwall,
        )# type: ignore  
    
# 全局共用的模板信息，各个建筑都进行引用
# 包括资产库资产引用等    
class ACA_data_template(bpy.types.PropertyGroup):
    # 材质对象
    mat_override:bpy.props.PointerProperty(
            name = "UVgrid",
            type = bpy.types.Object,
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
    mat_oilpaint:bpy.props.PointerProperty(
            name = "漆.通用",
            type = bpy.types.Object,
        )# type: ignore 
    mat_gold:bpy.props.PointerProperty(
            name = "漆.金",
            type = bpy.types.Object,
        )# type: ignore 
    mat_green:bpy.props.PointerProperty(
            name = "漆.绿",
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
    mat_dust_wall:bpy.props.PointerProperty(
            name = "墙体抹灰",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_big :bpy.props.PointerProperty(
            name = "梁枋彩画.大额枋",
            type = bpy.types.Object,
        )# type: ignore 
    mat_paint_beam_small :bpy.props.PointerProperty(
            name = "梁枋彩画.小额枋",
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
    mat_paint_dgfillboard_s :bpy.props.PointerProperty(
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
    mat_geshanxin_wan : bpy.props.PointerProperty(
            name = "万字锦棂心",
            type = bpy.types.Object,
        )# type: ignore    
    mat_ccfang : bpy.props.PointerProperty(
            name = "穿插枋",
            type = bpy.types.Object,
        )# type: ignore  
    mat_cornerbeam : bpy.props.PointerProperty(
            name = "老角梁",
            type = bpy.types.Object,
        )# type: ignore  
    mat_queti : bpy.props.PointerProperty(
            name = "雀替",
            type = bpy.types.Object,
        )# type: ignore  
    mat_dougong : bpy.props.PointerProperty(
            name = "斗栱",
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
    
    # 雀替对象
    queti_source : bpy.props.PointerProperty(
            name = "雀替",
            type = bpy.types.Object,
        )# type: ignore
    
    # 穿插枋对象
    ccfang_source : bpy.props.PointerProperty(
            name = "穿插枋",
            type = bpy.types.Object,
        )# type: ignore
    
    # 琉璃瓦对象
    flatTile_source:bpy.props.PointerProperty(
            name = "板瓦",
            type = bpy.types.Object,
        )# type: ignore 
    circularTile_source:bpy.props.PointerProperty(
            name = "筒瓦",
            type = bpy.types.Object,
        )# type: ignore 
    eaveTile_source:bpy.props.PointerProperty(
            name = "瓦当",
            type = bpy.types.Object,
        )# type: ignore 
    dripTile_source:bpy.props.PointerProperty(
            name = "滴水",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 屋脊对象
    ridgeTop_source:bpy.props.PointerProperty(
            name = "正脊筒",
            type = bpy.types.Object,
        )# type: ignore 
    ridgeBack_source:bpy.props.PointerProperty(
            name = "垂脊兽后",
            type = bpy.types.Object,
        )# type: ignore 
    ridgeFront_source:bpy.props.PointerProperty(
            name = "垂脊兽前",
            type = bpy.types.Object,
        )# type: ignore 
    ridgeEnd_source:bpy.props.PointerProperty(
            name = "端头盘子",
            type = bpy.types.Object,
        )# type: ignore 
    chiwen_source:bpy.props.PointerProperty(
            name = "螭吻",
            type = bpy.types.Object,
        )# type: ignore 
    baoding_source:bpy.props.PointerProperty(
            name = "宝顶",
            type = bpy.types.Object,
        )# type: ignore 
    chuishou_source:bpy.props.PointerProperty(
            name = "垂兽",
            type = bpy.types.Object,
        )# type: ignore 
    taoshou_source:bpy.props.PointerProperty(
            name = "套兽",
            type = bpy.types.Object,
        )# type: ignore 
    
    # 跑兽对象
    paoshou_0_source:bpy.props.PointerProperty(
            name = "仙人",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_1_source:bpy.props.PointerProperty(
            name = "龙",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_2_source:bpy.props.PointerProperty(
            name = "凤",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_3_source:bpy.props.PointerProperty(
            name = "狮子",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_4_source:bpy.props.PointerProperty(
            name = "海马",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_5_source:bpy.props.PointerProperty(
            name = "天马",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_6_source:bpy.props.PointerProperty(
            name = "狎鱼",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_7_source:bpy.props.PointerProperty(
            name = "狻猊",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_8_source:bpy.props.PointerProperty(
            name = "獬豸",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_9_source:bpy.props.PointerProperty(
            name = "斗牛",
            type = bpy.types.Object,
        )# type: ignore 
    paoshou_10_source:bpy.props.PointerProperty(
            name = "行什",
            type = bpy.types.Object,
        )# type: ignore     
    walleave:bpy.props.PointerProperty(
            name = "墙檐",
            type = bpy.types.Object,
        )# type: ignore     
    door_pushou:bpy.props.PointerProperty(
            name = "铺首",
            type = bpy.types.Object,
        )# type: ignore     
    door_ding:bpy.props.PointerProperty(
            name = "门钉",
            type = bpy.types.Object,
        )# type: ignore     
    door_zan:bpy.props.PointerProperty(
            name = "门簪",
            type = bpy.types.Object,
        )# type: ignore 
    
# template下拉框已经废弃，本方法也随之废弃
# # 使用动态enumproperty时，必须声明全局变量持久化返回的回调数据
# # https://docs.blender.org/api/current/bpy.props.html
# # Warning
# # There is a known bug with using a callback, 
# # Python must keep a reference to the strings 
# # returned by the callback or Blender will 
# # misbehave or even crash.
# templateList = []
# def getTemplateList(self, context):
#     from . import template
#     global templateList
#     templateList = template.getTemplateList()
#     return templateList

# 模板样式列表的行对象，绑定在UI_list上
class TemplateListItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(
        name="Name", default="Item"
    ) # type: ignore

# 模板缩略图控件对象，绑定在template_view_icon上
class TemplateThumbItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()# type: ignore     
    path: bpy.props.StringProperty()# type: ignore     

# 模板列表更新时，联动右侧缩略图
def updateSelectedThumb(self,context):    
    scene = bpy.context.scene
    tIndex = self.templateIndex
    tName = self.templateItem[tIndex].name
    try:
        scene.image_browser_enum = tName
    except Exception as e:
        utils.outputMsg(f"无法显示缩略图 {tName}") 
    return

def updateSelectedTemplate(self, context:bpy.types.Context):
    selectedThumb = self.image_browser_enum
    scnData = context.scene.ACA_data
    templateItems = scnData.templateItem
    for index,item in enumerate(templateItems):
        if item.name == selectedThumb:
            scnData['templateIndex'] = index
    return

# 场景范围的数据
# 可绑定面板参数属性
# 也可做为全局变量访问
# 属性声明的格式在vscode有告警，但blender表示为了保持兼容性，无需更改
# 直接添加“# type:ignore”
# https://blender.stackexchange.com/questions/311578/how-do-you-correctly-add-ui-elements-to-adhere-to-the-typing-spec
class ACA_data_scene(bpy.types.PropertyGroup):
    is_auto_redraw : bpy.props.BoolProperty(
            default = True,
            name = "是否实时重绘",
            description = "取消后，生成过程中不进行刷新，直到全部生成后才显示",
        ) # type: ignore
    is_auto_viewall : bpy.props.BoolProperty(
            default = True,
            name = "是否设置视角",
            description = "取消后，不再自动切换视角，始终保持当前视角",
        ) # type: ignore
    is_auto_rebuild : bpy.props.BoolProperty(
            default = True,
            name = "是否实时重建",
            description = "取消后，在大部分参数修改时，不会自动重建，直到手工点击更新建筑",
        ) # type: ignore
    # template原来提供给模板下拉框使用，现在改为列表，则不再使用该属性
    # template : bpy.props.EnumProperty(
    #         name = "样式列表",
    #         description = "样式列表",
    #         items = getTemplateList,
    #         options = {"ANIMATABLE"},
    #     ) # type: ignore
    templateItem : bpy.props.CollectionProperty(
        type=TemplateListItem)# type: ignore
    templateIndex: bpy.props.IntProperty(
            name="Active List Index",
            default=0, 
            update=updateSelectedThumb,
        )# type: ignore 