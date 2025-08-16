# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   营造的主入口
#   判断是建造一个新的单体建筑，还是院墙等附加建筑
import bpy
from mathutils import Vector,Euler,Matrix,geometry
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import template
from . import buildFloor
from . import buildYardWall
from . import buildRoof
from . import texture as mat
from . import buildCombo

# 全局参数 -----------------
# 是否在运行
isFinished = True
# 当前状态提示文字
buildStatus = ''
# 进度百分比
progress = 0
# 集合的排除属性备份
collExclude = {}

def buildSingle(acaType,
                  templateName,
                  comboObj = None):
    # 根据模板类型调用不同的入口
    if acaType == con.ACA_TYPE_BUILDING:
        buildFloor.buildFloor(
            buildingObj = None,
            templateName = templateName,
            comboObj = comboObj,
        )
    elif acaType == con.ACA_TYPE_YARDWALL:
        buildYardWall.buildYardWall(
            buildingObj = None,
            templateName = templateName
        )
    else:
        utils.popMessageBox("无法创建该类型的建筑：" + templateName)
    return

# 排除目录下的其他建筑
# isExclude=True是排除，False恢复
# keepObj非必须，传入时当前目录不排除
def __excludeOther(isExclude=True,
                   keepObj:bpy.types.Object=None,
    ):
    # 根目录
    rootColl = utils.setCollection(
        con.COLL_NAME_ROOT,isRoot=True)
    
    # 查找当前建筑所在的目录
    if keepObj != None:
        comboObj = utils.getComboRoot(keepObj)
        if comboObj is None:
            currentColl = keepObj.users_collection[0]
        else:
            currentColl = comboObj.users_collection[0]
    else:
        currentColl = None
    
    # 全局参数，缓存的集合可见性
    global collExclude
    # 排除时，更新缓存
    if isExclude:
        collExclude.clear()

    # 排除其他建筑
    for coll in rootColl.children:
        # 如果是当前建筑所在的目录，跳过
        if coll == currentColl:
            continue
        
        # 排除集合时，将集合状态存入缓存
        if isExclude:
            layerColl = utils.recurLayerCollection(
                bpy.context.view_layer.layer_collection, 
                coll.name,)
            # 将键值对存入字典
            collExclude[coll.name] = layerColl.exclude
            # print(f"write collexclude {coll.name}:{layerColl.exclude}")
        # 恢复集合时，从缓存判断
        else:
            # 缓存有滞后性，本次新增的集合没有键值
            if coll.name in collExclude:
                layerExclude = collExclude[coll.name]
                # print(f"read collexclude {coll.name}:{layerExclude}")
                # 如果原始状态就是隐藏，则跳出本次循环
                if layerExclude:
                    # print(f"collexclude skip {coll.name}")
                    continue

        utils.hideCollection(coll.name,isExclude=isExclude)
    utils.redrawViewport() # 刷新视图
    return

# 开始新的营造
def build():
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    # 待营造的模板，来自用户界面上的选择
    from . import data
    scnData : data.ACA_data_scene = bpy.context.scene.ACA_data
    templateList = scnData.templateItem
    templateIndex = scnData.templateIndex
    templateName = templateList[templateIndex].name

    # 获取模板类型，建筑或院墙
    acaType = template.getBuildingType(templateName)

    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther()

    if acaType != con.ACA_TYPE_COMBO:
        # 单体建筑
        buildSingle(
            acaType = acaType,
            templateName = templateName
        )
    else:
        # 组合建筑
        buildCombo.buildCombo(templateName)
    
    # 关闭进度条
    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(isExclude=False)

    # 关闭视角自动锁定
    scnData['is_auto_viewall'] = False

    return {'FINISHED'}

