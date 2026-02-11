# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   组合建筑的营造
import bpy
from mathutils import Vector
from typing import List

from . import utils
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import template
from . import buildFloor
from . import buildPlatform
from . import buildRoof

# 添加combo根节点
def __addComboRoot(templateName,
                   location=None):
    # 创建或锁定根目录
    coll = utils.setCollection(templateName)
    # 创建buildObj根节点
    if location == None:
        # 默认原点摆放在3D Cursor位置
        location =  bpy.context.scene.cursor.location
    comboObj = utils.addEmpty(
        name=templateName,
        location=location
    )
    cData:acaData = comboObj.ACA_data
    cData['template_name'] = templateName
    cData['aca_obj'] = True
    cData['aca_id'] = utils.generateID()
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
    comboObj = __addComboRoot('建筑组合',
                              location = buildingObj.location)

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

    # 执行组合后处理
    comboData:acaData = comboObj.ACA_data
    postProcess = comboData.postProcess
    # 解析后处理列表
    for pp in postProcess:
        # 建筑拼接
        if pp.action == con.POSTPROC_SPLICE:
            paraList = pp.parameter.split('#')
            # 验证拼接只能有2个参数
            if len(paraList) != 2:
                utils.outputMsg("后处理异常：参数中不是期望的两个id")
                continue

            # 根据spliceid查找建筑
            fromBuilding = toBuilding = None
            for obj in bpy.data.objects:
                if not hasattr(obj,'ACA_data'):
                    continue
                if obj.ACA_data.splice_id == paraList[0]:
                    fromBuilding = obj
                if obj.ACA_data.splice_id == paraList[1]:
                    toBuilding = obj
            if fromBuilding is None or toBuilding is None:
                utils.outputMsg("后处理异常：无法匹配建筑spliceid")
                continue
            
            # 执行拼接
            from . import buildSplice
            buildSplice.spliceBuilding(
                fromBuilding=fromBuilding,
                toBuilding=toBuilding)
        else:
            utils.outputMsg("无法识别的后处理类型")

    return {'FINISHED'}

