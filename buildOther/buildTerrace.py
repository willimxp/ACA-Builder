# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   月台的营造
import bpy
from mathutils import Vector

from .. import utils
from ..const import ACA_Consts as con
from ..locale.i18n import _
from ..data import ACA_data_obj as acaData
from .. import buildFloor
from .. import buildPlatform
from .. import buildCombo

# 添加月台
# 传入主建筑，在主建筑上添加月台
def addTerrace(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 250828 只要是台基，就允许添加月台
    # 260424 限制主建筑，以免回廊等对象添加月台
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox(_("抱歉，该建筑不支持添加月台"))
        return {'CANCELLED'}
    
    
    # 1、构造组合层次结构 ------------------------
    # 添加combo根节点
    comboObj = utils.getComboRoot(buildingObj)
    # 如果不存在combo则新建
    if comboObj is None:
        comboObj = buildCombo.addComboLevel(buildingObj)

    # 验证是否已经有月台
    terraceRoot = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    if terraceRoot is not None:
        utils.popMessageBox(_("已经有一个月台，不能再生成新的月台"))
        return {'CANCELLED'}

    # 构建月台子节点
    terraceRoot = buildFloor.__addBuildingRoot(
        templateName = buildingObj.ACA_data.template_name + _('.月台'),
        comboObj = comboObj
    ) 
    # 务必及时标注combo_type,后续的数据同步和数据设置时都要判断主建筑
    terraceRoot.ACA_data['combo_type'] = con.COMBO_TERRACE
    link_id = buildingObj.ACA_data.aca_id
    terraceRoot.ACA_data['combo_parent'] = link_id
    
    # 2、构造月台数据集 --------------------------
    # 从Combo根节点继承数据
    utils.outputMsg(_("添加月台子建筑..."))
    # __downloadData(toBuilding=terraceRoot)
    # 设置月台逻辑数据
    setTerraceData(parentObj=buildingObj,
                     terraceObj=terraceRoot,
                     isInit=True)
    
    # 3、开始营造 ------------------------------
    # 刷新主建筑月台（隐藏前出踏跺）
    buildPlatform.buildPlatform(buildingObj)
    
    # 添加月台，复用的buildPlatform
    # 但传入terraceRoot，做为组合建筑的子对象
    buildPlatform.buildPlatform(terraceRoot)

    # 初始化月台根节点
    bData:acaData = terraceRoot.ACA_data
    terraceRoot.location = bData.combo_location

    # 重做柱网（显示柱定位标识）
    buildFloor.buildPillars(terraceRoot)

    # 聚焦新生成的月台
    terraceObj = utils.getAcaChild(
        terraceRoot,con.ACA_TYPE_PLATFORM
    )
    if terraceObj is not None:
        utils.focusObj(terraceObj)

    return {'FINISHED'}

# 删除月台
def delTerrace(terraceObj:bpy.types.Object):
    # 载入数据
    bData:acaData = terraceObj.ACA_data

    # 批量还原标识
    comboObj = utils.getComboRoot(terraceObj)
    cData:acaData = comboObj.ACA_data
    cData['use_terrace'] = False
    for child in comboObj.children:
        child.ACA_data.use_terrace = False

    # 删除月台
    if bData.combo_type == con.COMBO_TERRACE:
        from .. import build
        build.delBuilding(terraceObj,
            withCombo=False,# 仅删除个体
        )

    # 预先找到主建筑，否则下一步删除comboRoot以后就找不到了
    mainBuilding = utils.getMainBuilding(comboObj)
    # 260424 如果是回廊等建筑的combo_type可能不是combo_main，导致找不到mainBuilding
    if mainBuilding is None:
        mainBuilding = comboObj.children[0]
    if mainBuilding is None:
        utils.outputMsg(_("删除组合建筑失败，找不到主建筑。"))
        return 

    # 是否需要组合降级
    from .. import build
    buildCombo.delComboLevel(comboObj, mainBuilding)

    # 更新主建筑台基
    buildPlatform.buildPlatform(mainBuilding)
    # 聚焦主建筑的台基
    mainPlatform = utils.getAcaChild(
        mainBuilding,con.ACA_TYPE_PLATFORM
    )
    if mainPlatform is not None:
        utils.focusObj(mainPlatform)

    return {'FINISHED'}

# 设置月台数据
def setTerraceData(parentObj:bpy.types.Object,
                     terraceObj:bpy.types.Object,
                     isInit = False, # 初始化标识，区分是新建还是更新
                     ):
    # 主建筑数据集
    mainBuildingObj = parentObj
    mData:acaData = mainBuildingObj.ACA_data
    
    # 初始化数据集
    # 月台数据集
    bData:acaData = terraceObj.ACA_data

    # 1、新建时的初始化处理，更新时跳过 -------------
    if isInit:
        # 同步基本建筑的柱网等数据
        buildCombo.syncData(fromBuilding=parentObj,
               toBuilding=terraceObj)
        
        # 不做踏跺
        bData.step_list.clear()
        # 不做墙体
        bData.wall_list.clear()
        bData.geshan_list.clear()
        bData.window_list.clear()
        bData.railing_list.clear()
        bData.maindoor_list.clear()
        
        # 这里不要上报了，仅仅为了use_terrace
        # 反而导致roof_style被覆盖
        # # 数据上报到combo ------------------------
        # utils.outputMsg("月台数据修改上报...")
        # __uploadData(fromBuilding=mainBuildingObj)

        # 2、月台开间与主建筑联动 -------------
        # 月台进深，五间以上减2间
        yRooms = mData.y_rooms
        if mData.use_double_eave:
            # 重檐不考虑廊间
            yRooms -= 2
        if yRooms > 2:
            bData['y_rooms'] = yRooms - 2
        else:
            bData['y_rooms'] = yRooms

        # 月台面阔，五间以上做"凸"形月台，减2间
        xRooms = mData.x_rooms
        if mData.use_double_eave:
            # 重檐不考虑廊间
            xRooms -= 2
        if xRooms > 5:
            bData['x_rooms'] = xRooms - 2
        else:
            bData['x_rooms'] = xRooms

        # 矫正梢间，不使用主建筑的廊间数据
        if mData.use_double_eave:
            if bData.x_rooms >= 7:
                bData['x_4'] = mData.x_3
                bData['x_3'] = mData.x_2
        
        # 月台高度，比主体低1踏步
        bData['platform_height'] = (
            mData.platform_height - con.STEP_HEIGHT)
        # 月台下出，比主体窄2踏步（未见规则）
        bData['platform_extend'] = (
            mData.platform_extend 
            - con.STEP_HEIGHT*2
            )
    
    # 2、其他数据的设置 --------------------------
    # 分层显示控制
    bData['is_showPlatform'] = True
    bData['is_showPillars'] = True
    bData['is_showWalls'] = False
    bData['is_showDougong'] = False
    bData['is_showBeam'] = False
    bData['is_showRafter'] = False
    bData['is_showTiles'] = False
    bData['is_showBalcony'] = False

    # 基本属性标注
    bData['use_terrace'] = True
    mData['use_terrace'] = True
    # 柱网仅显示定位点
    bData['pillar_net'] = con.ACA_PILLAR_HIDE
        
    # 月台定位 ------------------------
    # 更新地盘数据，计算当前的y_total
    buildFloor.getFloorDate(mainBuildingObj)
    buildFloor.getFloorDate(terraceObj)
    offsetY = (mData.y_total/2 
               + mData.platform_extend
               + bData.y_total/2 
               + bData.platform_extend
               )
    terraceLoc = Vector((0,-offsetY,0))
    bData['combo_location'] = terraceLoc

    return terraceObj
