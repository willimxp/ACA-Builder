# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   组合建筑的营造
import bpy
from mathutils import Vector

from . import utils
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import template
from . import buildFloor
from . import buildPlatform

# 添加combo根节点
def __addComboRoot(templateName):
    # 创建或锁定根目录
    coll = utils.setCollection(templateName)
    # 创建buildObj根节点
    # 原点摆放在3D Cursor位置
    comboObj = utils.addEmpty(
        name=templateName,
        location=bpy.context.scene.cursor.location
    )
    cData:acaData = comboObj.ACA_data
    cData['template_name'] = templateName
    cData['aca_type'] = con.ACA_TYPE_COMBO

    return comboObj

# 基于单一建筑，添加组合建筑
def __addComboLevel(buildingObj:bpy.types.Object):
    # 校验建筑为单一建筑
    buildingObj,bData,objData = utils.getRoot(buildingObj)
    comboObj = utils.getComboRoot(buildingObj)
    if comboObj is not None:
        utils.outputMsg("添加组合建筑失败，已经为组合建筑。")
        return
        
    # 添加组合建筑
    rootColl = utils.setCollection(con.COLL_NAME_ROOT,
                        isRoot=True,colorTag=2)
    # 添加combo根节点
    comboObj = __addComboRoot(buildingObj.name + '.combo')

    # 更改对象父节点
    m = buildingObj.matrix_world.copy()
    buildingObj.parent = comboObj

    # 更改映射
    comboObj.matrix_world = m
    import mathutils
    buildingObj.matrix_local = mathutils.Matrix()

    # 更改目录级别
    buildingColl = buildingObj.users_collection[0]
    # 关联到combo目录
    comboColl = comboObj.users_collection[0]
    comboColl.children.link(buildingColl)
    # 从根目录移除
    rootColl = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
    rootColl.children.unlink(buildingColl)

    return comboObj

def buildCombo(
        templateName,
):
    # 添加combo根节点
    comboObj = __addComboRoot(templateName)
    
    # 组合建筑
    tempChildren = template.getTemplateChild(templateName)
    for child in tempChildren:
        from . import build
        build.buildSingle(
            acaType = child['acaType'],
            templateName = child['templateName'],
            comboObj = comboObj
        )
    return

# 刷新组合建筑
def updateCombo(buildingObj:bpy.types.Object,
                reloadAssets=False,
                reset=False):
    comboObj = utils.getComboRoot(buildingObj)
    
    # 循环清空各个建筑构件
    for childBuilding in comboObj.children:
        utils.deleteHierarchy(childBuilding)
    
    # 同步combo子建筑数据
    updateComboData(buildingObj)

    # 重檐数据更新
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE)
    setDoubleEaveData(doubleEaveObj)

    # 月台数据更新
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    setTerraceData(terraceObj)            
        
    # 循环生成各个单体
    for childBuilding in comboObj.children:
        if reset:
            buildFloor.resetFloor(childBuilding,
                comboObj=comboObj)
        else:
            buildFloor.buildFloor(childBuilding,
                    reloadAssets=reloadAssets,
                    comboObj=comboObj)

# 组合建筑降级为单一建筑
def delCombo(buildingObj:bpy.types.Object):
    # 校验建筑为单一建筑
    buildingObj,bData,objData = utils.getRoot(buildingObj)
    if buildingObj.parent is None:
        utils.outputMsg("删除组合建筑失败，当前建筑没有父节点。")
        return
    else: 
        comboObj = buildingObj.parent
    
    if comboObj.ACA_data.aca_type != con.ACA_TYPE_COMBO:
        utils.outputMsg("删除组合建筑失败，不是组合建筑。")
        return
    
    # 是否只剩一个建筑？
    if len(comboObj.children) > 1:
        utils.outputMsg("删除组合建筑失败，不止一个建筑存在。")
        return
    
    # 更改目录级别
    buildingColl = buildingObj.users_collection[0]
    # 关联到根目录
    rootColl = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
    rootColl.children.link(buildingColl)
    # 删除父集合
    comboColl = comboObj.users_collection[0]
    comboColl.children.unlink(buildingColl)
    bpy.data.collections.remove(comboColl)    

    # 删除父节点
    buildingObj.parent = None
    # 更改映射
    buildingObj.matrix_world = comboObj.matrix_world.copy()
    utils.delObject(comboObj)

    return

