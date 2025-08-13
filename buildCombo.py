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
from . import buildRoof

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
    cData['combo_type'] = con.COMBO_ROOT

    return comboObj

# 基于单一建筑，添加组合建筑
def __addComboLevel(buildingObj:bpy.types.Object):
    # 校验建筑为单一建筑
    buildingObj,bData,objData = utils.getRoot(buildingObj)
    comboObj = utils.getComboRoot(buildingObj)
    if comboObj is not None:
        raise Exception("__addComboLevel失败，已经为组合建筑。")
        
    # ACA根目录
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

    # 数据上传到comboRoot
    # 放在层级结构生成后再处理数据，否则可能找不到combo节点
    utils.outputMsg("添加组合根节点...")
    __uploadData(fromBuilding=buildingObj)

    return comboObj

def buildCombo(
        templateName,
):
    # 添加combo根节点
    comboObj = __addComboRoot(templateName)
    # 在comboObj上绑定模板bData
    template.loadTemplate(comboObj)
    
    # 组合建筑
    tempChildren = template.getTemplateChild(templateName)
    for child in tempChildren:
        from . import build
        build.buildSingle(
            acaType = child['acaType'],
            templateName = child['templateName'],
            comboObj = comboObj
        )
    return {'FINISHED'}

# 刷新组合建筑
def updateCombo(buildingObj:bpy.types.Object,
                reloadAssets=False,
                resetFloor=False,
                resetRoof=False,):
    comboObj = utils.getComboRoot(buildingObj)
    bData:acaData = buildingObj.ACA_data
    doubleEaveType = (con.COMBO_MAIN,
                      con.COMBO_DOUBLE_EAVE,)
    # 更新的对象范围
    updateBuildingList = []

    # 如果基于combo根节点，全部更新
    # 用户点击“更新建筑”时会传入根节点，或激活再根节点上的修改
    if bData.aca_type == con.ACA_TYPE_COMBO:
        updateBuildingList = comboObj.children
    # 如果基于重檐的上檐或下檐
    elif bData.combo_type in doubleEaveType:
        # 全部更新，重檐柱网变化应该传递到月台
        updateBuildingList = comboObj.children
    # 其他子建筑，如，月台，独立更新
    else:
        updateBuildingList.append(buildingObj)

    # ComboRoot通用数据下发
    # 通用数据是通过panel暴露在combo层次的属性
    # 包括DK，roof_style，paint_style，梁架/椽架/瓦作层数据
    # 不包括地盘、台基、装修、斗栱的数据
    utils.outputMsg("更新组合建筑：ComboRoot【通用数据】下发...")
    for child in comboObj.children:
        __downloadCommonData(toBuilding=child)

    # 主建筑数据同步，先上传到comboRoot，再下发到重檐对象
    # 主建筑数据是通过panel暴露在mainBuilding层次的属性
    utils.outputMsg("更新组合建筑：MainBuilding【通用数据】上传...")
    __syncMainData(toBuilding=comboObj)

    # 重檐数据更新
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE)
    if doubleEaveObj is not None:
        utils.outputMsg("更新组合建筑：MainBuilding【通用数据】下发...")
        __syncMainData(toBuilding=doubleEaveObj)
        __setDoubleEaveData(doubleEaveObj)

    # 月台数据更新
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    # 跟随重檐变化
    if bData.combo_type in doubleEaveType:
        initTerrace = True
    else:
        initTerrace = False
    if terraceObj is not None:
        utils.outputMsg("更新组合建筑：MainBuilding【通用数据】下发...")
        __syncMainData(toBuilding=terraceObj)
        __setTerraceData(terraceObj,
                         isInit=initTerrace
                         )         

    # 立即刷新界面
    for childBuilding in updateBuildingList:
        # 重建屋顶时，仅清除屋顶
        if resetRoof:
            buildRoof.__clearRoof(childBuilding)
        # 否则全部清除
        else:
            utils.deleteHierarchy(childBuilding)   
        
    # 循环生成各个单体
    for childBuilding in updateBuildingList:
        # 重做地盘
        if resetFloor:
            buildFloor.resetFloor(childBuilding,
                comboObj=comboObj)
        # 重做屋顶
        if resetRoof:
            buildRoof.buildRoof(childBuilding)
        # 全部重做
        else:
            buildFloor.buildFloor(childBuilding,
                    reloadAssets=reloadAssets,
                    comboObj=comboObj)

