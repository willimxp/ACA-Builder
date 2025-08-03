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
    if buildingObj.parent is not None:
        comboObj = buildingObj.parent
    else:
        comboObj = buildingObj
    if comboObj.ACA_data.aca_type == con.ACA_TYPE_COMBO:
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
                reloadAssets=False,):
    # 查找是否存在comboRoot
    if buildingObj.parent is not None:
        # 用combo节点替换buildingObj
        rootObj = buildingObj.parent
    else:
        rootObj = buildingObj
    
    # 循环清空各个建筑构件
    for childBuilding in rootObj.children:
        utils.deleteHierarchy(childBuilding)
    
    # 同步combo子建筑数据
    syncComboData(rootObj,buildingObj)
        
    # 循环生成各个单体
    for childBuilding in rootObj.children:
        buildFloor.buildFloor(childBuilding,
                reloadAssets=reloadAssets,
                comboObj=rootObj)

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
# 仅在updateBuilding中调用
def syncComboData(comboObj:bpy.types.Object,
                    buildingObj:bpy.types.Object):
    syncKeys = [
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
        # 间数不能同步
        # 'x_rooms',
        # 'y_rooms',
    ]

    # combo的数据集
    cData:acaData = comboObj.ACA_data
    mainBuildingObj = utils.getMainBuilding(comboObj)
    if mainBuildingObj is None:
        utils.outputMsg("combo数据同步失败，未找到主建筑")
        return
    # 主建筑数据集
    mData:acaData = mainBuildingObj.ACA_data

    # 验证修改的数据是否是主建筑
    if mainBuildingObj == buildingObj:
        # 确认传入的是主建筑，向各个子建筑同步
        needSync = True
    else:
        # 可能传入的是月台之类的子建筑，不向主建筑同步
        needSync = False

    # 循环同步
    for childBuilding in comboObj.children:
        # 待同步的建筑数据集
        bData:acaData = childBuilding.ACA_data

        if needSync:
            # 验证是否与修改对象为同一建筑
            if childBuilding != buildingObj:
                for key in syncKeys:
                    if hasattr(mData,key):
                        bData[key] = getattr(mData,key)

        # 月台数据更新
        if bData.combo_type == con.COMBO_TERRACE:
            from . import buildPlatform
            buildPlatform.setTerraceData(childBuilding)

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

def terraceAdd(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # 验证组合根节点
    comboObj = None
    if buildingObj.parent is not None:
        parent = buildingObj.parent
        if parent.ACA_data.aca_type == con.ACA_TYPE_COMBO:
            comboObj = parent
    # 如果不存在combo则新建
    if comboObj is None:

        comboObj = __addComboLevel(buildingObj)
    
    # 验证是否为主体建筑
    if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
        utils.popMessageBox("不能添加月台，只有主体建筑可以添加月台")
        return
    
    # 验证是否已经有月台
    for building in comboObj.children:
        if building.ACA_data.combo_type == con.COMBO_TERRACE:
            utils.popMessageBox("已经有一个月台，不能再生成新的月台了。")
            return
    
    # 0、初始化主建筑数据
    mData:acaData = buildingObj.ACA_data
    mData['use_terrace'] = True

    # 1、开始构建月台 ----------------------------
    # 1.1、构建月台根节点
    
    terraceRoot = buildFloor.__addBuildingRoot(
        templateName = '月台',
        comboObj = comboObj
    )
    
    # 1.2、月台数据集
    bData:acaData = terraceRoot.ACA_data
    # 继承主建筑属性
    utils.copyAcaData(buildingObj,terraceRoot)
    # 月台组合类型
    bData['combo_type'] = con.COMBO_TERRACE
    # 设置月台逻辑数据
    terraceRoot = setTerraceData(terraceRoot)
    
    # 2、刷新主建筑月台（隐藏前出踏跺）
    buildPlatform.buildPlatform(buildingObj)
    
    # 3、添加月台，复用的buildPlatform
    # 但传入terraceRoot，做为组合建筑的子对象
    buildPlatform.buildPlatform(terraceRoot)
    # 移动月台根节点
    terraceRoot.location = bData.root_location

    # 4、重做柱网（显示柱定位标识）
    buildFloor.buildPillers(terraceRoot)

    # 5、聚焦新生成的月台
    terraceObj = utils.getAcaChild(
        terraceRoot,con.ACA_TYPE_PLATFORM
    )
    if terraceObj is not None:
        utils.focusObj(terraceObj)

    return

# 设置月台数据
# 在terraceAdd和bulld.__syncComboData中复用
def setTerraceData(terraceObj:bpy.types.Object):
    # 月台数据集
    bData:acaData = terraceObj.ACA_data
    # 主建筑数据集
    mainBuildingObj = utils.getMainBuilding(terraceObj)
    mData:acaData = mainBuildingObj.ACA_data

    # 更新主建筑台基
    # 不做其他层次
    bData['is_showWalls'] = False
    bData['is_showDougong'] = False
    bData['is_showBeam'] = False
    bData['is_showRafter'] = False
    bData['is_showTiles'] = False
    # 启用柱网，但只显示柱定位点
    bData['is_showPillers'] = True
    # 柱网不从主建筑继承
    bData['piller_net'] = con.ACA_PILLER_HIDE   # 仅显示定位点
    bData['fang_net'] = ''      # 额枋不从主建筑继承
    bData['wall_net'] = ''      # 墙体不继承
    bData['step_net'] = ''

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
    # 月台面阔，五间以上做“凸”形月台，减2间
    if mData.x_rooms > 5:
        bData['x_rooms'] = mData.x_rooms - 2
    
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
    print("添加重檐")
    bData:acaData = buildingObj.ACA_data
    # 处理当前建筑为主建筑
    bData.combo_type = con.COMBO_MAIN
    bData['use_double_eave'] = True

    # 在面阔、进深扩展一廊间，22DK
    hallway_deepth = bData.DK * con.HALLWAY_DEEPTH
    bData.x_rooms += 2
    bData.y_rooms += 2
    

    # 屋顶改为盝顶，檐步等于廊间
    return

# 取消重檐
def doubleEaveDel(buildingObj:bpy.types.Object):
    print("取消重檐")
    bData:acaData = buildingObj.ACA_data
    bData['use_double_eave'] = False
    return