# 同步combo组合建筑中的各个子建筑数据
# 调用方：terraceAdd,doubleEaveadd,updateCombo
# syncKeys限制同步的键值范围，None即全部拷贝
def initComboData(buildingObj:bpy.types.Object,
                  keys = None
    ):
    # 不做同步的字段
    skip = ['combo_type',]

    # combo的数据集
    comboObj = utils.getComboRoot(buildingObj)
    mainBuildingObj = utils.getMainBuilding(comboObj)
    if mainBuildingObj is None:
        utils.outputMsg("combo数据同步失败，未找到主建筑")
        return

    # 主建筑数据同步
    for childBuilding in comboObj.children:
        # 主建筑无需同步
        if childBuilding == mainBuildingObj:
            continue

        # 其他子建筑都要从主建筑同步
        utils.copyAcaData(
            fromObj = mainBuildingObj,
            toObj = childBuilding,
            skip = skip,
        )
    return

# 同步combo组合建筑中的各个子建筑数据
# 调用方：terraceAdd,doubleEaveadd,updateCombo
# syncKeys限制同步的键值范围，None即全部拷贝
def updateComboData(buildingObj:bpy.types.Object):
    # 同步combo子建筑数据
    # 仅限于以下的共性化属性
    # 保留各个子建筑的个性化设置
    keys = [
        'DK',
        'x_1',
        'x_2',
        'x_3',
        'x_4',
        'y_1',
        'y_2',
        'y_3',
        'paint_style',
        'dg_scale',
        'dg_gap',
        'tile_scale',
        'tile_color',
        'tile_alt_color',
        'tile_width',
        'tile_length',
    ]

    # combo的数据集
    comboObj = utils.getComboRoot(buildingObj)
    mainBuildingObj = utils.getMainBuilding(comboObj)
    if mainBuildingObj is None:
        utils.outputMsg("combo数据同步失败，未找到主建筑")
        return

    # 主建筑数据同步
    for childBuilding in comboObj.children:
        # 主建筑无需同步
        if childBuilding == mainBuildingObj:
            continue

        # 其他子建筑都要从主建筑同步
        utils.copyAcaData(
            fromObj = mainBuildingObj,
            toObj = childBuilding,
            keys = keys
        )
    return