# 组合建筑降级为单一建筑
def __delComboLevel(comboObj:bpy.types.Object):
    # 输入验证
    comboObj = utils.getComboRoot(comboObj)
    if comboObj is None:
        utils.outputMsg("删除组合建筑失败，不是组合建筑。")
        return
    
    # 是否只剩一个建筑？
    if len(comboObj.children) > 1:
        utils.outputMsg("删除组合建筑失败，不止一个建筑存在。")
        return
    
    # 更改目录级别
    mainBuilding = utils.getMainBuilding(comboObj)
    buildingColl = mainBuilding.users_collection[0]
    # 关联到根目录
    rootColl = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
    rootColl.children.link(buildingColl)
    # 删除父集合
    comboColl = comboObj.users_collection[0]
    comboColl.children.unlink(buildingColl)
    bpy.data.collections.remove(comboColl)    

    # 删除父节点
    mainBuilding.parent = None
    # 更改映射
    mainBuilding.matrix_world = comboObj.matrix_world.copy()
    utils.delObject(comboObj)

    return

# 建筑间的数据同步
def __syncData(fromBuilding:bpy.types.Object,
               toBuilding:bpy.types.Object,
               syncAll = True,  # 默认同步所有，使用defaultSkipKeys
               syncKeys = None, # 同步的字段
               skipKeys = None, # 跳过的字段
               ):
    utils.outputMsg(f"-- syncData fromBuilding={fromBuilding.name},toBuilding={toBuilding.name},syncAll={syncAll},syncKeys={syncKeys},skipKeys={skipKeys}")
    defaultSkipKeys = [
                'aca_type',
                'combo_type',
                'is_showPlatform',
                'is_showPillers',
                'is_showWalls',
                'is_showDougong',
                'is_showBeam',
                'is_showRafter',
                'is_showTiles',
                # 250812 重檐上檐需要同步pillernet，
                # 所以默认的数据上传需要上传这些字段
                # 月台不需要pillernet，不要用这个skip
                # 'step_net',
                # 'piller_net',
                # 'wall_net',
                # 'fang_net',
            ]
    defaultSyncKeys = [
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
    
    # 除了skipKeys同步其他所有字段
    if syncAll:
        if skipKeys is not None:
            # 跳过以下字段，同步其他所有字段
            skipKeys += defaultSkipKeys
        else:
            skipKeys = defaultSkipKeys
    # 只同步syncKeys
    else:
        if syncKeys is not None:
            syncKeys += defaultSyncKeys
        else:
            syncKeys = defaultSyncKeys
    
    # 拷贝字段
    utils.copyAcaData(
        fromObj = fromBuilding,
        toObj = toBuilding,
        keys = syncKeys,
        skip = skipKeys,
    )

    return

# 添加月台
# 传入主建筑，在主建筑上添加月台
def addTerrace(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox("不能添加月台，只有主体建筑可以添加月台")
        return {'CANCELLED'}
    
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
        return {'CANCELLED'}

    # 构建月台子节点
    terraceRoot = buildFloor.__addBuildingRoot(
        templateName = buildingObj.ACA_data.template_name + '.月台',
        comboObj = comboObj
    ) 
    # 务必及时标注combo_type,后续的数据同步和数据设置时都要判断主建筑
    terraceRoot.ACA_data['combo_type'] = con.COMBO_TERRACE
    
    # 2、构造月台数据集 --------------------------
    # 从Combo根节点继承数据
    utils.outputMsg("添加月台子建筑...")
    __downloadData(toBuilding=terraceRoot)
    # 设置月台逻辑数据
    __setTerraceData(terraceRoot,isInit=True)
    
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
        from . import build
        build.delBuilding(terraceObj,
            withCombo=False,# 仅删除个体
        )

    # 预先找到主建筑，否则下一步删除comboRoot以后就找不到了
    mainBuilding = utils.getMainBuilding(comboObj)

    # 是否需要组合降级
    from . import build
    __delComboLevel(comboObj)

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
def __setTerraceData(terraceObj:bpy.types.Object,
                     isInit = False, # 初始化标识，区分是新建还是更新
                     ):
    # 初始化数据集
    # 月台数据集
    bData:acaData = terraceObj.ACA_data
    # 主建筑数据集
    mainBuildingObj = utils.getMainBuilding(terraceObj)
    mData:acaData = mainBuildingObj.ACA_data
    # comboRoot数据集
    comboObj = utils.getComboRoot(terraceObj)
    cData:acaData = comboObj.ACA_data
    
    # 1、分层显示控制 --------------------------
    # 分层显示控制
    bData['is_showPlatform'] = True
    bData['is_showPillers'] = True
    bData['is_showWalls'] = False
    bData['is_showDougong'] = False
    bData['is_showBeam'] = False
    bData['is_showRafter'] = False
    bData['is_showTiles'] = False
    
    # 2、月台开间与主建筑联动 -------------
    # 月台进深，五间以上减2间
    yRooms = cData.y_rooms
    if cData.use_double_eave:
        # 重檐不考虑廊间
        yRooms -= 2
    if yRooms > 2:
        bData['y_rooms'] = yRooms - 2
    else:
        bData['y_rooms'] = yRooms

    # 月台面阔，五间以上做“凸”形月台，减2间
    xRooms = cData.x_rooms
    if cData.use_double_eave:
        # 重檐不考虑廊间
        xRooms -= 2
    if xRooms > 5:
        bData['x_rooms'] = xRooms - 2
    else:
        bData['x_rooms'] = xRooms

    # 矫正梢间，不使用主建筑的廊间数据
    if cData.use_double_eave:
        if bData.x_rooms >= 7:
            bData['x_4'] = cData.x_3
            bData['x_3'] = cData.x_2
    
    # 月台高度，比主体低1踏步
    bData['platform_height'] = (
        cData.platform_height - con.STEP_HEIGHT)
    # 月台下出，比主体窄2踏步（未见规则）
    bData['platform_extend'] = (
        cData.platform_extend 
        - con.STEP_HEIGHT*2
        )
    
    # 3、月台定位 ------------------------
    # 更新地盘数据，计算当前的y_total
    buildFloor.getFloorDate(mainBuildingObj)
    buildFloor.getFloorDate(terraceObj)
    offsetY = (cData.y_total/2 
               + cData.platform_extend
               + bData.y_total/2 
               + bData.platform_extend
               )
    terraceLoc = Vector((0,-offsetY,0))
    bData['root_location'] = terraceLoc

    # 4、仅在新建时的初始化处理，更新时跳过 -------------
    if isInit:
        # 基本属性标注
        bData['use_terrace'] = True
        mData['use_terrace'] = True
        
        # 不做踏跺
        bData['step_net'] = ''
        # 柱网仅显示定位点
        bData['piller_net'] = con.ACA_PILLER_HIDE
        # 不做额枋
        bData['fang_net'] = ''
        # 不做墙体
        bData['wall_net'] = ''
        
        # 这里不要上报了，仅仅为了use_terrace
        # 反而导致roof_style被覆盖
        # # 数据上报到combo ------------------------
        # utils.outputMsg("月台数据修改上报...")
        # __uploadData(fromBuilding=mainBuildingObj)

    return terraceObj

# 添加重檐
def addDoubleEave(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 验证是否为主体建筑
    if buildingObj.ACA_data.roof_style in (
                                con.ROOF_YINGSHAN,
                                con.ROOF_YINGSHAN_JUANPENG,):
        utils.popMessageBox("硬山屋顶不能添加重檐，请使用庑殿、歇山、悬山等屋顶样式")
        return {'CANCELLED'}
    
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox("请先选择主体建筑，只有主体建筑可以添加重檐")
        return {'CANCELLED'}
    
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
        return {'CANCELLED'}

    # 构建重檐子节点
    doubleEaveName = buildingObj.ACA_data.template_name + '.重檐'
    # 创建重檐根节点
    doubleEaveRoot = buildFloor.__addBuildingRoot(
        templateName = doubleEaveName,
        comboObj = comboObj
    )
    # 务必及时标注combo_type,后续的数据同步和数据设置时都要判断主建筑
    doubleEaveRoot.ACA_data['combo_type'] = con.COMBO_DOUBLE_EAVE

    # 2、构造重檐数据集 ----------------------
    # 初始化上檐数据，继承ComboRoot数据
    # 包括主建筑的原始地盘/装修/屋顶等设定
    utils.outputMsg("添加重檐子建筑...")
    __downloadData(toBuilding=doubleEaveRoot)
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
    build.__excludeOther(keepObj=buildingObj)

    # 如果有月台，则联动重新生成月台（地盘变化了）
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    if terraceObj is not None:
        utils.outputMsg("重檐联动月台更新...")
        # 不要同步柱网piller_net，保持为隐藏柱网状态
        __downloadData(toBuilding=terraceObj,
                       skipKeys=['piller_net',])
        __setTerraceData(terraceObj)
        buildFloor.buildFloor(
            terraceObj,
            comboObj=comboObj # 传入combo以便及时更新位置
            )
    
    # 重新生成主建筑
    buildFloor.buildFloor(buildingObj)

    # 重新生成上檐
    buildFloor.buildFloor(doubleEaveRoot)

    # 关闭进度条
    build.isFinished = True
    # 取消排除目录下的其他建筑
    build.__excludeOther(isExclude=False,
                         keepObj=buildingObj)

    return {'FINISHED'}

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

    # 显示进度条
    from . import build
    build.isFinished = False
    build.progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    build.__excludeOther(keepObj=mainBuilding)

    # 重建月台
    terraceObj = utils.getComboChild(
        mainBuilding,con.COMBO_TERRACE)
    if terraceObj is not None:
        # __setTerraceData(terraceObj,
        #                  isInit=True # 重建月台地盘
        #                  )
        # 250812 似乎没有必须重新初始化
        __setTerraceData(terraceObj)

        buildFloor.buildFloor(terraceObj,
                        comboObj=comboObj)
    
    # 重建主建筑    
    if mainBuilding is not None:
        buildFloor.buildFloor(mainBuilding,
                        comboObj=comboObj)
    
    # 关闭进度条
    build.isFinished = True
    # 取消排除目录下的其他建筑
    build.__excludeOther(isExclude=False,
                         keepObj=mainBuilding)
    
    # 是否需要组合降级
    from . import build
    __delComboLevel(mainBuilding)

    # 聚焦主建筑
    utils.focusObj(mainBuilding)

    return {'FINISHED'}

# 设置重檐数据
# 先分别设置上下檐数据，然后汇总到comboRoot中
def __setDoubleEaveData(doubleEaveObj:bpy.types.Object,
                    isInit = False, # 初始化标识，区分是新建还是更新
                    ):
    # 初始化数据集
    # 重檐数据（上檐）
    bData:acaData = doubleEaveObj.ACA_data
    # 主建筑数据集
    mainBuildingObj = utils.getMainBuilding(doubleEaveObj)
    mData:acaData = mainBuildingObj.ACA_data
    # comboRoot根节点
    comboObj = utils.getComboRoot(doubleEaveObj)
    cData:acaData = comboObj.ACA_data

    # 0、基本属性标注 ------------------------
    bData['use_double_eave'] = True
    mData['use_double_eave'] = True
       
    # 1、分层显示控制 -------------------------
    # 上檐不做台基，复用下檐台基
    bData['is_showPlatform'] = False    

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
        # 主建筑在面阔、进深缩减一廊间
        bData['x_rooms'] = mData['x_rooms'] - 2
        bData['y_rooms'] = mData['y_rooms'] - 2

    # 设置廊间宽度,22DK
    hallway_deepth = mData.DK * con.HALLWAY_DEEPTH
    # 下檐盝顶檐步进深
    mData['luding_rafterspan'] = hallway_deepth
    # 下檐面阔廊间宽度
    if mData.x_rooms <= 3:
        mData['x_2'] = hallway_deepth
    elif mData.x_rooms <= 5:
        mData['x_3'] = hallway_deepth
        if mData['x_2'] == hallway_deepth:
            mData['x_2'] = mData['x_1'] - 11*mData.DK
    else:
        mData['x_4'] = hallway_deepth
        if mData['x_3'] == hallway_deepth:
            mData['x_3'] = mData['x_2']
    # 下檐进深廊间面阔
    if mData.y_rooms <= 3:
        mData['y_2'] = hallway_deepth
    else:
        mData['y_3'] = hallway_deepth
        if mData['y_2'] == hallway_deepth:
            mData['y_2'] = mData['y_1']
    # 矫正上檐的次间、梢间，不使用主建筑的廊间数据
    if mData.use_double_eave:
        # 上檐面阔同步
        if bData.x_rooms >= 3:
            bData['x_2'] = mData.x_2
        if bData.x_rooms >= 5:
            bData['x_3'] = mData.x_3
        if bData.x_rooms >= 7:
            bData['x_4'] = mData.x_3
            bData['x_3'] = mData.x_2
        # 上檐进深同步
        if bData.y_rooms >= 5:
            bData['y_3'] = mData.y_2

    # 2.2、上檐柱高抬升
    doubleEaveLift = __getDoubleEaveLift(doubleEaveObj)
    # 应用上檐柱高
    bData['piller_height'] = (mData.piller_height 
                              + doubleEaveLift)
    
    # 2.3、装修层设置跑马板
    bData['wall_span'] = doubleEaveLift
    
    # 2.4、主建筑改用盝顶
    mData['roof_style'] = int(con.ROOF_LUDING)
    
    # 3、数据汇总到combo ------------------------
    # 绝大部分数据从下檐采集
    utils.outputMsg("重檐数据修改上报...")
    __uploadData(fromBuilding=mainBuildingObj)

    # 这里上报的时候会把盝顶写入comboRoot，导致后续更新时再下发
    # 所以，需要改写上报数据
    # ComboRoot记录的屋顶类型不继承主建筑，而是使用上檐的屋顶类型
    cData['roof_style'] = bData['roof_style']
    
    return

# 移除重檐数据
def __undoDoubleEaveData(buildingObj:bpy.types.Object):
    # 1、数据回传 -----------------------
    # 重檐数据（上檐）
    doubleEaveObj = utils.getComboChild(
        buildingObj,con.COMBO_DOUBLE_EAVE
    )
    # 主建筑数据（下檐）
    mainBuildingObj = utils.getComboChild(
        buildingObj,con.COMBO_MAIN
    )
    # 数据传递，保持柱高，保持跑马板高度
    utils.outputMsg("重檐移除，上檐数据传给下檐...")
    skipKeys = ['piller_height','wall_span',]
    __syncData(fromBuilding=doubleEaveObj,
               toBuilding=mainBuildingObj,
               skipKeys=skipKeys)
    
    # 2、标识位更新 ----------------------------
    mData:acaData = mainBuildingObj.ACA_data
    # 主建筑标识
    mData['combo_type'] = con.COMBO_MAIN
    # 显示台基
    mData['is_showPlatform'] = True
    mData['use_double_eave'] = False

    # 3、数据汇总到combo ------------------------
    comboObj = utils.getComboRoot(buildingObj)
    cData:acaData = comboObj.ACA_data
    # 下檐数据上报
    utils.outputMsg("重檐移除，下檐数据上报...")
    __uploadData(fromBuilding=mainBuildingObj)
    
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
        # 更新斗栱数据，以免修改DK，斗栱类型等操作时未及时更新
        # reloadAssets=False，以免重复载入重复的斗栱资产
        from . import template
        template.updateDougongData(mainBuildingObj,
                                   reloadAssets=False)
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
    # 廊间宽度加斜
    pillerLift += hallway * lift_radio[0]
    if mData.use_dg:
        # 斗栱出跳加斜
        pillerLift += mData.dg_extend * lift_radio[0]

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

# 将建筑数据上传至comboRoot根节点
# 调用方：
# __addComboLevel：组合建筑初始化时，将主建筑数据上传comboRoot
# __setTerraceData：月台创建后，对主建筑修改(添加use_terrace标识)，需要更新到comboRoot
# updateCombo：重檐修改后，及时更新comboRoot
def __uploadData(fromBuilding:bpy.types.Object):
    # 跳过的字段
    skipKeys = [
                'aca_type',
                'combo_type',
                'is_showPlatform',
                'is_showPillers',
                'is_showWalls',
                'is_showDougong',
                'is_showBeam',
                'is_showRafter',
                'is_showTiles',
                # 250812 comboRoot中需要与主建筑同步pillernet
                # 子建筑可以自行决定是否要继承该柱网，
                # 如，月台初始化时继承，修改更新时不继承，
                # 如，重檐上檐始终继承
                # 'step_net',
                # 'piller_net',
                # 'wall_net',
                # 'fang_net',
                # 'roof_style',   # 250812 不上传屋顶类型，将始终保留继承的主建筑屋顶类型
            ]
    
    utils.outputMsg(f"-- Upload Data from [{fromBuilding.name}]...")
    comboObj = utils.getComboRoot(fromBuilding)
    # 拷贝字段
    utils.copyAcaData(
        fromObj = fromBuilding,
        toObj = comboObj,
        skip = skipKeys,
    )

    return

# 从comboRoot下载数据，各个子建筑再决定如何二次加工
# 调用方：
# addTerrace,新建月台时从comboRoot初始化，但后续就数据独立了
def __downloadData(toBuilding:bpy.types.Object,
                   skipKeys = None):
    # 跳过的字段
    defaultSkipKeys = [
                'aca_type',
                'combo_type',
                'is_showPlatform',
                'is_showPillers',
                'is_showWalls',
                'is_showDougong',
                'is_showBeam',
                'is_showRafter',
                'is_showTiles',
                # 250812 comboRoot中需要与主建筑同步pillernet
                # 子建筑可以自行决定是否要继承该柱网，
                # 如，月台初始化时继承，修改更新时不继承，
                # 如，重檐上檐始终继承
                # 'step_net',
                # 'piller_net',
                # 'wall_net',
                # 'fang_net',
            ]
    
    if skipKeys is None:
        skipKeys = defaultSkipKeys
    else:
        skipKeys += defaultSkipKeys
    
    utils.outputMsg(f"-- Download data to [{toBuilding.name}]...")
    comboObj = utils.getComboRoot(toBuilding)
    # 拷贝字段
    utils.copyAcaData(
        fromObj = comboObj,
        toObj = toBuilding,
        skip = skipKeys,
    )

    return

# 从comboRoot下载通用数据，以反映用户在UI上的修改
# 通用数据是通过panel直接暴露修改的属性
# 包括DK，roof_style，paint_style，梁架/椽架/瓦作层数据
# 不包括地盘、台基、装修、斗栱的数据
# 调用方：
# updateCombo
def __downloadCommonData(toBuilding:bpy.types.Object):
    defaultSyncKeys = [
                'DK',
                'paint_style',
                'roof_style',
                'use_hallway',
                'rafter_count',
                'use_flyrafter',
                'use_wangban',
                'qiqiao',
                'chong',
                'use_pie',
                'shengqi',
                'liangtou',
                'tuishan',
                'shoushan',
                'luding_rafterspan',
                'juzhe',
                'roof_height',
                'tile_scale',
                'tile_color',
                'tile_alt_color',
                'paoshou_count',
            ]
    
    utils.outputMsg(f"-- Download common data to [{toBuilding.name}]...")
    comboObj = utils.getComboRoot(toBuilding)
    # 拷贝字段
    utils.copyAcaData(
        fromObj = comboObj,
        toObj = toBuilding,
        keys =defaultSyncKeys,
    )

    return

# 从主建筑同步数据到根节点以及其他子建筑
# 这些数据允许各个子建筑自行设定，如，月台的地盘与主建筑就可以不一样
# 所以在UI上支持暴露子建筑属性，提供灵活性
# 但在update时，这些数据也会更新到comboRoot中保证一致性
# 但是不包括个性化数据，如，wall_span，door_num等
# 调用方：
# updateCombo
def __syncMainData(toBuilding:bpy.types.Object,):
    syncKeys = [
                'x_rooms',
                'x_1',
                'x_2',
                'x_3',
                'x_4',
                'y_rooms',
                'y_1',
                'y_2',
                'y_3',
                'piller_height',
                'piller_diameter',
                'use_smallfang',
            ]
    
    utils.outputMsg(f"-- Download main data to [{toBuilding.name}]...")
    mainBuildingObj = utils.getMainBuilding(toBuilding)
    # 拷贝字段
    utils.copyAcaData(
        fromObj = mainBuildingObj,
        toObj = toBuilding,
        keys =syncKeys,
    )

    return