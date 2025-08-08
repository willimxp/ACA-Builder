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
    mainBuildingObj = utils.getMainBuilding(buildingObj)

    # 判断全局更新还是局部更新
    if comboObj == buildingObj:
        # 选中combo根节点时，全局更新
        isUpdateAll = True
    elif mainBuildingObj == buildingObj:
        # 选中主建筑时，全局更新
        isUpdateAll = True
    else:
        # 局部更新
        isUpdateAll = False
    
    # 全局更新时，
    if isUpdateAll:
        # 立即界面刷新，全部删除重做
        for childBuilding in comboObj.children:
            utils.deleteHierarchy(childBuilding)
    
        # 所有子建筑从主建筑同步数据
        __syncChildData(buildingObj,
                    isAll=True,)

    # 重檐数据更新
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE)
    if doubleEaveObj is not None:
        __setDoubleEaveData(doubleEaveObj)

    # 月台数据更新
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    if terraceObj is not None:
        __setTerraceData(terraceObj,
                         isInit=isUpdateAll # 全局更新时重新初始化
                         )            
        
    # 循环生成各个单体
    for childBuilding in comboObj.children:
        # 局部更新
        if not isUpdateAll:
            if childBuilding != buildingObj:
                continue
        
        # 区分是否重做地盘
        if reset:
            buildFloor.resetFloor(childBuilding,
                comboObj=comboObj)
        else:
            buildFloor.buildFloor(childBuilding,
                    reloadAssets=reloadAssets,
                    comboObj=comboObj)

# 组合建筑降级为单一建筑
def delCombo(buildingObj:bpy.types.Object):
    comboObj = utils.getComboRoot(buildingObj)
    
    if comboObj is None:
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
# 调用方：addTerrace,doubleEaveadd,updateCombo
# syncKeys限制同步的键值范围，None即全部拷贝
def __syncChildData(buildingObj:bpy.types.Object,
                  isInit = False, # 是否初始同步，区分新建和更新建筑的调用
                  isAll = False, # 是否同步combo下的所有子建筑
                  ):
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
        'x_rooms',
        'y_rooms',
    ]

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
        
        # 默认只同步buildingObj
        if not isAll:
            if childBuilding != buildingObj:
                continue

        if isInit:
            # 新建时，全量同步
            keys = None
        else:
            # 更新时，小范围同步
            skip = None

        # 其他子建筑都要从主建筑同步
        utils.copyAcaData(
            fromObj = mainBuildingObj,
            toObj = childBuilding,
            keys = keys,
            skip = skip,
        )
    return

# 添加月台
# 传入主建筑，在主建筑上添加月台
def addTerrace(buildingObj:bpy.types.Object):
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
    __syncChildData(terraceRoot,isInit=True)
    # 设置月台逻辑数据
    __setTerraceData(terraceRoot)
    
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
def delTerrace(buildingObj:bpy.types.Object):
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

    # 是否需要组合降级
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
# 在addTerrace和__syncChildData中复用
def __setTerraceData(terraceObj:bpy.types.Object,
                     isInit = False, # 初始化标识，区分是新建还是更新
                     ):
    # 初始化数据集
    # 月台数据集
    bData:acaData = terraceObj.ACA_data
    # 主建筑数据集
    mainBuildingObj = utils.getMainBuilding(terraceObj)
    mData:acaData = mainBuildingObj.ACA_data
    
    # 0、基本属性标注 ------------------------
    mData['use_terrace'] = True
    bData['use_terrace'] = True
    bData['combo_type'] = con.COMBO_TERRACE

    # 1、分层显示控制 --------------------------
    # 分层显示控制
    bData['is_showPlatform'] = True
    bData['is_showPillers'] = True
    bData['is_showWalls'] = False
    bData['is_showDougong'] = False
    bData['is_showBeam'] = False
    bData['is_showRafter'] = False
    bData['is_showTiles'] = False
    
    # 2、仅在新建时的初始化处理，更新时跳过 -------------
    if isInit:
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
    
        # 矫正梢间，不使用主建筑的廊间数据
        if mData.use_double_eave:
            if bData.x_rooms >= 7:
                bData['x_4'] = mData.x_3
                bData['x_3'] = mData.x_2
    
    # 3、月台定位 ------------------------
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
def addDoubleEave(buildingObj:bpy.types.Object):
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
    doubleEaveName = buildingObj.ACA_data.template_name + '.重檐'
    # 找到根目录
    rootColl = utils.setCollection(
        name = con.COLL_NAME_ROOT,
        isRoot=True,
        colorTag=2,
        )
    # 创建重檐目录
    doubleEaveColl = utils.setCollection(
        name = doubleEaveName,
        isRoot=True,
        colorTag=2,
        )
    # 创建重檐根节点
    doubleEaveRoot = buildFloor.__addBuildingRoot(
        templateName = doubleEaveName,
        comboObj = comboObj
    )
    # 立即设置combo_type，否则后续可能在区分combo_main时混乱
    doubleEaveRoot.ACA_data['combo_type'] = con.COMBO_DOUBLE_EAVE

    # 2、构造重檐数据集 ----------------------
    # 初始化上檐数据，继承了主建筑的原始地盘/装修/屋顶等设定
    __syncChildData(doubleEaveRoot,isInit=True)

    # 设置重檐逻辑数据
    # 包括下檐的廊间扩展、盝顶
    # 包括上檐的柱高抬升
    __setDoubleEaveData(doubleEaveRoot,
                      isInit=True, # 标识初始化
                      )

    # 3、开始营造 ------------------------------
    from . import build
    build.isFinished = False
    build.progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    build.__excludeOther(rootColl,True,buildingObj)

    # 如果有月台，则联动重新生成月台（地盘变化了）
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    if terraceObj is not None:
        __syncChildData(terraceObj)
        __setTerraceData(terraceObj)
        buildFloor.buildFloor(
            terraceObj,
            comboObj=comboObj # 传入combo以便及时更新位置
            )
    
    # 重新生成主建筑
    buildFloor.buildFloor(buildingObj)

    # 重新生成上檐
    buildFloor.buildFloor(doubleEaveRoot)

    build.isFinished = True
    # 取消排除目录下的其他建筑
    build.__excludeOther(rootColl,False,buildingObj)

    return