# 添加月台
# 传入主建筑，在主建筑上添加月台
def terraceAdd(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox("不能添加月台，只有主体建筑可以添加月台")
        return
    
    # 1、构造组合层次结构 ------------------------
    # 添加combo根节点
    comboObj = utils.getComboRoot(buildingObj)
    # 如果不存在combo则新建
    if comboObj is None:
        comboObj = __addComboLevel(buildingObj)

    # 验证是否已经有月台
    terraceRoot = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    if terraceRoot is not None:
        utils.popMessageBox("已经有一个月台，不能再生成新的月台")
        return

    # 构建月台子节点
    terraceRoot = buildFloor.__addBuildingRoot(
        templateName = '月台',
        comboObj = comboObj
    )    
    
    # 2、构造月台数据集 --------------------------
    # 基于主建筑属性，进行初始化
    initComboData(terraceRoot)
    # 设置月台逻辑数据
    setTerraceData(terraceRoot)
    
    # 3、开始营造 ------------------------------
    # 刷新主建筑月台（隐藏前出踏跺）
    buildPlatform.buildPlatform(buildingObj)
    
    # 添加月台，复用的buildPlatform
    # 但传入terraceRoot，做为组合建筑的子对象
    buildPlatform.buildPlatform(terraceRoot)

    # 初始化月台根节点
    bData:acaData = terraceRoot.ACA_data
    terraceRoot.location = bData.root_location

    # 重做柱网（显示柱定位标识）
    buildFloor.buildPillers(terraceRoot)

    # 聚焦新生成的月台
    terraceObj = utils.getAcaChild(
        terraceRoot,con.ACA_TYPE_PLATFORM
    )
    if terraceObj is not None:
        utils.focusObj(terraceObj)

    return

# 删除月台
def terraceDelete(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data
    # 获取主建筑
    mainBuilding = utils.getMainBuilding(buildingObj)
    mData:acaData = mainBuilding.ACA_data

    # 更新主建筑台基
    mData['use_terrace'] = False
    bData['use_terrace'] = False
    buildPlatform.buildPlatform(mainBuilding)

    # 删除月台
    if bData.combo_type == con.COMBO_TERRACE:
        from . import build
        build.delBuilding(buildingObj,
            withCombo=False,# 仅删除个体
        )

    # 组合建筑降级
    from . import build
    delCombo(mainBuilding)

    # 聚焦主建筑的台基
    mainPlatform = utils.getAcaChild(
        mainBuilding,con.ACA_TYPE_PLATFORM
    )
    if mainPlatform is not None:
        utils.focusObj(mainPlatform)

    return

# 设置月台数据
# 在terraceAdd和syncComboData中复用
def setTerraceData(terraceObj:bpy.types.Object):
    # 初始化数据集
    # 月台数据集
    bData:acaData = terraceObj.ACA_data
    # 主建筑数据集
    mainBuildingObj = utils.getMainBuilding(terraceObj)
    mData:acaData = mainBuildingObj.ACA_data
    
    # 1、主建筑数据更新 ------------------------
    mData['use_terrace'] = True

    # 2、月台数据更新 --------------------------
    bData['use_terrace'] = True
    bData['combo_type'] = con.COMBO_TERRACE
    # 分层显示控制
    bData['is_showPlatform'] = True
    bData['is_showPillers'] = True
    bData['is_showWalls'] = False
    bData['is_showDougong'] = False
    bData['is_showBeam'] = False
    bData['is_showRafter'] = False
    bData['is_showTiles'] = False
    
    # 不做踏跺
    bData['step_net'] = ''
    # 柱网仅显示定位点
    bData['piller_net'] = con.ACA_PILLER_HIDE
    # 不做额枋
    bData['fang_net'] = ''
    # 不做墙体
    bData['wall_net'] = ''
    
    # 月台高度，比主体低1踏步
    bData['platform_height'] = (
        mData.platform_height - con.STEP_HEIGHT)
    # 月台下出，比主体窄2踏步（未见规则）
    bData['platform_extend'] = (
        mData.platform_extend 
        - con.STEP_HEIGHT*2
        )
    
    # 月台进深，五间以上减2间
    if mData.y_rooms > 2:
        bData['y_rooms'] = mData.y_rooms - 2
    else:
        bData['y_rooms'] = mData.y_rooms
    # 月台面阔，五间以上做“凸”形月台，减2间
    if mData.x_rooms > 5:
        bData['x_rooms'] = mData.x_rooms - 2
    else:
        bData['x_rooms'] = mData.x_rooms
    
    # 月台定位
    # 更新地盘数据，计算当前的y_total
    buildFloor.getFloorDate(mainBuildingObj)
    buildFloor.getFloorDate(terraceObj)
    offsetY = (mData.y_total/2 
               + mData.platform_extend
               + bData.y_total/2 
               + bData.platform_extend
               )
    terraceLoc = Vector((0,-offsetY,0))
    bData['root_location'] = terraceLoc

    return terraceObj

# 添加重檐
def doubleEaveAdd(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox("请先选择主体建筑，只有主体建筑可以添加重檐")
        return
    
    # 1、构造组合层次结构 ------------------------
    # 添加combo根节点
    comboObj = utils.getComboRoot(buildingObj)
    # 如果不存在combo则新建
    if comboObj is None:
        comboObj = __addComboLevel(buildingObj)

    # 验证是否已经有重檐
    doubleEaveRoot = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE)
    if doubleEaveRoot is not None:
        utils.popMessageBox("已经有一个重檐，不能再生成新的重檐")
        return

    # 构建重檐子节点
    doubleEaveRoot = buildFloor.__addBuildingRoot(
        templateName = '重檐',
        comboObj = comboObj
    )

    # 2、构造重檐数据集 ----------------------
    # 基于主建筑属性，进行初始化
    initComboData(doubleEaveRoot)    
    # 设置重檐逻辑数据
    setDoubleEaveData(doubleEaveRoot)

    # 3、开始营造 ------------------------------
    # 重新生成月台（地盘变化了）
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    if terraceObj is not None:
        updateComboData(terraceObj)
        setTerraceData(terraceObj)
        buildFloor.buildFloor(
            terraceObj,
            comboObj=comboObj # 传入combo以便及时更新位置
            )
    
    # 重新生成主建筑
    buildFloor.buildFloor(buildingObj)

    # 重新生成上檐
    buildFloor.buildFloor(doubleEaveRoot)

    return

# 设置重檐数据
def setDoubleEaveData(doubleEaveObj:bpy.types.Object):
    # 初始化数据集
    # 重檐
    bData:acaData = doubleEaveObj.ACA_data
    # 主建筑
    mainBuildingObj = utils.getMainBuilding(doubleEaveObj)
    mData:acaData = mainBuildingObj.ACA_data

    # 1、主建筑(下檐)数据更新 -----------------------------
    mData['use_double_eave'] = True
    # 分层显示控制
    mData['is_showPlatform'] = True
    mData['is_showPillers'] = True
    mData['is_showWalls'] = True
    mData['is_showDougong'] = True
    mData['is_showBeam'] = True
    mData['is_showRafter'] = True
    mData['is_showTiles'] = True

    # 主建筑改用盝顶
    mData['roof_style'] = int(con.ROOF_LUDING)
    
    # 主建筑在面阔、进深扩展一廊间
    mData['x_rooms'] = bData['x_rooms'] + 2
    mData['y_rooms'] = bData['y_rooms'] + 2
    # 地盘变化后，柱网、踏跺、墙体、额枋都需要重置
    mData['piller_net'] = ''
    mData['step_net'] = ''
    mData['wall_net'] = ''
    mData['fang_net'] = ''

    # 设置廊间宽度,22DK
    hallway_deepth = mData.DK * con.HALLWAY_DEEPTH
    mData['luding_rafterspan'] = hallway_deepth
    if mData.x_rooms <= 3:
        mData['x_2'] = hallway_deepth
    elif mData.x_rooms <= 5:
        mData['x_3'] = hallway_deepth
    else:
        mData['x_4'] = hallway_deepth
    
    if mData.y_rooms <= 3:
        mData['y_2'] = hallway_deepth
    else:
        mData['y_3'] = hallway_deepth

    # 主建筑内部柱网全部减柱


    
    # 2、重檐（上檐）数据更新 ----------------------------    
    bData['use_double_eave'] = True
    bData['combo_type'] = con.COMBO_DOUBLE_EAVE
    # 分层显示控制
    bData['is_showPillers'] = True
    bData['is_showWalls'] = True
    bData['is_showDougong'] = True
    bData['is_showBeam'] = True
    bData['is_showRafter'] = True
    bData['is_showTiles'] = True

    # 上檐不做台基，复用下檐台基
    bData['is_showPlatform'] = False    
    # 上檐不做踏跺
    bData['step_net'] = ''

    # 柱高抬升
    bData['piller_height'] += 2.0
    
    return

# 取消重檐
def doubleEaveDel(buildingObj:bpy.types.Object):
    print("取消重檐")
    bData:acaData = buildingObj.ACA_data
    bData['use_double_eave'] = False
    return