def updateBuilding(buildingObj:bpy.types.Object,
                   reloadAssets = False):
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther(keepObj=buildingObj)

    # 根据模板类型调用不同的入口
    # 查找是否存在comboRoot
    comboObj = utils.getComboRoot(buildingObj)
    # 组合建筑
    if comboObj is not None:
        buildCombo.updateCombo(buildingObj,
                    reloadAssets=reloadAssets)
    # 单体建筑
    else:
        # 载入数据
        bData:acaData = buildingObj.ACA_data
        if bData.aca_type == con.ACA_TYPE_BUILDING:
            buildFloor.buildFloor(buildingObj,
                        reloadAssets=reloadAssets)
        # 围墙
        elif bData.aca_type == con.ACA_TYPE_YARDWALL:
            buildYardWall.buildYardWall(buildingObj,
                        reloadAssets=reloadAssets)
        else:
            utils.popMessageBox(f"无法创建该类型的建筑,{bData.aca_type}")
        
        # 聚焦台基
        focusObj = utils.getAcaChild(
            buildingObj,con.ACA_TYPE_PLATFORM)
        if focusObj is not None:
            utils.focusObj(focusObj)

    # 关闭进度条
    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(isExclude=False,
                   keepObj=buildingObj)

    return {'FINISHED'}

# 删除建筑
def delBuilding(buildingObj:bpy.types.Object,
                withCombo = True,
                ):
    # 判断是否为组合建筑
    comboObj = utils.getComboRoot(buildingObj)
    # 如果是单体建筑，从根目录删除
    if comboObj is None:
        # 父目录是“ACA筑韵古建”
        parentColl = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
        # 删除单体目录
        delColl = buildingObj.users_collection[0]
    # 如果是组合建筑，判断删单体还是全删
    else:
        # 全删
        if withCombo:
            # 父目录是“ACA筑韵古建”
            parentColl = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
            # 删除combo目录
            delColl = comboObj.users_collection[0]
        # 仅删个体
        else:
            # 父目录就是combo目录
            parentColl = comboObj.users_collection[0]
            # 删除单体目录
            delColl = buildingObj.users_collection[0]

    # 删除目录
    parentColl.children.unlink(delColl)
    bpy.data.collections.remove(delColl)
    # 清理垃圾  
    utils.delOrphan()
    return {'FINISHED'}

# 清除所有的装修、踏跺等，重新生成地盘
def resetFloor(buildingObj:bpy.types.Object):
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther(keepObj=buildingObj)

    # 查找是否存在comboRoot
    comboObj = utils.getComboRoot(buildingObj)
    # 根据模板类型调用不同的入口
    # 组合建筑
    if comboObj is not None:
        buildCombo.updateCombo(buildingObj,resetFloor=True)
    else:
        # 载入数据
        bData:acaData = buildingObj.ACA_data
        # 单体建筑
        if bData.aca_type == con.ACA_TYPE_BUILDING:
            buildFloor.resetFloor(buildingObj)
        else:
            utils.popMessageBox("无法创建该类型的建筑：" + bData.aca_type)

    # 关闭进度条
    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(isExclude=False,
                   keepObj=buildingObj)

    return  {'FINISHED'}

# 重新生成屋顶
def resetRoof(buildingObj:bpy.types.Object):    
    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther(keepObj=buildingObj)

    # 区分是否是Combo组合建筑
    comboObj = utils.getComboRoot(buildingObj)
    # 组合建筑
    if comboObj is not None:
        buildCombo.updateCombo(buildingObj,
                               resetRoof=True)
    # 单体建筑
    else:
        buildRoof.__clearRoof(buildingObj)
        buildRoof.buildRoof(buildingObj)

    # 关闭进度条
    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(isExclude=False,
                   keepObj=buildingObj)
    return  {'FINISHED'}