# 取消重檐
def delDoubleEave(buildingObj:bpy.types.Object):
    # 重檐对象
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE
    )
    # 主建筑对象
    mainBuilding = utils.getComboChild(
        buildingObj,con.COMBO_MAIN
    )
    # combo根对象
    comboObj = utils.getComboRoot(buildingObj)

    # 反向处理combo数据
    __undoDoubleEaveData(buildingObj)

    # 删除重檐对象
    if doubleEaveObj is not None:
        from . import build
        build.delBuilding(doubleEaveObj,
            withCombo=False,# 仅删除个体
        )

    from . import build
    build.isFinished = False
    build.progress = 0
    rootColl = utils.setCollection(
        name = con.COLL_NAME_ROOT,
        isRoot=True,
        colorTag=2,
        )
    # 暂时排除目录下的其他建筑，以加快执行速度
    build.__excludeOther(rootColl,True,mainBuilding)

    # 重建主建筑    
    if mainBuilding is not None:
        buildFloor.buildFloor(mainBuilding,
                        comboObj=comboObj)
    
    build.isFinished = True
    # 取消排除目录下的其他建筑
    build.__excludeOther(rootColl,False,mainBuilding)
    
    # 是否需要组合降级
    from . import build
    delCombo(mainBuilding)

    # 聚焦主建筑
    utils.focusObj(mainBuilding)

    return

# 设置重檐数据
def __setDoubleEaveData(doubleEaveObj:bpy.types.Object,
                    isInit = False, # 初始化标识，区分是新建还是更新
                    ):
    # 初始化数据集
    # 重檐数据（上檐）
    bData:acaData = doubleEaveObj.ACA_data
    # 主建筑数据（下檐）
    mainBuildingObj = utils.getMainBuilding(doubleEaveObj)
    mData:acaData = mainBuildingObj.ACA_data

    # 0、基本属性标注 ------------------------
    mData['use_double_eave'] = True
    bData['use_double_eave'] = True
    bData['combo_type'] = con.COMBO_DOUBLE_EAVE
       
    # 1、分层显示控制 -------------------------
    # 下檐分层显示
    # mData['is_showPlatform'] = True
    # mData['is_showPillers'] = True
    # mData['is_showWalls'] = True
    # mData['is_showDougong'] = True
    # mData['is_showBeam'] = True
    # mData['is_showRafter'] = True
    # mData['is_showTiles'] = True    
    # 上檐分层显示
    bData['is_showPlatform'] = False    # 上檐不做台基，复用下檐台基
    # bData['is_showPillers'] = True
    # bData['is_showWalls'] = True
    # bData['is_showDougong'] = True
    # bData['is_showBeam'] = True
    # bData['is_showRafter'] = True
    # bData['is_showTiles'] = True

    # 2、重檐做法 ------------------------------
    # 2.1、地盘控制
    # 第一次新建时，采用下檐主动扩展的做法
    if isInit:
        # 主建筑在面阔、进深扩展一廊间
        mData['x_rooms'] = bData['x_rooms'] + 2
        mData['y_rooms'] = bData['y_rooms'] + 2
        # 地盘变化后，柱网、踏跺、墙体、额枋都需要重置
        mData['piller_net'] = ''
        mData['step_net'] = ''
        mData['wall_net'] = ''
        mData['fang_net'] = ''
    # 建筑更新，采用上檐被动的缩减1廊间
    else:
        # 将用户通过UI修改的主建筑地盘，同步到combo下所有对象
        # 包括上檐、月台等
        __syncChildData(doubleEaveObj,isAll=True)

        # 主建筑在面阔、进深缩减一廊间
        bData['x_rooms'] = mData['x_rooms'] - 2
        bData['y_rooms'] = mData['y_rooms'] - 2

    # 设置廊间宽度,22DK
    hallway_deepth = mData.DK * con.HALLWAY_DEEPTH
    mData['luding_rafterspan'] = hallway_deepth
    if mData.x_rooms <= 3:
        mData['x_2'] = hallway_deepth
    elif mData.x_rooms <= 5:
        mData['x_3'] = hallway_deepth
        if mData['x_2'] == hallway_deepth:
            mData['x_2'] = mData['x_1']
    else:
        mData['x_4'] = hallway_deepth
        if mData['x_3'] == hallway_deepth:
            mData['x_3'] = mData['x_2']
    if mData.y_rooms <= 3:
        mData['y_2'] = hallway_deepth
    else:
        mData['y_3'] = hallway_deepth
        if mData['y_2'] == hallway_deepth:
            mData['y_2'] = mData['y_1']
    # 矫正梢间，不使用主建筑的廊间数据
    if mData.use_double_eave:
        if bData.x_rooms >= 7:
            bData['x_4'] = mData.x_3
            bData['x_3'] = mData.x_2

    # 2.2、柱网控制
    # 主建筑内部柱网全部减柱
    x_rooms = mData.x_rooms   # 面阔几间
    y_rooms = mData.y_rooms   # 进深几间
    pillerNet = ''
    for y in range(y_rooms + 1):
        for x in range(x_rooms + 1):
            if x in (0,x_rooms) or y in (0,y_rooms):
                pillerID = f"{x}/{y},"
                pillerNet += pillerID
    mData['piller_net'] = pillerNet

    # 2.3、上檐柱高抬升
    doubleEaveLift = __getDoubleEaveLift(doubleEaveObj)
    
    # 应用上檐柱高
    bData['piller_height'] = (mData.piller_height 
                              + doubleEaveLift)
    
    # 2.4、装修层设置跑马板
    bData['wall_span'] = doubleEaveLift
    
    # 2.5、主建筑改用盝顶
    mData['roof_style'] = int(con.ROOF_LUDING)
    
    return

