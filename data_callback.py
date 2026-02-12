# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   自定义数据结构的业务逻辑回调
#   从data.py中分离出的逻辑代码

import bpy
import time 
from functools import partial

from .const import ACA_Consts as con
from . import utils

# # 筛选资产目录
# def p_filter(self, object:bpy.types.Object):
#     # 仅返回Assets collection中的对象
#     return object.users_collection[0].name == 'Assets'

# 刷新斗口
def update_dk(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 确认选中为building节点
    buildingObj,bData,odata = utils.getRoot(context.object)
    if buildingObj != None:
        from . import template
        template.updateDougongData(buildingObj)
        update_building(self,context)
    return

# 更新柱高
def update_pillarHeight(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 如果有楼阁，更新楼阁层高
    comboRoot = utils.getComboRoot(context.object)
    if comboRoot is not None:
        # 显示进度条 
        from . import build
        build.isFinished = False
        build.progress = 0

        from . import buildCombo
        buildCombo.__updateFloorLoc(comboRoot)
    
    # 重建当前建筑
    update_building(self,context)
    

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

# 更新踏跺
def update_step(self, context:bpy.types.Context):
    # 建筑根节点数据
    buildingObj,bData,oData = utils.getRoot(context.object)
    # 确认选中了踏跺
    if oData.aca_type != con.ACA_TYPE_STEP:
        utils.popMessageBox("当前活动对象不是踏跺")
        return
    
    # 获取当前踏跺数据
    for step in bData.step_list:
        if step.id == oData['stepID'] :
            currentStepData = step
    
    # 所有选中的对象
    selected_steps = context.selected_objects
    # 暂存选中的对象
    selected_names = []
    for stepSelected in selected_steps:
        selected_names.append(stepSelected.name)
    
    # 批量设置所有选中的对象
    for stepSelected in selected_steps:
        # 确认是踏跺
        if stepSelected.ACA_data.aca_type != con.ACA_TYPE_STEP:
            continue

        # 全部修改为当前值
        for stepData in bData.step_list:
            if stepData.id == stepSelected.ACA_data['stepID']:
                stepData['width'] = currentStepData.width

    # 更新整个台基
    update_platform(self,context)

    # 恢复踏跺选择
    # 先取消所有选中（因为可能再update_platform中focus了root）
    bpy.ops.object.select_all(action='DESELECT')
    for objName in selected_names:
        stepObj = bpy.data.objects[objName]
        stepObj.select_set(True)
        bpy.context.view_layer.objects.active = stepObj

    return

# 更新栏杆，设置开口参数
def update_railing(self, context:bpy.types.Context):
    # 建筑根节点数据
    buildingObj,bData,oData = utils.getRoot(context.object)
    railingID = oData['wallID']
    # 确认选中了栏杆
    if oData.aca_type not in (con.ACA_WALLTYPE_RAILILNG,
                              con.ACA_WALLTYPE_BENCH):
        utils.popMessageBox("当前活动对象不是栏杆/坐凳")
        return
    
    # 所有选中的对象
    selected_objs = context.selected_objects
    # 暂存选中的对象
    selected_names = []
    for objSelected in selected_objs:
        selected_names.append(objSelected.name)

    # 获取当前栏杆数据    
    currentRailingData = utils.getDataChild(
        contextObj = buildingObj,
        obj_type = con.ACA_WALLTYPE_RAILILNG,
        obj_id = railingID,
    )
    if currentRailingData is None:
        raise Exception("无法获取railing_list中的{railingID}数据集")
    
    # 批量设置所有选中的对象
    for railingSelect in selected_objs:
        # 确认是踏跺
        if railingSelect.ACA_data.aca_type not in (con.ACA_WALLTYPE_RAILILNG,
                              con.ACA_WALLTYPE_BENCH):
            continue

        # 获取其他被选中的栏杆数据    
        selectedID = railingSelect.ACA_data['wallID']
        selectedRailingData = utils.getDataChild(
            contextObj = buildingObj,
            obj_type=con.ACA_WALLTYPE_RAILILNG,
            obj_id=selectedID,
        )
        if selectedRailingData is None:
            raise Exception("无法获取railing_list中的{railingID}数据集")
        
        # 设置数据
        selectedRailingData['gap'] = currentRailingData.gap

        # 更新实体
        from . import buildWall
        funproxy = partial(buildWall.updateWall,
                        wallObj=railingSelect)
        utils.fastRun(funproxy)

    # 恢复踏跺选择
    # 先取消所有选中（因为可能再update_platform中focus了root）
    bpy.ops.object.select_all(action='DESELECT')
    for objName in selected_names:
        stepObj = bpy.data.objects[objName]
        stepObj.select_set(True)
        bpy.context.view_layer.objects.active = stepObj

    return

def update_platform(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 台基最小值控制
    buildingObj,bData,oData = utils.getRoot(context.object)
    # 下出不小于柱径
    if bData.platform_extend<bData.pillar_diameter:
        bData['platform_extend'] = bData.pillar_diameter/2
    # 高度不小于方砖曼地
    if bData.platform_height<con.STEP_HEIGHT:
        bData['platform_height'] = con.STEP_HEIGHT
    
    # 从self属性找到对应的Object，用self.id_data
    # https://blender.stackexchange.com/questions/145245/how-to-access-object-instance-from-property-instance-in-update-callback
    refObj = self.id_data

    # 251217 添加清除拼接
    from . import buildSplice
    buildSplice.undoSplice(buildingObj)
    
    # 调用台基缩放
    from . import buildPlatform
    # buildPlatform.resizePlatform(buildingObj)
    funproxy = partial(
            buildPlatform.resizePlatform,
            buildingObj=refObj)
    utils.fastRun(funproxy)

    return

# 仅更新柱体样式，不触发其他重建
def update_PillarStyle(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 调用营造序列
        from . import buildFloor
        # buildFloor.buildPillars(buildingObj)
        funproxy = partial(
                buildFloor.buildPillars,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated building failed, context.object should be buildingObj")
    return

# 更新柱体尺寸，会自动触发墙体重建
def update_pillar(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return

    # 确认选中为building节点
    buildingObj,bdata,odata = utils.getRoot(context.object)
    if buildingObj != None:
        # 缩放柱形
        from . import buildFloor
        # buildFloor.resizePillar(buildingObj)
        funproxy = partial(
                buildFloor.resizePillar,
                buildingObj=buildingObj)
        utils.fastRun(funproxy)
    else:
        utils.outputMsg("updated pillar failed, context should be pillarObj")
    return

def update_wall(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    contextObj = context.active_object
    # 暂存，以便批量更新后的恢复选择
    activeObjName = contextObj.name
    buildingObj,bData,oData = utils.getRoot(contextObj)

    # 1、预处理，校验所有选中的对象---------------------------
    # 所有选中的对象
    selected_walls = context.selected_objects
    # 暂存选中的对象
    selected_names = []
    # 经过确认需要更新的墙体对象，如，将隔扇子对象，替换成槛框父对象
    update_walls = []
    for wallSelected in selected_walls:
        # 验证是否跨建筑
        wallbuilding,wbData,woData = utils.getRoot(wallSelected)
        if wallbuilding != buildingObj:
            # 丢弃跨建筑的对象
            continue

        # 验证为待更新的装修对象
        if wallSelected.ACA_data.aca_type in (
            con.ACA_TYPE_WALL,              # 槛墙
            con.ACA_WALLTYPE_WINDOW,        # 槛窗
            con.ACA_WALLTYPE_GESHAN,        # 隔扇
            con.ACA_WALLTYPE_BARWINDOW,     # 直棂窗
            con.ACA_WALLTYPE_MAINDOOR,      # 板门
            con.ACA_WALLTYPE_FLIPWINDOW,    # 支摘窗
            con.ACA_WALLTYPE_RAILILNG,      # 栏杆
            con.ACA_WALLTYPE_BENCH,         # 坐凳
        ):
            # 存入选择列表
            if not wallSelected.name in selected_names:
                selected_names.append(wallSelected.name)
            # 存入待更新列表
            if not wallSelected in update_walls:
                update_walls.append(wallSelected)
        # 如果是门窗子对象，自动选择槛框
        elif wallSelected.ACA_data.aca_type == con.ACA_TYPE_WALL_CHILD:
            kankuangObj = wallSelected.parent
            # 自动选择槛框父对象
            kankuangObj.select_set(True)
            # 如果门窗子对象是活动对象
            if context.active_object == wallSelected:
                # 设置槛框父对象为活动对象
                bpy.context.view_layer.objects.active = kankuangObj
            # 存入选择列表
            if not kankuangObj.name in selected_names:
                selected_names.append(kankuangObj.name)
            # 存入待更新列表
            if not kankuangObj in update_walls:
                update_walls.append(kankuangObj)
        # 其他不符合的构件，不做处理
        else:
            continue

    # 2、开始批量处理--------------------------------------
    from . import buildWall
    # 活动对象，批量设置时，以此对象的设置为准
    contextObj = context.active_object
    buildingObj,bData,oData = utils.getRoot(contextObj)
    # 批量设置所有选中的对象
    for wallUpdate in update_walls:
        # 多选时，数据传递
        if wallUpdate != contextObj:
            # 获取对应的data
            walldata = utils.getDataChild(
                contextObj=buildingObj,
                obj_type=wallUpdate.ACA_data.aca_type,
                obj_id=wallUpdate.ACA_data['wallID'])
            # 全部修改为当前值
            for prop in self.bl_rna.properties:
                if prop.is_runtime:
                    key = prop.identifier
                    value = getattr(self,key)
                    # id不要覆盖哦！
                    if key == 'id' : continue

                    # 只传递有的字段，没有的字段就抛弃
                    if hasattr(walldata,key):
                        walldata[key] = value
        # 执行更新
        funproxy = partial(buildWall.updateWall,
                                wallObj=wallUpdate)
        utils.fastRun(funproxy)

    # 恢复墙体选择
    bpy.ops.object.select_all(action='DESELECT')
    for objName in selected_names:
        wallObj = bpy.data.objects[objName]
        wallObj.select_set(True)
    if activeObjName in bpy.data.objects:
        activeObj = bpy.data.objects[activeObjName]
        bpy.context.view_layer.objects.active = activeObj
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
        # 2、因为这里抢先用上檐柱头科替换掉了aData.dg_pillar_source
        # 从而导致buildCombo.__getDoubleEaveLift时获取了错误的dg_extend
        # 3、同时，在buildDougong.__buildDougong中已经调用了updateDougongData，
        # 所以，这里直接禁用掉，目前看起来没有问题
        # 以观后效
        # 250831 重新调用此斗栱数据更新，否则在单体建筑切换斗栱时，柱高未及时更新
        # 重檐的问题，晚些再说
        # -------------
        # 初始化斗栱数据，避免跨建筑时公用的aData干扰
        from . import template
        template.updateDougongData(buildingObj)

        # 如果有楼阁，更新楼阁层高
        comboRoot = utils.getComboRoot(context.object)
        if comboRoot is not None:
            # 显示进度条 
            from . import build
            build.isFinished = False
            build.progress = 0

            from . import buildCombo
            buildCombo.__updateFloorLoc(comboRoot)
        
        # 241125 修改斗栱时，涉及到柱高的变化，最好是全屋更新
        update_building(self,context)
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
    
    # 确认选中为building节点
    buildingObj,bData,oData = utils.getRoot(context.object)
    if buildingObj != None:
        bpy.ops.aca.build_roof()

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

    # 盝顶默认2步架
    if bData.roof_style in (
        con.ROOF_LUDING,
    ):
        bData['rafter_count'] = 2
    else:
        bData['rafter_count'] = 6

    # 250907 切换平坐屋顶时，需要更新平坐斗栱
    from . import template
    template.updateDougongData(buildingObj)

    return

def update_rooftile(self, context:bpy.types.Context):
    # 判断自动重建开关
    isRebuild = bpy.context.scene.ACA_data.is_auto_rebuild
    if not isRebuild:
        return
    
    # 确认选中为building节点
    buildingObj,bData,oData = utils.getRoot(context.object)
    if buildingObj != None:
        # 251217 添加清除拼接
        from . import buildSplice
        buildSplice.undoSplice(buildingObj)

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
def hide_pillars(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_PILLAR,
        self.is_showPillars)

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
    
# 显示/隐藏平坐层
def hide_balcony(self, context:bpy.types.Context):
    buildingObj = self.id_data
    utils.hideLayer(
        buildingObj,con.COLL_NAME_BALCONY,
        self.is_showBalcony)

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

# 模板列表更新时，联动右侧缩略图
def updateSelectedPavilionThumb(self,context):    
    scene = bpy.context.scene
    tIndex = self.pavilionIndex
    tName = self.pavilionItem[tIndex].name
    try:
        scene.pavilion_browser_enum = tName
    except Exception as e:
        utils.outputMsg(f"无法显示缩略图 {tName}") 
    
    # 更新默认参数
    from . import buildCombo
    buildCombo.set_multiFloor_plan(self,context)
    return

def updateSelectedPavilion(self, context:bpy.types.Context):
    selectedThumb = self.pavilion_browser_enum
    scnData = context.scene.ACA_data
    pavilionItems = scnData.pavilionItem
    for index,item in enumerate(pavilionItems):
        if item.name == selectedThumb:
            scnData['pavilionIndex'] = index

    # 更新默认参数
    from . import buildCombo
    buildCombo.set_multiFloor_plan(self,context)
    return