# 纵剖视图
def addSection(buildingObj:bpy.types.Object,
               sectionPlan='X+'):
    bData = buildingObj.ACA_data
    # 剖视修改器名称，便于找回
    sectionModName = 'Section'
    # 当前剖视模式
    currentPlan = None
    joinedObj = None

    # 1、验证是否合并？是否剖视？ -----------------------
    # 1.1、如果还未合并，先做合并
    if bData.aca_type != con.ACA_TYPE_BUILDING_JOINED:
        joinedObj = joinBuilding(
            buildingObj,sectionPlan=sectionPlan)
    # 1.2、如果已经合并，确认是否已经做了剖视
    else:
        # 当前剖视模式
        if 'sectionPlan' in bData:     
            currentPlan = bData['sectionPlan']
        # 1.2.1、已合并但未作剖视的新合并对象，无需特殊处理
        if currentPlan == None:
            joinedObj = buildingObj
        # 1.2.2、已合并已剖视的对象，需要重新处理
        else:
            # 1.2.2.1、如果剖视方案相同，解除剖视
            if sectionPlan == currentPlan:
                # 这里解除合并的同时，就会解除剖视
                __undoJoin(buildingObj)
                return
            # 1.2.2.2、剖视方案不同，重新合并
            else:
                # 解除合并
                buildingObj = __undoJoin(buildingObj)
                joinedObj = joinBuilding(
                    buildingObj,sectionPlan=sectionPlan)
    
    # 验证是否合并成功
    if joinedObj == None:
        utils.outputMsg("合并失败，无法继续做剖视图")
        return
    
    # 合并的结果需要进行一次刷新
    # 否则可能出现getBoundCenter时结果错误
    utils.updateScene()
    
    # 2、开始做剖视 -----------------------
    # 指定在合并目录中操作
    coll:bpy.types.Collection = utils.setCollection(
                'ACA古建.合并',isRoot=True,colorTag=3)
    
    # 寻找剖视对象
    sectionObjs = []
    if joinedObj.children:
        # 针对子对象做剖视
        for child in joinedObj.children:
            sectionObjs.append(child)
    else:
        # 针对根对象做剖视
        sectionObjs.append(joinedObj)

    # 逐个对象添加剖视修改器
    for sectionObj in sectionObjs:
        # 1、清除老的bool ---------------------------
        # 确认该对象是否已经有boolean
        mod = sectionObj.modifiers.get(sectionModName)
        # 已有boolean的删除boolCube和modifier
        if mod != None:
            # 删除布尔对象
            utils.delObject(mod.object)
            # 删除修改器
            sectionObj.modifiers.remove(mod)
        
        # 2、新建bool对象 -------------------------------
        # 命名
        boolName = 'b.' + sectionObj.name
        # 略作放大
        sectionDim = (Vector(sectionObj.dimensions) 
                * Vector((1.1,1.1,1.1))
                )
        sectionLoc = utils.getBoundCenter(sectionObj)
        # 创建剖视布尔对象
        boolObj = utils.addCube(
            name=boolName,
            dimension=sectionDim,
            location=sectionLoc,
            parent=sectionObj
        )
        
        # 3、载入剖视方案 --------------------------
        # 设置剖视方案
        boolPlan = __getSectionPlan(boolObj,sectionPlan)
        # 布尔材质
        mat.paint(boolObj,boolPlan['mat'])
        # 布尔位移
        boolObj.location += boolPlan['offset']
        # 设置外观
        utils.hideObjFace(boolObj)
        # boolObj.hide_select = True    # 禁止选中

        # 仅对需要布尔的对象添加修改器
        if boolPlan['bool']:
            # 添加boolean
            utils.addModifierBoolean(
                name=sectionModName,
                object=sectionObj,
                boolObj=boolObj,
                operation=boolPlan['operation'],
            )
    
    joinedObj.ACA_data['sectionPlan']=sectionPlan 
    utils.focusObj(joinedObj)
    return