# 刷新组合建筑
def updateCombo(buildingObj:bpy.types.Object,
                reloadAssets=False,
                resetFloor=False,
                resetRoof=False,):
    utils.outputMsg("开始更新......")

    # 251217 添加清除拼接
    from . import buildSplice
    buildSplice.undoSplice(buildingObj)

    comboObj = utils.getComboRoot(buildingObj)
    bData:acaData = buildingObj.ACA_data
    mainBuilding = utils.getMainBuilding(buildingObj)

    # 更新的对象范围
    updateBuildingList = []
    # 如果基于combo根节点，全部更新
    if bData.aca_type == con.ACA_TYPE_COMBO:
        # 251224 排除combo下的bool等对象的影响
        # updateBuildingList = comboObj.children
        for child in comboObj.children:
            if child.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
                updateBuildingList.append(child)
                
        # ComboRoot通用数据下发
        # 目前仅用于paint_style的下发同步
        #　utils.outputMsg("更新组合建筑：ComboRoot【通用数据】下发...")
        for child in comboObj.children:
            __downloadCommonData(toBuilding=child)
    else:
        updateBuildingList.append(buildingObj)

    # 月台数据更新
    terraceObj = utils.getComboChild(
        buildingObj,con.COMBO_TERRACE)
    # 主数据下发，以便同步地盘开间
    # 主动更新(buildingObj是月台)不做主数据下发
    # 被动更新(buildingObj不是月台)，需要做一次主数据下发
    # 此时会强制月台开间与主建筑同步
    if terraceObj is not None:
        if buildingObj != terraceObj:
            __syncMainData(toBuilding=terraceObj,
                        resetFloor=resetFloor)
        # 初始化月台，并重新定位月台位置
        __setTerraceData(parentObj=mainBuilding,
                         terraceObj=terraceObj,
                        isInit=False
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
        elif resetRoof:
            buildRoof.buildRoof(childBuilding)
        # 全部重做
        else:
            buildFloor.buildFloor(childBuilding,
                    reloadAssets=reloadAssets,
                    comboObj=comboObj)
            
    # 聚焦对象
    utils.focusObj(buildingObj)
    
    return {'FINISHED'}

# 建筑间的数据同步
def __syncData(fromBuilding:bpy.types.Object,
               toBuilding:bpy.types.Object,
               syncAll = True,  # 默认同步所有，使用defaultSkipKeys
               syncKeys = None, # 同步的字段
               skipKeys = None, # 跳过的字段
               ):
    # print(f"-- syncData fromBuilding={fromBuilding.name},toBuilding={toBuilding.name},syncAll={syncAll},syncKeys={syncKeys},skipKeys={skipKeys}")
    defaultSkipKeys = [
                'aca_id',
                'aca_type',
                'combo_type',
                'combo_parent'
                # 'is_showPlatform',
                # 'is_showPillars',
                # 'is_showWalls',
                # 'is_showDougong',
                # 'is_showBeam',
                # 'is_showRafter',
                # 'is_showTiles',
                # 250812 重檐上檐需要同步pillarnet，
                # 所以默认的数据上传需要上传这些字段
                # 月台不需要pillarnet，不要用这个skip
                # 'pillar_net',
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

# 从主建筑同步数据到根节点以及其他子建筑
# 这些数据允许各个子建筑自行设定，如，月台的地盘与主建筑就可以不一样
# 所以在UI上支持暴露子建筑属性，提供灵活性
# 但在update时，这些数据也会更新到comboRoot中保证一致性
# 但是不包括个性化数据，如，wall_span，door_num等
# 调用方：
# updateCombo
def __syncMainData(toBuilding:bpy.types.Object,
                   resetFloor = False):
    syncKeys = ['x_1',
                'x_2',
                'x_3',
                'x_4',
                'y_1',
                'y_2',
                'y_3',
                'pillar_height',
                'pillar_diameter',
                'use_smallfang',]
    
    # 仅在重置柱网时，同步面阔/进深间数
    if resetFloor:
        syncKeys += ['x_rooms','y_rooms',]
    
    print(f"-- Download main data to [{toBuilding.name}]...")
    mainBuildingObj = utils.getMainBuilding(toBuilding)
    # 拷贝字段
    utils.copyAcaData(
        fromObj = mainBuildingObj,
        toObj = toBuilding,
        keys =syncKeys,
    )

    return

# 将建筑数据上传至comboRoot根节点
# 调用方：
# __addComboLevel：组合建筑初始化时，将主建筑数据上传comboRoot
# __setTerraceData：月台创建后，对主建筑修改(添加use_terrace标识)，需要更新到comboRoot
# updateCombo：重檐修改后，及时更新comboRoot
def __uploadData(fromBuilding:bpy.types.Object):
    # 跳过的字段
    skipKeys = [
                'aca_id',
                'aca_type',
                'combo_type',
                'combo_parent',
                'is_showPlatform',
                'is_showPillars',
                'is_showWalls',
                'is_showDougong',
                'is_showBeam',
                'is_showRafter',
                'is_showTiles',
                # 250812 comboRoot中需要与主建筑同步pillarnet
                # 子建筑可以自行决定是否要继承该柱网，
                # 如，月台初始化时继承，修改更新时不继承，
                # 如，重檐上檐始终继承
                # 'pillar_net',
                # 250819 roof_style不能跳过，否则默认值为'0'
                #'roof_style',   # 250819 不上传屋顶类型，将始终保留继承的主建筑屋顶类型
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

# 从comboRoot下载通用数据，以反映用户在UI上的修改
# 通用数据是通过panel直接暴露修改的属性
# 包括DK，roof_style，paint_style，梁架/椽架/瓦作层数据
# 不包括地盘、台基、装修、斗栱的数据
# 调用方：
# updateCombo
def __downloadCommonData(toBuilding:bpy.types.Object):
    defaultSyncKeys = [
                # 'DK',
                'paint_style',
                # 'roof_style', # 250818 盝顶独立管理
                # 'use_hallway',
                # 'rafter_count',
                # 'use_flyrafter',
                # 'use_wangban',
                # 'qiqiao',
                # 'chong',
                # 'use_pie',
                # 'shengqi',
                # 'liangtou',
                # 'tuishan',
                # 'shoushan',
                # 'luding_rafterspan', #250816 这个由建筑自行管理，不做同步
                # 'juzhe',
                # 'roof_height',
                # 'tile_scale',
                # 'tile_color',
                # 'tile_alt_color',
                # 'paoshou_count',
            ]
    
    print(f"-- Download common data to [{toBuilding.name}]...")
    comboObj = utils.getComboRoot(toBuilding)
    # 拷贝字段
    utils.copyAcaData(
        fromObj = comboObj,
        toObj = toBuilding,
        keys =defaultSyncKeys,
    )

    return

# 添加月台
# 传入主建筑，在主建筑上添加月台
def addTerrace(buildingObj:bpy.types.Object):
    # 0、合法性验证 -----------------------
    # # 验证是否为主体建筑
    # if buildingObj.ACA_data.combo_type != con.COMBO_MAIN:
    #     utils.popMessageBox("不能添加月台，只有主体建筑可以添加月台")
    #     return {'CANCELLED'}
    # 250828 只要是台基，就允许添加月台
    
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
    link_id = buildingObj.ACA_data.aca_id
    terraceRoot.ACA_data['combo_parent'] = link_id
    
    # 2、构造月台数据集 --------------------------
    # 从Combo根节点继承数据
    utils.outputMsg("添加月台子建筑...")
    # __downloadData(toBuilding=terraceRoot)
    # 设置月台逻辑数据
    __setTerraceData(parentObj=buildingObj,
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
def __setTerraceData(parentObj:bpy.types.Object,
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
        __syncData(fromBuilding=parentObj,
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

        # 月台面阔，五间以上做“凸”形月台，减2间
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

# 根据楼阁方案，设置楼阁默认参数
def set_multiFloor_plan(self, context:bpy.types.Context):
    buildingObj,bData,oData = utils.getRoot(context.object)
    dk = bData.DK
    scnData = bpy.context.scene.ACA_data

    # 初始化列表
    # 清空
    scnData.pavilionItem.clear()
    # 添加列表
    item = scnData.pavilionItem.add()
    item.name = '0-重檐'
    item = scnData.pavilionItem.add()
    item.name = '1-简单重楼'
    item = scnData.pavilionItem.add()
    item.name = '2-重楼+平坐'
    item = scnData.pavilionItem.add()
    item.name = '3-重楼+腰檐'
    item = scnData.pavilionItem.add()
    item.name = '4-重楼+腰檐+平坐(无栏杆)'
    item = scnData.pavilionItem.add()
    item.name = '5-重楼+腰檐+平坐(有栏杆)'
    item = scnData.pavilionItem.add()
    item.name = '6-重楼+腰檐+回廊'
    item = scnData.pavilionItem.add()
    item.name = '7-下出平坐'
    
    pavilionIndex = scnData.pavilionIndex
    setting = scnData.pavilionSetting
    # 数据初始化
    setting.use_floor = False
    setting.use_mideave = False
    setting.use_pingzuo = False
    setting.use_railing = False
    setting.use_loggia = False
    setting.use_lower_pingzuo = False
    setting.taper = 0
    setting.loggia_width = 0
    setting.pingzuo_taper = 0

    # 0.重檐
    if pavilionIndex == 0:
        setting.use_mideave = True
        setting.taper = 11*dk  # 默认收分一攒
    # 1.简单重楼(涵月楼)
    if pavilionIndex == 1:
        setting.use_floor = True
        setting.use_pingzuo = True
        setting.taper = 0  # 默认不做收分
    # 2.重楼+平坐栏杆
    if pavilionIndex == 2:
        setting.use_floor = True
        setting.use_pingzuo = True
        setting.use_railing = True
        setting.taper = 3*dk  # 默认收分1拽架
    # 3.重楼+披檐(无平坐，如，边靖楼)
    if pavilionIndex == 3:
        setting.use_floor = True
        setting.use_mideave = True
        setting.taper = 3*dk  # 默认收分1拽架
    # 4-重楼+腰檐+平坐(无栏杆)
    if pavilionIndex == 4:
        setting.use_floor = True
        setting.use_mideave = True
        setting.use_pingzuo = True
        setting.taper = 3*dk  # 默认收分1拽架
        pingzuo_extend = (bData.dg_extend   # 斗栱出跳
              + con.BALCONY_EXTENT*bData.DK*bData.dk_scale # 平坐出跳，对齐桁出梢
              - con.PILLAR_D_EAVE*bData.DK/2 # 柱的保留深度
              - bData.DK # 保留1斗口边线
            ) 
        setting.pingzuo_taper = -pingzuo_extend
    # 5-重楼+腰檐+平坐(有栏杆)
    if pavilionIndex == 5:
        setting.use_floor = True
        setting.use_mideave = True
        setting.use_pingzuo = True
        setting.use_railing = True
        setting.taper = 3*dk  # 默认收分1拽架
        setting.pingzuo_taper = 3*dk # 默认平坐再收分1拽架
    # 6-重楼+腰檐+回廊
    if pavilionIndex == 6:
        setting.use_floor = True
        setting.use_mideave = True
        setting.use_pingzuo = True
        setting.use_railing = True
        setting.use_loggia = True
        setting.taper = 11*dk  # 默认收分1攒
        setting.loggia_width = 22*dk # 回廊默认2攒
    # 7-下出平坐
    if pavilionIndex == 7:
        setting.use_railing = True
        setting.use_lower_pingzuo = True
        setting.taper = 9*dk  # 默认收分3拽架

# 添加重楼
def addMultiFloor(baseFloor:bpy.types.Object,
                  setting,# 重楼设置
                #   taper=0.0, # 收分
                #   use_floor=True,# 做重屋
                #   use_mideave=False, # 做腰檐
                #   use_pingzuo=False, # 做平坐
                #   pingzuo_taper=0.0, # 平坐收分
                #   use_railing=False, # 做平坐栏杆
                #   use_loggia=False, # 做回廊
                #   loggia_width=0.0,# 回廊宽度
                  ):   
    # 载入数据
    bData:acaData = baseFloor.ACA_data
    taper=setting.taper # 收分
    use_floor=setting.use_floor # 做重屋
    use_mideave=setting.use_mideave # 做腰檐
    use_pingzuo=setting.use_pingzuo # 做平坐
    pingzuo_taper=setting.pingzuo_taper # 平坐收分
    use_railing=setting.use_railing # 做平坐栏杆
    use_loggia=setting.use_loggia # 做回廊
    loggia_width=setting.loggia_width # 回廊宽度
    use_lower_pingzuo=setting.use_lower_pingzuo # 下出平坐
    
    # 0、合法性验证 -----------------------
    if bData.combo_type not in (con.COMBO_MULTI_FLOOR,
                                con.COMBO_MAIN,
                                con.COMBO_DOUBLE_EAVE,
                                con.COMBO_PINGZUO):
        utils.popMessageBox("只有主体建筑可以做重楼，月台无法做重楼")
        return {'CANCELLED'}

    # 验证屋顶样式
    if bData.roof_style not in (
                con.ROOF_LUDING,
                con.ROOF_WUDIAN,
                con.ROOF_XIESHAN,
                con.ROOF_XIESHAN_JUANPENG,):
        utils.popMessageBox("暂时只用庑殿、歇山屋顶样式支持添加重楼")
        return {'CANCELLED'}

    # 避免类似直接从空柱网模板开始做阁楼的异常做法
    if bData.combo_type != con.COMBO_PINGZUO:
        tileRoot = utils.getAcaChild(baseFloor,con.ACA_TYPE_TILE_ROOT)
        if tileRoot==None:
            utils.popMessageBox("当前建筑尚未生成屋顶，请先设置完成屋顶参数")
            return {'CANCELLED'}
    
    # 避免直接在平坐上做重檐
    if bData.combo_type == con.COMBO_PINGZUO and use_mideave:
        utils.popMessageBox("无法在平座层上做重檐或披檐，请选择其他楼层")
        return {'CANCELLED'}
        
    # 保护避免0的异常
    if taper == 0:taper = 0.01

    # 验证重檐最小收分
    if use_mideave:
        eave_ex = taper
        # 如果斗栱出跳大于3DK，重檐收分可为0
        if bData.use_dg:
            eave_ex += bData.dg_extend
        
        if eave_ex < 3* bData.DK:
            utils.popMessageBox("收分验证失败：斗栱出跳与重檐收分合计至少应3斗口，请更换斗栱，或增加收分")
            return {'CANCELLED'}

    # 验证回廊做法的开间尺寸，避免楼阁5出现异常
    if use_floor and use_mideave and use_pingzuo and use_loggia:
        msg = ''
        room_min = round(taper + loggia_width,3)

        # 面阔验证
        if bData.x_rooms >= 7 and bData.x_4 < room_min:
            msg = f'面阔尽间当前[{round(bData.x_4,3)}],应大于[{room_min}]'
        elif bData.x_rooms == 5 and bData.x_3 < room_min:
            msg = f'面阔梢间当前[{round(bData.x_3,3)}],应大于[{room_min}]'
        elif bData.x_rooms == 3 and bData.x_2 < room_min:
            msg = f'面阔梢间当前[{round(bData.x_2,3)}],应大于[{room_min}]'
        elif bData.x_rooms == 1 and bData.x_1 < room_min*2:
            msg = f'面阔梢间当前[{round(bData.x_1,3)}],应大于[{room_min*2}]'

        # 进深验证
        if bData.y_rooms >= 5 and bData.y_3 < room_min:
            msg = f'进深梢间当前[{round(bData.y_3,3)}],应大于[{room_min}]'
        elif bData.y_rooms in {3,4} and bData.y_2 < room_min: 
            msg = f'进深次间当前[{round(bData.y_2,3)}],应大于[{room_min}]'
        elif bData.y_rooms == 2 and bData.y_1 < room_min: 
            msg = f'进深明间当前[{round(bData.y_1,3)}],应大于[{room_min}]'
        elif bData.y_rooms == 1 and bData.y_1 < room_min*2: 
            msg = f'进深明间当前[{round(bData.y_1,3)}],应大于[{room_min*2}]'
        
        if msg != '':
            utils.popMessageBox(f"收分验证失败：{msg}（注意：如果下层已经有回廊，建议不要使用方案“6-重楼+腰檐+回廊”，可以尝试使用方案“4-重楼+腰檐+平坐(无栏杆)”）")
            return {'CANCELLED'}

    # 1、数据准备 --------------------
    # 1.1、显示进度条 
    from . import build
    build.isFinished = False
    build.progress = 0
    utils.outputMsg("添加重楼子建筑...")
    # 暂时排除目录下的其他建筑，以加快执行速度
    build.__excludeOther(keepObj=baseFloor)
    
    # 1.2、添加combo根节点
    comboObj = utils.getComboRoot(baseFloor)
    # 如果不存在combo则新建
    if comboObj is None:
        comboObj = __addComboLevel(baseFloor)

    # 2、重楼数据初始化，包括下层、披檐、平坐、重楼等
    # 2.1、下层的处理
    # 下出平坐，下层关闭台基，删除柱础
    needUpdateBaseFloor = False
    if use_lower_pingzuo:
        # 关闭平坐台基
        bData['is_showPlatform'] = False
        bData['platform_height'] = 0
        # 删除柱础
        utils.deleteByName(baseFloor,name='素平柱础')
        utils.deleteByName(baseFloor,name='柱顶石')
    # 上出平坐或重楼，重设屋顶样式
    else:
        # 梁架强制不做廊间举架
        if bData.use_hallway:
            bData['use_hallway'] = False
            needUpdateBaseFloor = True
        # 如果要做腰檐，屋顶改做盝顶
        if use_mideave:
            # 下层屋顶：改为盝顶
            bData['roof_style'] = int(con.ROOF_LUDING)
            bData['rafter_count'] = 2
            bData['luding_rafterspan'] = taper
        # 如果不做腰檐，屋顶改作平坐
        else:
            # 下层屋顶：改为平坐
            bData['roof_style'] = int(con.ROOF_BALCONY)
            # 做平坐的朝天栏杆
            bData['use_balcony_railing'] = use_railing
            # 不涉及收分、栏杆
        # 设置上层基座为下层（盝顶或平坐）
        lowerFloor = baseFloor

    # 2.2、添加独立平坐层
    # 同时要求做平坐和腰檐时，做一个独立的平座层
    # 不做腰檐的，直接下层已经改为平坐了，不额外添加
    pingzuo = None
    if (use_pingzuo and use_mideave) or use_lower_pingzuo:
        # 添加平坐，做收分，栏杆
        if use_loggia:
            # 上层做回廊时，不做平坐栏杆
            use_railing_pingzuo = False
        else:
            use_railing_pingzuo = use_railing

        # 收分处理
        if use_lower_pingzuo:
            # 下出平坐，外扩
            p_taper = - taper
        else:
            # 上出平坐，内收
            p_taper = taper
        pingzuo = __addPingzuo(baseFloor,
                               p_taper,
                               use_lower_pingzuo, # 是否为下出平坐
                               use_railing=use_railing_pingzuo,
                               )        
        # 设置上层基座为新生成的平坐
        lowerFloor = pingzuo

    # 2.3、添加上层重楼
    upperFloor = None
    # use_floor做重楼，或use_mideave做重檐/腰檐
    # 如果是下出平坐，则无需做上层重楼
    if use_floor or use_mideave:
        # 可能基于做了腰檐的下层盝顶
        # 可能基于不做腰檐的下层平坐
        # 可能基于做了腰檐的下层平坐

        # 如果下层为独立平坐层，
        if use_pingzuo and use_mideave:
            # 默认上层不做收分
            upperTaper = 0
            # 如果回廊较大，则需要在平坐收分的基础上，做二次收分
            if use_loggia and loggia_width > taper:
                upperTaper = loggia_width-taper
            # 叠加平坐收分
            upperTaper += pingzuo_taper
        # 下层没有独立平座层，如简单重楼模式，直接应用收分
        else:
            upperTaper = taper
            
        try:
            upperFloor = __addUpperFloor(
                lowerFloor,
                taper=upperTaper,
                use_floor=use_floor,
                use_railing=use_railing,
                # 回廊是否外扩,如果不做平坐，按内收做法
                is_on_pingzuo=use_pingzuo,
                # 做回廊
                use_loggia=use_loggia, 
                loggia_width=loggia_width
            )
        except Exception as e:
            utils.popMessageBox(str(e))

            # 异常回滚
            if pingzuo != None:
                from . import build
                build.delBuilding(pingzuo,
                    withCombo=False,# 仅删除个体
                )
                # 是否需要组合降级
                from . import build
                __delComboLevel(baseFloor)

            # 关闭进度条
            build.isFinished = True
            # 取消排除目录下的其他建筑
            build.__excludeOther(isExclude=False,
                                keepObj=baseFloor)
            utils.focusObj(baseFloor)
            return {'CANCELLED'}

    # 3、执行营造 -------------------------------------
    # 3.1、刷新各层的抬升
    __updateFloorLoc(comboObj)
    # 下层处理
    if use_lower_pingzuo:
        # 下出平坐，关闭下层台基
        buildPlatform.resizePlatform(baseFloor)
    else:
        # 刷新下层，上面如果修改了廊间举架，需要刷新全屋
        if needUpdateBaseFloor:
           buildFloor.buildFloor(baseFloor,comboObj=comboObj)
        # 否则仅需刷新屋顶
        else:
            buildRoof.buildRoof(baseFloor)
    # 生成平坐
    if pingzuo is not None:
        buildFloor.buildFloor(pingzuo,comboObj=comboObj)
    # 生成重楼
    if upperFloor is not None:
        buildFloor.buildFloor(upperFloor,comboObj=comboObj)

    # 3.2、关闭进度条
    build.isFinished = True
    # 取消排除目录下的其他建筑
    build.__excludeOther(isExclude=False,
                         keepObj=baseFloor)

    return {'FINISHED'}

# 添加平坐层
def __addPingzuo(baseFloor:bpy.types.Object,
                 taper, # 收分
                 use_lower_pingzuo=False,
                 use_railing=False, # 做平坐栏杆
                 ):
    # 载入数据
    bData:acaData = baseFloor.ACA_data

    # 1、添加平坐子节点
    comboObj = utils.getComboRoot(baseFloor)
    pingzuoName = bData.template_name + '.平坐'
    pingzuo = buildFloor.__addBuildingRoot(
        templateName = pingzuoName,
        comboObj = comboObj
    )

    # 2、平坐数据初始化
    # 从下同步：柱网等信息
    __syncData(fromBuilding=baseFloor,
               toBuilding=pingzuo)
    
    # 3、平坐数据的其他设置
    mData:acaData = pingzuo.ACA_data
    mData['combo_type'] = con.COMBO_PINGZUO
    # 平坐父子关系
    if use_lower_pingzuo:
        __updateMultiFloorParent(parentObj=pingzuo,
                                childObj=baseFloor)
    else:
        __updateMultiFloorParent(parentObj=baseFloor,
                                childObj=pingzuo)

    # 屋顶设为平坐
    mData['roof_style'] = int(con.ROOF_BALCONY)
    # 做平坐的朝天栏杆
    mData['use_balcony_railing'] = use_railing
    # 关闭平坐台基
    mData['is_showPlatform'] = False
    mData['platform_height'] = 0
    # 设置柱高:叉柱到斗栱上
    # 从斗栱顶(挑檐桁下皮)，到围脊向上额枋高度
    mideaveHeight = __getPingzuoHeight(baseFloor)
    mData['pillar_height'] = mideaveHeight
    # 250916 新的逻辑中，建筑数据层层向上传递（不再使用comboRoot数据）
    # 所以这里不要清除，延迟到buildWall函数中判断
    # # 不做装修
    # utils.clearChildData(mData)
    
    # 根据收分，更新地盘数据
    __setTaperData(mData,taper)

    return pingzuo

# 添加重楼
def __addUpperFloor(lowerFloor:bpy.types.Object,
                    taper=0.01, # 收分
                    use_floor=True, # 做重屋
                    use_railing=False, # 做栏杆
                    is_on_pingzuo=True, # 回廊是否外扩
                    use_loggia=False, # 做回廊
                    loggia_width=0.0, # 回廊宽度
                    ):
    # 载入数据
    bData:acaData = lowerFloor.ACA_data

    # 1、添加重楼子节点
    comboRootObj = utils.getComboRoot(lowerFloor)
    if use_floor:
        upperfloorName = '.重楼'
    else:
        upperfloorName = '.重檐'
    upperfloor = buildFloor.__addBuildingRoot(
        templateName = bData.template_name + upperfloorName,
        comboObj = comboRootObj
    )
    
    # 2、上层数据初始化
    mData:acaData = upperfloor.ACA_data
    # 区分重楼和重檐
    if use_floor:
        mData['combo_type'] = con.COMBO_MULTI_FLOOR
    else:
        mData['combo_type'] = con.COMBO_DOUBLE_EAVE
    # 上层父子关系
    __updateMultiFloorParent(parentObj=lowerFloor,
                             childObj=upperfloor)
    
    # 1、基本设置 ------------------
    # 地盘数据从下层同步
    __syncData(fromBuilding=lowerFloor,
               toBuilding=upperfloor)
    dk = mData.DK
    # 清除踏步
    mData.step_list.clear()
    # 根据收分，更新地盘数据
    try:
        __setTaperData(mData,taper)
    except Exception as e:
        from . import build
        build.delBuilding(upperfloor,
            withCombo=False,# 仅删除个体
        )
        # 是否需要组合降级
        from . import build
        __delComboLevel(comboRootObj)
        raise Exception(str(e))

    # 1.1 设置屋顶
    # 是否为顶层？
    isTop = True
    for child in comboRootObj.children:
        if child.ACA_data.combo_parent == mData.aca_id:
            isTop = False
            break
    if isTop:
        # 屋顶类型从comboRoot同步
        mData['roof_style'] = int(comboRootObj.ACA_data.roof_style)
    else:
        mData['roof_style'] = int(con.ROOF_LUDING)
        bData['rafter_count'] = 2

    # 2、设置楼板 ----------------------
    # 如果建于平坐之上，或不做重屋，关闭上层台基
    if bData.roof_style == con.ROOF_BALCONY or not use_floor:
        mData['is_showPlatform'] = False
        mData['platform_height'] = 0
    # 如果没有平坐，如边靖楼模式，做楼板(台基)
    else:
        mData['is_showPlatform'] = True
        mData['platform_height'] = con.BALCONY_FLOOR_H*dk
        mData['platform_extend'] = mData.pillar_diameter/2

    # 3、设置柱子 ------------------------------
    # 3.1、设置柱高
    # 柱高默认从下层传递，但下层如果是平座层，则柱高太短
    if use_floor:
        # 这里统一重新设置为55DK
        mData['pillar_height'] = 55*dk
    # 不做重屋时(单一重檐)，只露出额枋
    else:
        mData['pillar_height'] = __getPingzuoHeight(lowerFloor)

    # 3.2、设置插柱
    # 插柱初始化，以免继承下层数据
    mData['pillar_insert'] = 0
    # 如果立于腰檐之上且要做重楼(边靖楼模式)，柱子下插
    # 这里通过use_floor来判断是否是重檐，重檐直接落在梁上，不用再重复计算下插
    if bData.roof_style == con.ROOF_LUDING and use_floor:
        insert_height = 0
        # 盝顶围脊高度
        aData = bpy.context.scene.ACA_temp
        ridgeObj:bpy.types.Object = aData.ridgeBack_source
        ridgeH = ridgeObj.dimensions.z
        # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
        tileScale = dk / con.DEFAULT_DK  * bData.tile_scale
        ridgeH = ridgeH * tileScale
        insert_height += ridgeH
        insert_height -= con.RIDGE_SURR_OFFSET*dk   # 围脊调整
        # 屋瓦层抬升
        insert_height += (con.YUANCHUAN_D*dk   # 椽架
                    + con.WANGBAN_H*dk   # 望板
                    + con.ROOFMUD_H*dk   # 灰泥
                    )
        # 檐椽架加斜
        from . import buildBeam
        lift_radio = buildBeam.getLiftRatio(lowerFloor)
        # 盝顶步架加斜
        insert_height += bData.luding_rafterspan * lift_radio[0]
        # 半根正心桁(梁上皮在正心桁中心)
        insert_height += con.HENG_COMMON_D*dk        
        mData['pillar_insert'] = - insert_height

    # 4、设置栏杆与回廊 -----------------------------
    if use_loggia:
        # 回廊宽度，与平坐做法一致，参考buildBalcony.__buildFloor()
        pingzuo_extend = (bData.dg_extend   # 斗栱出跳
              + con.BALCONY_EXTENT*bData.DK*bData.dk_scale # 平坐出跳，对齐桁出梢
              - con.PILLAR_D_EAVE*bData.DK/2 # 柱的保留深度
              - bData.DK # 保留1斗口边线
            ) 
        # 如果不在平坐上，回廊采用内收做法，宽度取负数
        if not is_on_pingzuo:
            loggia_width *= -1
        
        # 调用buildFloor中的添加回廊方法
        try:
            buildFloor.setLoggiaData(
                mData,
                width=loggia_width,
                side='0',
                use_railing=use_railing,
                )
        except Exception as e:
            from . import build
            build.delBuilding(upperfloor,
                withCombo=False,# 仅删除个体
            )
            # 是否需要组合降级
            from . import build
            __delComboLevel(comboRootObj)
            raise Exception(str(e))

    return upperfloor

# 更新combo中的所有建筑高度
def __updateFloorLoc(contextObj:bpy.types.Object):
    utils.outputMsg("重新计算楼阁高度...")
    # 查找combo根节点
    comboRoot = utils.getComboRoot(contextObj)

    # 查找底层节点
    comboBase = None
    for comboChild in comboRoot.children:
        # 251211 combo节点下可能有splice对象，需要排除
        if comboChild.ACA_data.aca_type != con.ACA_TYPE_BUILDING:
            continue
        
        if comboChild.ACA_data.combo_parent == '':
            comboBase = comboChild
            break
    
    # 依次设置上层节点
    hasNextLevel = (comboBase is not None)
    preFloor = comboBase
    if comboBase is None: return
    # print(f"updatefloorloc,combobase={comboBase.name},hasnextlevel={hasNextLevel}")

    whilecount = 0
    while hasNextLevel:
        if whilecount<10:
            whilecount += 1
        else:
            break

        preData:acaData = preFloor.ACA_data

        # 查找下一层(上层)
        nextFloor = None
        for comboChild in comboRoot.children:
            # 跳过月台等子对象
            if comboChild.ACA_data.combo_type not in (
                con.COMBO_MAIN,
                con.COMBO_MULTI_FLOOR,
                con.COMBO_DOUBLE_EAVE,
                con.COMBO_PINGZUO):
                continue

            # 确实是否为父对象
            parentID = comboChild.ACA_data.combo_parent
            if parentID == preData.aca_id:
                nextFloor = comboChild
                break

        if nextFloor is not None:
            nextData:acaData = nextFloor.ACA_data
            dk = nextData.DK

            # 计算新位置
            # 1、先计算到斗栱挑高(挑檐桁下皮)
            floorHeight = 0
            if preData.is_showPlatform:
                floorHeight += preData.platform_height
            floorHeight += preData.pillar_height
            if preData.use_dg:
                if preData.use_pingbanfang:
                    floorHeight += con.PINGBANFANG_H*dk
                # 更新斗栱数据
                from . import template
                template.updateDougongData(preFloor)
                floorHeight += preData.dg_height

            # 2、当前楼层在平坐之上(观音阁、涵月楼、插花楼模式)，叠加楼板高度
            if preData.roof_style == con.ROOF_BALCONY:
                # 250905 叠加楼板高度
                floorHeight += con.BALCONY_FLOOR_H*dk
            
            # 3、平座层和重檐，柱立于大梁上皮，即正心桁中心
            # if (preData.roof_style == con.ROOF_LUDING
            #   and nextData.roof_style == con.ROOF_BALCONY):
            if nextData.combo_type in (con.COMBO_PINGZUO,
                                       con.COMBO_DOUBLE_EAVE):
                # 挑檐桁中心
                floorHeight += con.HENG_COMMON_D*dk/2
                # 斗栱出跳加斜
                if preData.use_dg:
                    from . import buildBeam
                    lift_radio = buildBeam.getLiftRatio(preFloor)
                    floorHeight += preData.dg_extend * lift_radio[0]
            

            # 4、边靖楼类型，楼顶落于围脊上皮
            # （柱下插在pillar_insert中另行处理）
            elif preData.roof_style == con.ROOF_LUDING:
            # if (preData.roof_style == con.ROOF_LUDING
            #         and nextData.roof_style != con.ROOF_BALCONY):
            # if (preData.roof_style == con.ROOF_LUDING
            #         and nextData.combo_type not in (
            #                 con.COMBO_PINGZUO,
            #                 con.COMBO_DOUBLE_EAVE)
            # ):
                # 计算从斗栱挑高到围脊上皮 -------------
                # 挑檐桁(斗栱高度到挑檐桁下皮)
                floorHeight += con.HENG_COMMON_D*dk

                # 檐椽架加斜
                from . import buildBeam
                lift_radio = buildBeam.getLiftRatio(preFloor)
                # 盝顶步架加斜
                floorHeight += preData.luding_rafterspan * lift_radio[0]
                if preData.use_dg:
                    # 斗栱出跳加斜
                    floorHeight += preData.dg_extend * lift_radio[0]

                # 屋瓦层抬升
                floorHeight += (con.YUANCHUAN_D*dk   # 椽架
                            + con.WANGBAN_H*dk   # 望板
                            + con.ROOFMUD_H*dk   # 灰泥
                            )
                
                # 盝顶围脊高度
                aData = bpy.context.scene.ACA_temp
                ridgeObj:bpy.types.Object = aData.ridgeBack_source
                ridgeH = ridgeObj.dimensions.z
                # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
                tileScale = dk / con.DEFAULT_DK  * preData.tile_scale
                ridgeH = ridgeH * tileScale
                floorHeight += ridgeH
                floorHeight -= con.RIDGE_SURR_OFFSET*dk   # 围脊调整

                # 扣除楼板高度
                floorHeight -= con.BALCONY_FLOOR_H*dk

            # 填充入下一层的数据
            nextData['combo_location'] = (preFloor.location
                        + Vector((0,0,floorHeight)))
            # 更新高度
            nextFloor.location = nextData.combo_location
            # utils.redrawViewport()

            # 递归到下一个循环
            preFloor = nextFloor

        else:
            # 跳出while循环
            hasNextLevel = False

    return

# 计算平坐层的柱高
# 从大梁上皮到围脊上露额枋的高度
def __getPingzuoHeight(buildingObj:bpy.types.Object):
    bData:acaData = buildingObj.ACA_data
    pillarLift = 0.0
    dk = bData.DK

    # 从大梁上皮开始计算
    # 已包括台基、柱高、斗栱挑高、斗栱出跳加斜、半根正心桁

    # 正心桁上皮，半根正心桁
    pillarLift += con.HENG_COMMON_D*dk/2

    # 盝顶步架加斜
    from . import buildBeam
    lift_radio = buildBeam.getLiftRatio(buildingObj)
    pillarLift += bData.luding_rafterspan * lift_radio[0]

    # 屋瓦层抬升
    pillarLift += (con.YUANCHUAN_D*dk   # 椽架
                   + con.WANGBAN_H*dk   # 望板
                   + con.ROOFMUD_H*dk   # 灰泥
                   )
    
    # 盝顶围脊高度
    aData = bpy.context.scene.ACA_temp
    ridgeObj:bpy.types.Object = aData.ridgeBack_source
    ridgeH = ridgeObj.dimensions.z
    # 瓦片缩放，以斗口缩放为基础，再叠加用户自定义缩放系数
    tileScale = bData.DK / con.DEFAULT_DK  * bData.tile_scale
    ridgeH = ridgeH * tileScale
    pillarLift += ridgeH
    pillarLift -= con.RIDGE_SURR_OFFSET*dk   # 围脊调整

    # 额枋高度
    # 大额枋
    pillarLift += con.EFANG_LARGE_H*dk
    if bData.use_smallfang:
        # 由额垫板
        pillarLift += con.BOARD_YOUE_H*dk
        # 小额枋
        pillarLift += con.EFANG_SMALL_H*dk

    return pillarLift

# 根据收分要求，设置地盘数据
def __setTaperData(mData,taper):
    # 上层收分，在最后的开间做收分，如果不够，则自动缩减间数
    xTaper = taper
    if mData.x_rooms >= 7:
        if mData['x_4'] > xTaper:
            mData['x_4'] -= xTaper
        else:
            raise Exception(
                f"楼阁收分失败：尽间尺寸请至少加大{round(xTaper-mData.x_4,3)}")
    elif mData.x_rooms == 5:
        if mData['x_3'] > xTaper:
            mData['x_3'] -= xTaper
        else:
            raise Exception(
                f"楼阁收分失败：梢间尺寸当前{round(mData.x_3),3}，需大于收分{round(xTaper,3)}")
    elif mData.x_rooms == 3:
        if mData['x_2'] > xTaper:
            mData['x_2'] -= xTaper
        else:
            raise Exception(
                f"楼阁收分失败：次间尺寸当前{round(mData.x_2,3)}，需大于收分{round(xTaper,3)}")
    elif mData.x_rooms == 1:
        if mData['x_1']/2 > xTaper:
            mData['x_1'] -= xTaper*2
        else:
            raise Exception(
                f"楼阁收分失败：明间尺寸当前{round(mData.x_1,3)}，需大于收分{round(xTaper,3)}")
    else:
        raise Exception(
                f"楼阁收分失败，未知原因")
    
    # 进深收分
    yTaper = taper
    if mData.y_rooms >= 5:
        if mData['y_3'] > yTaper:
            mData['y_3'] -= yTaper
        else:
            raise Exception(
                f"楼阁收分失败：进深梢间尺寸当前{round(mData.y_3,3)}，需大于收分{round(yTaper,3)}")
    elif mData.y_rooms in (3,4):
        if mData['y_2'] > yTaper:
            mData['y_2'] -= yTaper
        else:
            raise Exception(
                f"楼阁收分失败：进深次间应至少增加{round(yTaper-mData.y_2,3)}")
    elif mData.y_rooms == 2:
        if mData['y_1'] > yTaper:
            mData['y_1'] -= yTaper
        else:
            raise Exception(
                f"楼阁收分失败：进深明间尺寸应增加{round(yTaper -mData.y_1,3)}")
    elif mData.y_rooms == 1:
        if mData['y_1'] > yTaper*2:
            mData['y_1'] -= yTaper*2
        else:
            raise Exception(
                f"楼阁收分失败：进深明间尺寸当前{round(mData.y_1,3)}，需大于2倍收分{round(yTaper*2,3)}")
    else:
        raise Exception(
                f"楼阁收分失败，未知原因")
    
    return

# 解决重楼的父子冲突
def __updateMultiFloorParent(parentObj:bpy.types.Object,
                             childObj:bpy.types.Object):
    bData:acaData = parentObj.ACA_data
    mData:acaData = childObj.ACA_data
    # 父节点继承当前子节点的父亲，用于下出平坐时的关联
    if mData.combo_parent != '':
        bData['combo_parent'] = mData.combo_parent
    # 当前对象绑定到父对象
    mData['combo_parent'] = bData.aca_id

    # 查找comboRoot
    comboObj = utils.getComboRoot(parentObj)
    
    # 解决冲突的父子关系
    for child in comboObj.children:
        # 当前对象不做改变
        if child == childObj: continue
        cData:acaData = child.ACA_data

        # 非重楼对象(月台等)，不做处理
        if cData.combo_type not in (
            con.COMBO_MAIN,
            con.COMBO_MULTI_FLOOR,
            con.COMBO_PINGZUO,
            con.COMBO_DOUBLE_EAVE,):
            continue
        
        # 把冲突对象的父id，绑定到当前对象上
        if cData.combo_parent == bData.aca_id:
            # 原来的子楼层，挂接在新增的平坐上
            cData['combo_parent'] = mData.aca_id
            break
    return

# 将选中的对象合并为一个combo
def addCombo(buildingList:List[bpy.types.Object]):
    # 检验合并涉及的集合，并预先记录
    # 如果是单体与单体集成就不涉及
    # 如果是单体和集合，或集合与集合之间的集成，需要先记录下来，最后清理
    comboList = []
    isAllComboChild = True
    for buildingObj in buildingList:
        comboObj = utils.getComboRoot(buildingObj)
        if comboObj is None:
            isAllComboChild = False
        else:
            if comboObj not in comboList:
                comboList.append(comboObj)

            # 将集合中的其他建筑也加入集成
            for building in comboObj.children:
                if hasattr(building,'ACA_data'):
                    if building.ACA_data.aca_type == con.ACA_TYPE_BUILDING:
                        if building not in buildingList:
                            buildingList.append(building)

    # 验证是否已经集成，不再重复集成
    if len(comboList) == 1 and isAllComboChild:
        print("建筑已在同一个集合中，不再做集成")
        return {'CANCELLED'},comboList[0]
    
    # 新建一个combo
    # 锁定在ACA根目录下
    rootColl = utils.setCollection(con.COLL_NAME_ROOT)
    # 无论是单体和单体的集成，还是单体与combo的集成，或者combo与combo的集成
    fromBuilding = buildingList[0]
    # 251210 可以用translation直接获取全局坐标
    fromLoc = fromBuilding.matrix_world.translation
    comboNewObj = __addComboRoot(templateName='建筑组合',
                                 location=fromLoc)
    comboNewColl = comboNewObj.users_collection[0]

    # 将所有对象迁移到新comboNew中
    for buildingObj in buildingList:
        buildingObj:bpy.types.Object
        # 预先保存对象的原始父节点
        parentCombo = utils.getComboRoot(buildingObj)
        # 关联父对象
        mw = buildingObj.matrix_world
        buildingObj.parent = comboNewObj
        buildingObj.matrix_world = mw
        # 更新combo_location
        bData:acaData = buildingObj.ACA_data
        bData['combo_location'] = buildingObj.location
        bData['combo_rotation'] = buildingObj.rotation_euler
        # 更新parent id
        bData['combo_parent'] = comboNewObj.ACA_data.aca_id
        # 关联集合目录
        buildingColl = buildingObj.users_collection[0]
        comboNewColl.children.link(buildingColl)
        # 从原集合目录中移除
        if parentCombo is None:
            # 如果单体建筑，从'ACA筑韵古建'目录中移除
            oldColl = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
        else:
            # 如果是combo子建筑，从原来的combo中移除
            oldColl = parentCombo.users_collection[0]
        oldColl.children.unlink(buildingColl)

    # 清理老combo
    # 如果是单体与集合，或集合与集合的合并，需要清理
    # 如果是单体与单体的组合就不涉及
    for comboObj in comboList:
        comboObj: bpy.types.Collection
        # 迁移comboObj的postProcess
        comboData:acaData = comboObj.ACA_data
        ppData = comboData.postProcess
        if len(ppData) > 0:
            for item in ppData:
                newpp = comboNewObj.ACA_data.postProcess.add()
                newpp.action = item.action
                newpp.parameter = item.parameter

        comboColl = comboObj.users_collection[0]
        # 迁移子对象，如bool对象等
        for obj in comboColl.objects:
            obj:bpy.types.Object
            # 跳过老combo root
            if obj.ACA_data.aca_type == con.ACA_TYPE_COMBO:continue
            # 绑定在新组合root
            mw = obj.matrix_world
            obj.parent = comboNewObj
            obj.matrix_world = mw
            # 其他对象迁移到新combo中
            comboColl.objects.unlink(obj)
            comboNewColl.objects.link(obj)

        # 删除combo Coll
        bpy.data.collections.remove(comboColl)  

    return {'FINISHED'},comboNewObj