# 移除重檐数据
def __undoDoubleEaveData(buildingObj:bpy.types.Object):
    # 1、数据回传 -----------------------
    # 传递数据回主建筑
    # 属性跳过，保持柱高，保持跑马板高度
    skip = ['piller_height',
            'wall_span',]
    
    # 重檐数据（上檐）
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE
    )
    # 主建筑数据（下檐）
    mainBuildingObj = utils.getComboChild(
        buildingObj,con.COMBO_MAIN
    )
    # 数据传递
    utils.copyAcaData(
            fromObj = doubleEaveObj,
            toObj = mainBuildingObj,
            skip=skip)
    
    # 2、标识位更新 ----------------------------
    mData:acaData = mainBuildingObj.ACA_data
    # 主建筑标识
    mData['combo_type'] = con.COMBO_MAIN
    # 重檐标识(取消)
    mData['use_double_eave'] = False
    # 显示台基
    mData['is_showPlatform'] = True
    
    return

# 计算重檐抬升高度
def __getDoubleEaveLift(buildingObj:bpy.types.Object):
    # 主建筑数据（下檐）
    mainBuildingObj = utils.getComboChild(
        buildingObj,con.COMBO_MAIN
    )
    mData:acaData = mainBuildingObj.ACA_data
    pillerLift = 0.0
    dk = mData.DK

    if mData.use_dg:
        # 平板枋
        if mData.use_pingbanfang:
            pillerLift += con.PINGBANFANG_H*dk
        # 斗栱高度(dg_height已经按dg_Scale放大了)
        pillerLift += mData.dg_height
    else:
        # 以大梁抬升檐桁垫板高度，即为挑檐桁下皮位置
        pillerLift += con.BOARD_YANHENG_H*dk

    # 挑檐桁(斗栱高度到挑檐桁下皮)
    pillerLift += con.HENG_COMMON_D*dk

    # 檐椽架加斜
    netX,netY = buildFloor.getFloorDate(mainBuildingObj)
    hallway = netY[1] - netY[0]
    from . import buildBeam
    lift_radio = buildBeam.getLiftRatio(mainBuildingObj)
    # （廊间+出跳）加斜
    pillerLift += (hallway + mData.dg_extend) * lift_radio[0]

    # 屋瓦层抬升
    pillerLift += (con.YUANCHUAN_D*dk   # 椽架
                   + con.WANGBAN_H*dk   # 望板
                   + con.ROOFMUD_H*dk   # 灰泥
                   )
    
    # 盝顶围脊高度
    aData = bpy.context.scene.ACA_temp
    ridgeObj:bpy.types.Object = aData.ridgeBack_source
    ridgeH = ridgeObj.dimensions.z
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = mData.DK / con.DEFAULT_DK  * mData.tile_scale
    ridgeH = ridgeH * tileScale
    pillerLift += ridgeH
    pillerLift -= con.RIDGE_SURR_OFFSET*dk   # 围脊调整

    # 额枋高度
    # 大额枋
    pillerLift += con.EFANG_LARGE_H*dk
    if mData.use_smallfang:
        # 由额垫板
        pillerLift += con.BOARD_YOUE_H*dk
        # 小额枋
        pillerLift += con.EFANG_SMALL_H*dk
    
    return pillerLift