# 剖面图方案
def __getSectionPlan(boolObj:bpy.types.Object,
                     sectionType='X+',):
    Y_reserve = -0.35
    offset = Vector((0,0,0))
    origin_loc = boolObj.location.copy()
    layerName = boolObj.name

    # 每一层对象的布尔处理存入字典
    boolPlan = {}
    boolPlan['bool'] = False
    # 默认无位移
    boolPlan['offset'] = Vector((0,0,0))
    # 操作类型，DIFFERENCE，INTERSECT，UNION
    boolPlan['operation'] = 'DIFFERENCE'
    boolPlan['mat'] = con.M_STONE

    # Y剖面正方向
    if sectionType == 'Y+':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            0,
            boolObj.dimensions.y/2 - Y_reserve - origin_loc.y,
            0
        ))
    elif sectionType == 'Y-':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            0,
            -boolObj.dimensions.y/2 + Y_reserve - origin_loc.y,
            0
        ))
    elif sectionType == 'X+':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            boolObj.dimensions.x/2 - origin_loc.x,
            0,
            0
        ))
    elif sectionType == 'X-':
        boolPlan['bool'] = True
        boolPlan['offset'] = Vector((
            -boolObj.dimensions.x/2 - origin_loc.x,
            0,
            0
        ))
    # 穿墙透壁模式
    elif sectionType == 'A':
        # 1-台基层，不裁剪
        if con.COLL_NAME_BASE in layerName:
            pass
        # 2-柱网层
        elif con.COLL_NAME_PILLER in layerName:
            pass
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            pass
        # 4-斗栱层
        elif con.COLL_NAME_DOUGONG in layerName:
            pass
        # 5-梁架层
        elif con.COLL_NAME_BEAM in layerName:
            pass
        # 6-椽架层
        elif con.COLL_NAME_RAFTER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 7-山花望板层
        elif con.COLL_NAME_BOARD in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.4 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 8-瓦作层，裁剪整个右侧
        elif con.COLL_NAME_TILE in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.35 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
    elif sectionType == 'B':
        # 1-台基层，不裁剪
        if con.COLL_NAME_BASE in layerName:
            pass
        # 2-柱网层
        elif con.COLL_NAME_PILLER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                boolObj.dimensions.z*0.3
            ))
            boolPlan['mat'] = con.M_WOOD
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                boolObj.dimensions.z*0.2,
            ))
            boolPlan['mat'] = con.M_STONE
        # 4-斗栱层
        elif con.COLL_NAME_DOUGONG in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 5-梁架层
        elif con.COLL_NAME_BEAM in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 6-椽架层
        elif con.COLL_NAME_RAFTER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 7-山花望板层
        elif con.COLL_NAME_BOARD in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.4 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 8-瓦作层，裁剪整个右侧
        elif con.COLL_NAME_TILE in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.35 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
    elif sectionType == 'C':
        # 1-台基层，不裁剪
        if con.COLL_NAME_BASE in layerName:
            pass
        # 2-柱网层
        elif con.COLL_NAME_PILLER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                boolObj.dimensions.z*0.3
            ))
            boolPlan['mat'] = con.M_WOOD
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0, 
                boolObj.dimensions.z*0.2,
            ))
            boolPlan['mat'] = con.M_STONE
        # 4-斗栱层
        elif con.COLL_NAME_DOUGONG in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 5-梁架层
        elif con.COLL_NAME_BEAM in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 6-椽架层
        elif con.COLL_NAME_RAFTER in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 7-山花望板层
        elif con.COLL_NAME_BOARD in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.4 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_WOOD
        # 8-瓦作层，裁剪整个右侧
        elif con.COLL_NAME_TILE in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.35 - origin_loc.x,
                0,
                0,
            ))
            boolPlan['mat'] = con.M_STONE

    return boolPlan

# 组合建筑为一个实体
# 或者解除组合恢复
def joinBuilding(buildingObj:bpy.types.Object,
                 useLayer=False, # 是否分层合并
                 sectionPlan=None, # 可根据剖视方案自动决定是否分层
                ):
    # 判断组合或解除组合
    buildingObj,bData,objData = utils.getRoot(buildingObj)
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        __undoJoin(buildingObj)
        return
    
    # 1、参数和变量 --------------------------
    # 合并对象的名称后缀
    joinSuffix = '.joined'
    collcopySuffix = '.collcopy'

    # 根据剖视方案决定是否分层
    if sectionPlan != None:
        if sectionPlan in ('X+','X-','Y+','Y-'):
            useLayer = False
        else:
            useLayer = True
    # 墙体只有一级层次，不区分是否分层
    if bData.aca_type == con.ACA_TYPE_YARDWALL:
        useLayer = False
    
    # 2、准备合并的组织结构 ------------------------------------
    # 2.0、combo组合替换根对象
    isCombo = False
    comboObj = utils.getComboRoot(buildingObj)
    if comboObj is not None:
        buildingObj = comboObj
        isCombo = True

    # 2.1、复制建筑的整个集合，在复制集合上进行合并
    # 这样不会影响原有的生成模型
    collName = buildingObj.users_collection[0].name
    collCopy = utils.copyCollection(collName,collName + collcopySuffix)

    # 2.2、新建/绑定合并集合
    collJoined = utils.setCollection(
            'ACA古建.合并',isRoot=True,colorTag=3)
    
    # 2.3、复制原始建筑根节点，做为合并对象的根节点
    # 第一个对象就是建筑根节点，这样判断可能不够安全
    buildingObjCopy = collCopy.objects[0]    
    # 复制生成分层合并的父节点
    joinedRoot = utils.copySimplyObject(buildingObjCopy)
    # 设置名称
    joinedRoot.name = buildingObj.name + joinSuffix
    # 标示为ACA对象
    joinedRoot.ACA_data['aca_obj'] = True
    joinedRoot.ACA_data['aca_type'] = \
        con.ACA_TYPE_BUILDING_JOINED

    # 3、开始合并对象 -------------------------------------
    # 3.1、选择所有下级层次对象
    partObjList = []    # 在addChild中递归填充
    def addChild(buildingObjCopy):
        for childObj in buildingObjCopy.children:
            useObj = True
            # 仅处理可见的实体对象
            if childObj.type not in ('MESH'):
                useObj = False
            if childObj.hide_viewport or childObj.hide_render:
                useObj = False
            # 记录对象名称
            if useObj:
                partObjList.append(childObj)
            # 次级递归
            if childObj.children:
                addChild(childObj)
    
    # 3.2、合并对象
    # 判断是否需要分层合并
    layerList = []
    if useLayer:
        # 如果组合建筑，将每个单体的每一层都独立追加
        if isCombo:
            for singleBuilding in buildingObjCopy.children:
                layerList += singleBuilding.children
        # 单体建筑以本身的分层处理
        else:
            layerList = buildingObjCopy.children
    else:
        # 不分层
        layerList.append(buildingObjCopy)

    # 3.3、分层合并
    for layer in layerList:
        # 递归填充待合并对象
        partObjList.clear()
        addChild(layer)
        if len(partObjList) == 0 :
            print(f"{layer.name}没有需要合并的对象，继续...")
            continue
        
        # 区分是否分层的不同命名规则
        if useLayer:
            # 合并名称以层标注
            joinedName = (buildingObj.name 
                          + '.' 
                          + layer.name)
        else:
            # 合并名称直接加'joined'后缀
            joinedName = buildingObj.name + joinSuffix

        # 合并前提取第一个子对象的父节点矩阵
        # 为后续重新绑定父节点做准备
        if isCombo:
            # 组合建筑要分别取两层的转换
            baseMatrix = partObjList[0].parent.parent.matrix_local.copy()
        else:
            # 一般可能是台基层，或柱网层根节点
            baseMatrix = partObjList[0].parent.matrix_local.copy()

        # 合并对象
        joinedModel = utils.joinObjects(
            objList=partObjList,
            newName=joinedName,)
        
        # 区分是否分层的坐标映射
        if useLayer:
            if isCombo:
                # 组合建筑要分别取两层的转换
                matrix = (joinedModel.parent.parent.matrix_local 
                          @ joinedModel.parent.matrix_local)
            else:
                # 取各个分层的局部坐标
                matrix = joinedModel.parent.matrix_local  
        else:
            # 墙体只有一级层次，不区分是否分层
            if joinedModel.parent.ACA_data.aca_type == \
                con.ACA_TYPE_YARDWALL:
                matrix = joinedModel.matrix_local
            else:                
                # 不分层的建筑体，取合并基准的父节点坐标系
                matrix = baseMatrix

        # 重新绑定父级对象
        joinedModel.parent = joinedRoot
        # 重新映射坐标
        joinedModel.location = matrix @ joinedModel.location
        utils.applyTransform2(joinedModel,
                                use_location=True,
                                use_rotation=True,
                                use_scale=True)

        # 2、添加到合并目录
        collJoined.objects.link(joinedModel)

    # 3、删除复制的建筑，包括复制的集合
    delBuilding(buildingObjCopy)

    # 4、隐藏原建筑
    utils.hideCollection(collName)

    # 5、聚焦根节点
    utils.focusObj(joinedRoot)

    return joinedRoot

# 解除建筑合并
def __undoJoin(buildingObj:bpy.types.Object):
    # 合并对象的名称后缀
    joinSuffix = '.joined'

    # 恢复目录显示
    collName = buildingObj.name.removesuffix(joinSuffix)
    utils.hideCollection(collName,isExclude=False)

    # 彻底删除原来的合并对象
    utils.deleteHierarchy(buildingObj,
            del_parent=True)

    # 选择目录中的所有构件
    src_coll = bpy.data.collections.get(collName)
    oldbuildingObj = src_coll.objects[0]
    utils.selectAll(oldbuildingObj)
    bpy.context.view_layer.objects.active = oldbuildingObj

    return oldbuildingObj