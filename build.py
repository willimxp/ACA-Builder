# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   营造的主入口
#   判断是建造一个新的单体建筑，还是院墙等附加建筑
import bpy
import math
import bmesh
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
    validate =  __validate(buildingObj)
    if validate is not None:
        utils.popMessageBox(validate)
        return {'CANCELLED'}
    
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
    # 判断是否为合并建筑
    bData:acaData = buildingObj.ACA_data
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        # 找到未合并建筑
        buildingJoined = buildingObj
        buildingObj = __getJoinedOriginal(buildingJoined)
        if buildingObj is None:
            raise Exception("删除失败，未找到建筑未合并的本体")
        # 删除合并建筑
        utils.deleteHierarchy(buildingJoined,del_parent=True)
    
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
    validate =  __validate(buildingObj)
    if validate is not None:
        utils.popMessageBox(validate)
        return {'CANCELLED'}
    
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
                con.COLL_NAME_ROOT_JOINED,isRoot=True,colorTag=3)
    
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
        utils.hideObj(boolObj)
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
    # 载入数据
    # boolObj是切割体，parent是层合并对象，该对象在合并时继承了建筑的combo_type
    bData = boolObj.parent.ACA_data
    # 区分是否为楼阁等组合对象
    if bData.combo_type in (con.COMBO_MAIN,con.COMBO_TERRACE):
        isComboNext = False
    else:
        isComboNext = True
    
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
            if not isComboNext:
                # 底层，不裁剪
                pass
            else:
                # 上层楼板裁剪1/4
                boolPlan['bool'] = True
                boolPlan['offset'] = Vector((
                    boolObj.dimensions.x*0.5 - origin_loc.x,
                    -boolObj.dimensions.y*0.5 + Y_reserve,
                    0
                ))
                boolPlan['mat'] = con.M_STONE
        # 2-柱网层
        elif con.COLL_NAME_PILLER in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.3
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                boolZ
            ))
            boolPlan['mat'] = con.M_WOOD
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.2
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5 + Y_reserve,
                boolZ,
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
        # 9-平座层，裁剪1/4
        elif con.COLL_NAME_BALCONY in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                -boolObj.dimensions.y*0.5,
                0,
            ))
            boolPlan['mat'] = con.M_STONE
    elif sectionType == 'C':
        # 1-台基层
        if con.COLL_NAME_BASE in layerName:
            if not isComboNext:
                # 底层，不裁剪
                pass
            else:
                # 上层楼板裁剪一半
                boolPlan['bool'] = True
                boolPlan['offset'] = Vector((
                    boolObj.dimensions.x*0.5 - origin_loc.x,
                    0,
                    0
                ))
                boolPlan['mat'] = con.M_STONE
        # 2-柱网层
        elif con.COLL_NAME_PILLER in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.3
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0,
                boolZ
            ))
            boolPlan['mat'] = con.M_WOOD
        # 3-装修层
        # 因为装修没有做到柱头（额枋），所以实际比柱网层裁剪更低
        elif con.COLL_NAME_WALL in layerName:
            # 判断combo对象
            if isComboNext:
                boolZ = 0
            else:
                boolZ = boolObj.dimensions.z*0.2
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
                0, 
                boolZ,
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
        # 9-平座层，裁剪一半
        elif con.COLL_NAME_BALCONY in layerName:
            boolPlan['bool'] = True
            boolPlan['offset'] = Vector((
                boolObj.dimensions.x*0.5 - origin_loc.x,
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
    
    # 251114 manifold boolean在合并后再做重复材质清理，会导致材质混乱
    # 所以，统一在合并前清理材质
    utils.updateScene()
    utils.cleanDupMat()
    
    # 1、参数和变量 --------------------------
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
    # 250909 确保目录与对象名称一致，以免后续取消组合时找不到原目录
    buildingObj.users_collection[0].name = buildingObj.name
    # 这样不会影响原有的生成模型
    collName = buildingObj.users_collection[0].name
    collCopy = utils.copyCollection(collName,collName + collcopySuffix)

    # 2.2、新建/绑定合并集合
    collJoined = utils.setCollection(
            con.COLL_NAME_ROOT_JOINED,isRoot=True,colorTag=3)
    
    # 2.3、复制原始建筑根节点，做为合并对象的根节点
    # 第一个对象就是建筑根节点，这样判断可能不够安全
    buildingObjCopy = collCopy.objects[0]    
    # 复制生成分层合并的父节点
    joinedRoot = utils.copySimplyObject(buildingObjCopy)
    # 设置名称
    joinedRoot.name = buildingObj.name + con.JOIN_SUFFIX
    # 标示为ACA对象
    joinedRoot.ACA_data['aca_obj'] = True
    joinedRoot.ACA_data['aca_type'] = \
        con.ACA_TYPE_BUILDING_JOINED

    # 3、开始合并对象 -------------------------------------
    # 3.1、选择所有下级层次对象
    partObjList = []    # 在addChild中递归填充
    def addChild(buildingObjCopy):
        for childObj in buildingObjCopy.children:
            childObj: bpy.types.Object
            useObj = True
            # 仅处理可见的实体对象
            if childObj.type not in ('MESH'):
                useObj = False
            if childObj.hide_viewport or childObj.hide_render:
                useObj = False
            # 251204 判断对象所属的集合是否可见
            parentColl = childObj.users_collection[0]
            print(f"{parentColl.name}-{parentColl.hide_viewport}-{childObj.name}")
            if parentColl.hide_viewport:
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
            joinedName = buildingObj.name + con.JOIN_SUFFIX

        # 合并前提取第一个子对象的父节点矩阵
        # 为后续重新绑定父节点做准备
        if isCombo:
            # 组合建筑要分别取两层的转换
            baseMatrix = partObjList[0].parent.parent.matrix_local.copy()
        else:
            # 一般可能是台基层，或柱网层根节点
            baseMatrix = partObjList[0].parent.matrix_local.copy()

        # 250929 提取combo对象的属性
        if isCombo:
            comboType = partObjList[0].parent.parent.ACA_data.combo_type
        
        # 合并对象
        joinedModel = utils.joinObjects(
            objList=partObjList,
            newName=joinedName,)
        
        # 250929 继承父建筑的combo_type，以便剖视图区分是否为底层建筑还是楼阁
        if isCombo:
            joinedModel.ACA_data['combo_type'] = comboType
            # print(joinedName + " joinedComboType=" + comboType)
        
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
    # 恢复目录显示
    collName = buildingObj.name.removesuffix(con.JOIN_SUFFIX)
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

# 参数合法性验证
def __validate(buildingObj:bpy.types.Object):
    bData:acaData = buildingObj.ACA_data
    dk = bData.DK
    
    # 盝顶验证
    if (bData.roof_style == con.ROOF_LUDING):
        ludingExtend = bData.luding_rafterspan
        if bData.use_dg:
            ludingExtend += bData.dg_extend
        if ludingExtend < 3*dk:
            return "盝顶设置异常，斗栱出跳或盝顶檐步架宽太小。请使用有出跳的斗栱，或增加盝顶檐步架宽。"
        
    # 平坐验证
    if (bData.roof_style == con.ROOF_BALCONY):
        if not bData.use_dg:
            if bData.dg_extend < 0.001:
                return "无法生成平坐，请启用斗栱，且斗栱应该有足够的出跳。"
    return

# 建筑组合
def unionBuilding(context:bpy.types.Context):
    # 1、获取选中的建筑
    fromBuilding = None
    fromBuildingJoined = None
    toBuilding = None
    toBuildingJoined = None
    # 遍历选中的对象，如果已合并的直接添加，未合并的记录在未合并列表
    for obj in context.selected_objects:
        # 活动主建筑
        if obj == context.active_object:
            building,bData,oData = utils.getRoot(obj)
            if building.ACA_data.aca_type == con.ACA_TYPE_BUILDING_JOINED:
                fromBuildingJoined = building
                # 已合并的找到原始建筑
                fromBuilding = __getJoinedOriginal(building)
                bData = fromBuilding.ACA_data
            else:
                fromBuilding = building        
        # 副建筑
        else:
            if toBuilding is not None:
                utils.popMessageBox('不止两个建筑')
                return {'CANCELLED'}
            building,mData,oData = utils.getRoot(obj)
            if building.ACA_data.aca_type == con.ACA_TYPE_BUILDING_JOINED:
                toBuildingJoined = building
                # 已合并的找到原始建筑
                toBuilding = __getJoinedOriginal(building)
                mData = toBuilding.ACA_data
            else:
                toBuilding = building

    # 校验应该有两个建筑(在正式合并前检验，避免回滚)
    if not fromBuilding or not toBuilding:
        utils.popMessageBox("请选择需要组合的2个建筑")
        return {'CANCELLED'}

    # 方案一：勾连搭
    # 两个建筑面阔相等，且为平行相交
    if (bData.x_total == mData.x_total 
        and (fromBuilding.rotation_euler.z ==
              toBuilding.rotation_euler.z)
        ):
        
        # 是否相交
        buildingSpan = abs(fromBuilding.location.y 
                           - toBuilding.location.y)
        roofSpan = (bData.y_total+mData.y_total)/2+21*bData.DK
        if buildingSpan > roofSpan:
            utils.popMessageBox("建筑不相交，无法进行组合")
            return {'CANCELLED'}
        
        result = __unionGoulianda(
            fromBuilding,
            toBuilding,
            fromBuildingJoined,
            toBuildingJoined
        )
        return result
    
    # 方案二：平行抱厦
    baoshaRot = fromBuilding.rotation_euler.z
    mainRot = toBuilding.rotation_euler.z
    angleDiff = abs(baoshaRot - mainRot)
    xDiff = abs(fromBuilding.location.x - toBuilding.location.x)
    yDiff = abs(fromBuilding.location.y - toBuilding.location.y)
    if (bData.x_total != mData.x_total
        and xDiff < abs(mData.x_total-bData.x_total)/2
        and yDiff > abs(mData.y_total-bData.y_total)/2
        and angleDiff < 0.001
        ):
        
        # 是否相交
        buildingSpan = abs(fromBuilding.location.y 
                           - toBuilding.location.y)
        roofSpan = (bData.y_total+mData.y_total)/2+21*bData.DK
        if buildingSpan > roofSpan:
            utils.popMessageBox("建筑不相交，无法进行组合")
            return {'CANCELLED'}

        # 设置面阔较小的为fromBuilding(抱厦)
        if bData.x_total > mData.x_total:
            temp = fromBuilding
            fromBuilding = toBuilding
            toBuilding = temp
            temp = fromBuildingJoined
            fromBuildingJoined = toBuildingJoined
            toBuildingJoined = temp
            bData:acaData = fromBuilding.ACA_data
            mData:acaData = toBuilding.ACA_data

        # 抱厦为悬山顶
        if bData.roof_style in (
            con.ROOF_XUANSHAN,con.ROOF_XUANSHAN_JUANPENG):
            result = __unionParallelXuanshan(
                fromBuilding,
                toBuilding,
                fromBuildingJoined,
                toBuildingJoined
            )
            return result
        # 抱厦为歇山顶
        if bData.roof_style in (
            con.ROOF_XIESHAN,con.ROOF_XIESHAN_JUANPENG):
            result = __unionParallelXieshan(
                fromBuilding,
                toBuilding,
                fromBuildingJoined,
                toBuildingJoined
            )
            return result
    
    # 方案三：丁字形抱厦
    # 设置进深较小的为fromBuilding(抱厦)
    if bData.y_total > mData.y_total:
        temp = fromBuilding
        fromBuilding = toBuilding
        toBuilding = temp
        temp = fromBuildingJoined
        fromBuildingJoined = toBuildingJoined
        toBuildingJoined = temp
        bData = fromBuilding.ACA_data
        mData = toBuilding.ACA_data
    # 1、抱厦旋转90度后，与前后檐相交
    baoshaRot = fromBuilding.rotation_euler.z
    mainRot = toBuilding.rotation_euler.z
    angleDiff = abs(baoshaRot - mainRot)
    xDiff = abs(fromBuilding.location.x - toBuilding.location.x)
    yDiff = abs(fromBuilding.location.y - toBuilding.location.y)
    if (abs(angleDiff - math.radians(90)) < 0.001
        and xDiff < abs(mData.x_total-bData.x_total)/2):
        result = __unionCrossBaosha(
            fromBuilding,
            toBuilding,
            fromBuildingJoined,
            toBuildingJoined,
            dir='Y'
        )
        return result
    # 2、抱厦直接与两山檐相交
    if (angleDiff < 0.001
        and yDiff < abs(mData.y_total-bData.y_total)/2):
        result = __unionCrossBaosha(
            fromBuilding,
            toBuilding,
            fromBuildingJoined,
            toBuildingJoined,
            dir='X'
        )
        return result
    
    # 未找到
    utils.popMessageBox("无法处理的建筑合并")
    return {'CANCELLED'}


# 获取合并建筑对应的原建筑
def __getJoinedOriginal(joinedBuilding: bpy.types.Object):
    collName = joinedBuilding.name.removesuffix(con.JOIN_SUFFIX)
    src_coll = bpy.data.collections.get(collName)
    src_building = src_coll.objects[0]
    return src_building

# 建筑组合：勾连搭
# 适用于主建筑和副建筑平行，且面阔相等
def __unionGoulianda(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object):    
    # 载入数据
    bData = fromBuilding.ACA_data
    dk = bData.DK
    
    # 计算屋顶碰撞点
    crossPoint = __getRoofCrossPoint(fromBuilding,toBuilding)
    if crossPoint == 'CANCELLED': return {'CANCELLED'}
    
    # 建筑合并
    if fromBuildingJoined is None:
        fromBuildingJoined = joinBuilding(fromBuilding)
    if toBuildingJoined is None:
        toBuildingJoined = joinBuilding(toBuilding)

    # 生成剪切体 ----------------------------------
    # 1、出檐
    # 椽飞出檐
    eave_extend = (con.YANCHUAN_EX*dk 
              + con.FLYRAFTER_EX*dk)
    # 斗栱出檐
    if bData.use_dg:
        eave_extend += bData.dg_extend*bData.dg_scale[0]
    # 出冲
    eave_extend += bData.chong * con.YUANCHUAN_D*dk
    # 保险数
    eave_extend += 20*dk

    # 2、建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    # 3、裁剪体大小、位置
    boolX = bData.x_total + eave_extend*2
    boolY = bData.y_total + eave_extend*2
    boolDim = (boolX,boolY,buildingH)
    # 根据屋顶碰撞点定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolY/2
    else:
        offset = -boolY/2
    
    boolLoc = (0,
               offset+crossPoint.y, # 碰撞点
               buildingH/2)
    boolObj = utils.addCube(
        name="勾连搭" + con.BOOL_SUFFIX,
        location=boolLoc,
        dimension=boolDim,
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 4、添加bool modifier
    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        # 跳过bool对象本身
        if layer == boolObj: continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='INTERSECT',
        )
    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )
    if fromBuildingJoined:
        utils.focusObj(fromBuildingJoined)

    return {'FINISHED'}

# 建筑组合：平行抱厦-悬山
# fromBuilding为面阔较小的抱厦
def __unionParallelXuanshan(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object):
    # 载入数据
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data
    dk = bData.DK

    # 1、确保抱厦和主建筑分层合并
    # 抱厦进行分层合并
    if fromBuildingJoined:
        # 强制解除合并
        __undoJoin(fromBuildingJoined)
    # 重新分层合并
    fromBuildingJoined = joinBuilding(fromBuilding,useLayer=True)
    # 主建筑分层合并
    # 已合并的话，检查是否分层
    if toBuildingJoined:
        # 合并根节点
        building,mData,oData = utils.getRoot(toBuildingJoined)
        # 如果没有分层，则重新分层
        if len(building.children) == 1:
            __undoJoin(building)
            toBuildingJoined = joinBuilding(toBuilding,useLayer=True)
        else:
            # 如果已经分层，则保留
            toBuildingJoined = building
    # 未合并的话，进行分层合并
    else:
        toBuildingJoined = joinBuilding(toBuilding,useLayer=True)

    # 一、裁剪屋顶 ------------------------
    # 包括：装修、斗栱、梁架、椽架
    # 不包括：台基、柱网、装修
    # 1、主建筑屋顶裁剪：宽到柱外皮，深到瓦面交界点，高覆盖建筑高度
    # 瓦面碰撞点
    crossPoint = __getRoofCrossPoint(fromBuilding,toBuilding)
    if crossPoint == 'CANCELLED': return {'CANCELLED'}

    # 建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    # 出檐
    eave_extend = (con.YANCHUAN_EX*dk 
              + con.FLYRAFTER_EX*dk)
    # 斗栱出檐
    if bData.use_dg:
        eave_extend += bData.dg_extend*bData.dg_scale[0]
    # 保险数
    eave_extend += 20*dk

    # 剪切体尺寸
    boolWidth = bData.x_total + mData.piller_diameter
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH

    # 裁剪体定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolDeepth/2
    else:
        offset = -boolDeepth/2
    boolX = 0
    boolY = offset + crossPoint.y # 碰撞点
    boolZ = buildingH/2
    
    boolObj = utils.addCube(
        name="平行抱厦-悬山-主建筑" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        # 跳过台基、柱网、装修
        if con.COLL_NAME_BASE in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name : continue
        if con.COLL_NAME_WALL in layer.name : continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    # 2、抱厦屋顶裁剪：宽度到悬山外侧
    # 裁剪体尺寸
    boolWidth = bData.x_total + 21*2*dk # 悬山出檐
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH

    # 裁剪体定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolDeepth/2
    else:
        offset = -boolDeepth/2
    boolX = 0
    boolY = offset + crossPoint.y # 碰撞点
    boolZ = buildingH/2
    
    boolObj = utils.addCube(
        name="平行抱厦-悬山-抱厦" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    for layer in fromBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in layer.name : continue
        # 跳过台基、柱网、装修
        if con.COLL_NAME_BASE in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name : continue
        if con.COLL_NAME_WALL in layer.name : continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='INTERSECT',
        )

    # 二、裁剪柱网 -------------------------------
    # 沿着主建筑的檐面额枋进行裁剪，以同时保证不破坏主建筑的额枋，同时不产生柱础的重叠
    # 同时，保留了主建筑保修，裁剪了抱厦可能存在的雀替等
    boolWidth= bData.x_total + 21*2*dk # 悬山出檐
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total+con.EFANG_LARGE_Y*dk+0.01)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2
    boolObj = utils.addCube(
        name="平行抱厦-悬山-柱网" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if (con.COLL_NAME_PILLER in layer.name
            # 抱厦的装修也按这个范围裁剪，包括雀替等
            or con.COLL_NAME_WALL in layer.name) :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='INTERSECT',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    
    # 三、裁剪台基 --------------------------------
    # 从柱做45度斜切
    boolWidth= (bData.x_total 
                + bData.platform_extend *2
                + con.GROUND_BORDER *2
                # + bData.platform_height*3 # 保留踏跺空间
                )
    boolDeepth = (bData.y_total
                  + bData.platform_extend
                  + con.GROUND_BORDER)
    boolHeight = bData.platform_height
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2
    boolObj = utils.addCube(
        name="平行抱厦-悬山-台基" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )

    # 做45度折角
    # 折角宽度取台基下出
    offset= bData.platform_extend + con.GROUND_BORDER
    # 选择内侧被裁剪的边线做折角
    if fromBuilding.location.y > toBuilding.location.y:
        bevelEdges = [1,9]
    else:
        bevelEdges = [3,6]
    utils.edgeBevel(bevelObj=boolObj,
                    bevelEdges=bevelEdges,
                    bevelOffset=offset)
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_BASE in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_BASE in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='INTERSECT',
            )

    # 四、裁剪抱厦的博缝板
    # 以主建筑的瓦面为基础进行拉伸
    tileGrid = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if not tileGrid: raise Exception('无法找到主建筑瓦面')
    tileGrid_copy = utils.copySimplyObject(
        tileGrid,singleUser=True)
    # 挂接到合并对象下
    tileGrid_copy.parent = toBuildingJoined
    # 重新映射坐标系
    tileGrid_copy.location = (toBuildingJoined.matrix_world.inverted()
                              @ tileGrid.parent.matrix_world 
                              @ tileGrid.location)
    utils.showObj(tileGrid_copy)
    utils.focusObj(tileGrid_copy)
    # 镜像
    utils.addModifierMirror(
        object=tileGrid_copy,
        mirrorObj=toBuildingJoined,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True
    )
    utils.applyAllModifer(tileGrid_copy)

    # 推出裁剪体
    boolDeepth = bData.y_total
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(tileGrid_copy.data)
    # 选中所有面
    for face in bm.faces: face.select = True
    # 沿Z方向挤出
    extrude_result = bmesh.ops.extrude_face_region(
        bm, geom=bm.faces)
    extruded_verts = [v for v in extrude_result['geom'] 
                      if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(
        bm,
        vec=Vector((0, 0, -boolDeepth)),  # Y轴方向移动
        verts=extruded_verts
    )
    # 沿Y方向缩放0
    # 以所有挤出面的平均中心为原点
    center = Vector((0, 0, 0))
    for v in extruded_verts:
        center += v.co
    center /= len(extruded_verts)
    for v in extruded_verts:
        v.co.z = center.z
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(tileGrid_copy.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )
    utils.hideObjFace(tileGrid_copy)
    utils.hideObj(tileGrid_copy)

    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_BOARD in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=tileGrid_copy,
                operation='DIFFERENCE',
            )
    
    if fromBuildingJoined:
        utils.focusObj(fromBuildingJoined)

    return {'FINISHED'}

# 建筑组合：平行抱厦-歇山
# fromBuilding为面阔较小的抱厦
def __unionParallelXieshan(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object):
    utils.outputMsg('平行抱厦-歇山')
    # 载入数据
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data
    dk = bData.DK

    # 1、确保抱厦和主建筑分层合并
    # 抱厦进行分层合并
    if fromBuildingJoined:
        # 强制解除合并
        __undoJoin(fromBuildingJoined)
    # 重新分层合并
    fromBuildingJoined = joinBuilding(fromBuilding,useLayer=True)
    # 主建筑分层合并
    # 已合并的话，检查是否分层
    if toBuildingJoined:
        # 合并根节点
        building,mData,oData = utils.getRoot(toBuildingJoined)
        # 如果没有分层，则重新分层
        if len(building.children) == 1:
            __undoJoin(building)
            toBuildingJoined = joinBuilding(toBuilding,useLayer=True)
        else:
            # 如果已经分层，则保留
            toBuildingJoined = building
    # 未合并的话，进行分层合并
    else:
        toBuildingJoined = joinBuilding(toBuilding,useLayer=True)

    # 一、裁剪屋顶 ------------------------
    # 包括：装修、斗栱、梁架、椽架
    # 不包括：台基、柱网、装修
    # 宽到抱厦正身出檐，45度折角
    # 瓦面碰撞点
    crossPoint = __getRoofCrossPoint(fromBuilding,toBuilding)
    if crossPoint == 'CANCELLED': return {'CANCELLED'}

    # 建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    # 出檐
    eave_extend = (con.YANCHUAN_EX*dk 
              + con.FLYRAFTER_EX*dk)
    # 斗栱出檐
    if bData.use_dg:
        eave_extend += bData.dg_extend*bData.dg_scale[0]
    # 安全保留（包括翘飞椽雀台、勾滴等）
    eave_extend += 20*dk

    # 剪切体尺寸
    boolWidth = bData.x_total + eave_extend*2
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH

    # 裁剪体定位
    if fromBuilding.location.y > toBuilding.location.y:
        offset = boolDeepth/2
    else:
        offset = -boolDeepth/2
    boolX = 0
    boolY = offset + crossPoint.y # 碰撞点
    boolZ = buildingH/2
    boolObj = utils.addCube(
        name="平行抱厦-歇山屋顶" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    # 做45度折角
    # 折角宽度取檐出
    offset= eave_extend
    # 选择内侧被裁剪的边线做折角
    if fromBuilding.location.y > toBuilding.location.y:
        bevelEdges = [1,9]
    else:
        bevelEdges = [3,6]
    utils.edgeBevel(bevelObj=boolObj,
                    bevelEdges=bevelEdges,
                    bevelOffset=offset)
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    for layer in toBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in layer.name : continue
        # 跳过台基、柱网、装修
        if con.COLL_NAME_BASE in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name : continue
        if con.COLL_NAME_WALL in layer.name : continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    # 添加bool modifier
    for layer in fromBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in layer.name : continue
        # 跳过台基、柱网、装修
        if con.COLL_NAME_BASE in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name : continue
        if con.COLL_NAME_WALL in layer.name : continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='INTERSECT',
        )

    # 二、裁剪柱网 -------------------------------
    # 沿着主建筑的檐面额枋进行裁剪，以同时保证不破坏主建筑的额枋，同时不产生柱础的重叠
    # 同时，保留了主建筑保修，裁剪了抱厦可能存在的雀替等
    boolWidth= bData.x_total + 21*2*dk # 歇山出檐
    boolDeepth = bData.y_total + eave_extend*2
    boolHeight = buildingH
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total+con.EFANG_LARGE_Y*dk+0.01)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2
    boolObj = utils.addCube(
        name="平行抱厦-歇山-柱网" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if (con.COLL_NAME_PILLER in layer.name
            # 抱厦的装修也按这个范围裁剪，包括雀替等
            or con.COLL_NAME_WALL in layer.name) :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='INTERSECT',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    
    # 三、裁剪台基 --------------------------------
    # 从柱做45度斜切
    boolWidth= (bData.x_total 
                + bData.platform_extend *2
                + con.GROUND_BORDER *2
                #+ bData.piller_diameter*2
                )
    boolDeepth = (bData.y_total
                  + bData.platform_extend
                  + con.GROUND_BORDER
                  + bData.platform_height*3 # 保留踏跺空间
                  )
    boolHeight = bData.platform_height
    # 定位点做在檐柱中线，没有按瓦面碰撞
    # 后出抱厦的定位
    boolY = (boolDeepth-bData.y_total)/2
    if fromBuilding.location.y < toBuilding.location.y:
        # 前出抱厦的定位
        boolY *= -1
    boolZ = boolHeight/2
    boolObj = utils.addCube(
        name="平行抱厦-悬山-台基" + con.BOOL_SUFFIX ,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )

    # 做45度折角
    # 折角宽度取台基下出
    offset= bData.platform_extend + con.GROUND_BORDER
    # 选择内侧被裁剪的边线做折角
    if fromBuilding.location.y > toBuilding.location.y:
        bevelEdges = [1,9]
    else:
        bevelEdges = [3,6]
    utils.edgeBevel(bevelObj=boolObj,
                    bevelEdges=bevelEdges,
                    bevelOffset=offset)
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_BASE in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_BASE in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='INTERSECT',
            )

    # 四、裁剪抱厦的博缝板
    # 以主建筑的瓦面为基础进行拉伸
    tileGrid = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if not tileGrid: raise Exception('无法找到主建筑瓦面')
    tileGrid_copy = utils.copySimplyObject(
        tileGrid,singleUser=True)
    # 挂接到合并对象下
    tileGrid_copy.parent = toBuildingJoined
    # 重新映射坐标系
    tileGrid_copy.location = (toBuildingJoined.matrix_world.inverted()
                              @ tileGrid.parent.matrix_world 
                              @ tileGrid.location)
    utils.showObj(tileGrid_copy)
    utils.focusObj(tileGrid_copy)
    # 镜像
    utils.addModifierMirror(
        object=tileGrid_copy,
        mirrorObj=toBuildingJoined,
        use_axis=(True,True,False),
        use_bisect=(True,True,False),
        use_merge=True
    )
    utils.applyAllModifer(tileGrid_copy)

    # 推出裁剪体
    boolDeepth = bData.y_total
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(tileGrid_copy.data)
    # 选中所有面
    for face in bm.faces: face.select = True
    # 沿Z方向挤出
    extrude_result = bmesh.ops.extrude_face_region(
        bm, geom=bm.faces)
    extruded_verts = [v for v in extrude_result['geom'] 
                      if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(
        bm,
        vec=Vector((0, 0, -boolDeepth)),  # Y轴方向移动
        verts=extruded_verts
    )
    # 沿Y方向缩放0
    # 以所有挤出面的平均中心为原点
    center = Vector((0, 0, 0))
    for v in extruded_verts:
        center += v.co
    center /= len(extruded_verts)
    for v in extruded_verts:
        v.co.z = center.z
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(tileGrid_copy.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )
    utils.hideObjFace(tileGrid_copy)
    utils.hideObj(tileGrid_copy)

    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_BOARD in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=tileGrid_copy,
                operation='DIFFERENCE',
            )

    if fromBuildingJoined:
        utils.focusObj(fromBuildingJoined)

    return {'FINISHED'}

# 建筑组合：丁字形抱厦
# fromBuilding为面阔较小的抱厦
def __unionCrossBaosha(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object,
                     dir='Y'):
    utils.outputMsg('丁字形抱厦')
    # 指定合并目录，以免碰撞体落在原建筑目录中
    coll:bpy.types.Collection = utils.setCollection(
                con.COLL_NAME_ROOT_JOINED,isRoot=True,colorTag=3)
    
    # 1、计算屋顶相交面 ----------------------------------
    # 抱厦瓦面
    fromRoof = utils.getAcaChild(
        fromBuilding,con.ACA_TYPE_TILE_GRID)
    if fromRoof:
        fromRoof_copy = utils.copySimplyObject(
            fromRoof,singleUser=True)
        utils.showObj(fromRoof_copy)
        # 镜像
        utils.addModifierMirror(
            object=fromRoof_copy,
            mirrorObj=fromBuilding,
            use_axis=(True,True,False),
            use_bisect=(True,True,False),
            use_merge=True
        )
        utils.applyAllModifer(fromRoof_copy)        

    # 主建筑瓦面
    if dir == 'Y':
        gridType = con.ACA_TYPE_TILE_GRID
    else:
        gridType = con.ACA_TYPE_TILE_GRID_LR
    toRoof = utils.getAcaChild(toBuilding,gridType)
    if toRoof:
        toRoof_copy = utils.copySimplyObject(
            toRoof,singleUser=True)
        utils.showObj(toRoof_copy)
        utils.focusObj(toRoof_copy)
        
        # 如果是盝顶，则将瓦面的顶部挤出高度，以确保与抱厦相交出闭合面
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.new()
        bm = bmesh.from_edit_mesh(toRoof_copy.data)
        bm.edges.ensure_lookup_table()
        # 查找几何中心
        center = Vector((0.0, 0.0, 0.0))
        for v in bm.verts:
            center += v.co
        center /= len(bm.verts)
        # 轮询各个边，查找靠盝顶围脊的顶边
        for edge in bm.edges:
            # 1、非边界边，跳过
            if len(edge.link_faces) != 1:
                continue
            # 边的两个端点
            v1 = edge.verts[0].co
            v2 = edge.verts[1].co
            # 边的斜率
            dir_vec = v2 - v1
            # 2、跳过零长度边（无效边）
            if dir_vec.length < 1e-6:
                continue
            # 归一化方向向量
            dir_vec.normalize()
            # 南北抱厦与X轴比较
            if dir == 'Y':
                # 与X轴做向量点积，正为同向，0为垂直，负为反向
                axisX = Vector((1,0,0))
                dir_alt = dir_vec.dot(axisX)
                # 3、跳过接近于垂直的线
                if dir_alt < 0.5:
                    continue
                # 4、跳过下缘
                if v1.y > center.y or v2.y > center.y:
                    continue
            # 东西抱厦与Y轴比较
            else:
                # 与Y轴做向量点积，正为同向，0为垂直，负为反向
                axisY = Vector((0,1,0))
                dir_alt = dir_vec.dot(axisY)
                # 3、跳过接近于垂直的线
                if dir_alt < 0.5:
                    continue
                # 4、跳过下缘
                if v1.x > center.x or v2.x > center.x:
                    continue
            # 选中南面平行于X轴的边线
            edge.select = True
        # 微调，以免碰撞围脊
        offset = 0.625*toBuilding.ACA_data.DK
        for v in bm.verts:
            if v.select == True:
                if dir == 'Y':
                    v.co.y += offset
                else:
                    v.co.x += offset
        # 向上挤出
        toRoofTopEdge = []
        for edge in bm.edges:
            if edge.select:
                toRoofTopEdge.append(edge)
        extrude_result = bmesh.ops.extrude_edge_only(
            bm, edges=toRoofTopEdge)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        geom = (extrude_result.get('geom', []) 
                or extrude_result.get('verts', []) 
                or [])
        extruded_verts = [ele for ele in geom 
            if isinstance(ele, bmesh.types.BMVert)]
        # 挤出：高度取抱厦进深
        extrude_height = fromBuilding.ACA_data.y_total/2
        bmesh.ops.translate(bm,
                verts=extruded_verts,
                vec=Vector((0, 0, extrude_height))
            )
        bmesh.update_edit_mesh(toRoof_copy.data ) 
        bm.free() 
        bpy.ops.object.mode_set( mode = 'OBJECT' )

        # 镜像
        utils.addModifierMirror(
            object=toRoof_copy,
            mirrorObj=toBuilding,
            use_axis=(True,True,False),
            use_bisect=(True,True,False),
            use_merge=True
        )
        utils.applyAllModifer(toRoof_copy)
    
    # 基于BVH的碰撞检测
    if fromRoof_copy and toRoof_copy: 
        intersections,curve = utils.mesh_mesh_intersection(
            fromRoof_copy, toRoof_copy,create_curve=True)
        if intersections == []:
            utils.popMessageBox(f"未找到屋顶相交范围：from={fromBuilding.name},to={toBuilding.name}")
            return {'CANCELLED'}
    else:
        # print(f"未找到屋顶相交范围：from={fromBuilding.name},to={toBuilding.name}")
        return {'CANCELLED'}
    
    # 2、拉伸相交面，成为剪切体 ----------------------------
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data
    dk = bData.DK
    # 拉伸高度，屋面高度+屋身高度+上保留+下保留
    topSpan = 40*dk # 向上预留的空间，考虑屋脊、脊兽等
    bottomSpan = 20*dk # 向下预留的空间，考虑勾滴等
    extrude_Z = bData.y_total/2 + topSpan + bottomSpan
    extrude_Z += bData.piller_height + bData.platform_height
    if bData.use_dg:
        extrude_Z += bData.dg_height
    # 拉伸出檐
    baoshaExtend = (bData.x_total - mData.y_total)/2 # 抱厦出头
    # 无需考虑出檐，瓦面碰撞交点已经在檐口
    baoshaExtend += bData.chong*con.YUANCHUAN_D*dk # 冲
    baoshaExtend += 20*dk # 保留宽度，考虑勾滴、角兽等
    extrude_eave = baoshaExtend

    # 可能存在多个相交面，逐一挤出
    for interface in intersections:
        # 选中
        utils.focusObj(interface)
        # 编辑
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.new()
        bm = bmesh.from_edit_mesh(interface.data)

        # 2.1、做平行地面的投影面
        # 以最高点挤压投影平面
        zmax = -999999
        for v in bm.verts:
            if v.co.z > zmax:
                zmax = v.co.z
        for v in bm.verts:
            v.co.z = zmax
            # 向上抬升，以包裹瓦面
            v.co.z += topSpan

        # 2.2、向外挤出，覆盖抱厦出檐
        bm.edges.ensure_lookup_table()
        # 取出最后一条边（檐口边），仅对该边做挤出并沿 Y 轴平移
        eaveEdge = bm.edges[0]  # 第一条线为檐口线
        # 挤出
        extrude_result = bmesh.ops.extrude_edge_only(
            bm, edges=[eaveEdge])
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        geom = (extrude_result.get('geom', []) 
                or extrude_result.get('verts', []) 
                or [])
        extruded_verts = [ele for ele in geom 
            if isinstance(ele, bmesh.types.BMVert)]
        if extruded_verts:
            # 根据几何中心，决定向+Y还是-Y挤出
            edge_center = Vector((0.0, 0.0, 0.0))
            for v in bm.verts:
                edge_center += v.co
            edge_center /= len(bm.verts)

            if dir=='Y':
                if edge_center.y <= extruded_verts[0].co.y:
                    trans_y = extrude_eave 
                else:
                    trans_y = -extrude_eave
                bmesh.ops.translate(bm,
                    verts=extruded_verts,
                    vec=Vector((0, trans_y, 0))
                )
                # 根据中心，决定向+X还是-X扩展
                for v in extruded_verts:
                    if v.co.y > edge_center.y:
                        if v.co.x > edge_center.x :
                            v.co.x += trans_y
                        else:
                            v.co.x -= trans_y
                    else:
                        if v.co.x > edge_center.x :
                            v.co.x -= trans_y
                        else:
                            v.co.x += trans_y
            else:
                if edge_center.x <= extruded_verts[0].co.x:
                    trans_x = extrude_eave 
                else:
                    trans_x = -extrude_eave
                bmesh.ops.translate(bm,
                    verts=extruded_verts,
                    vec=Vector((trans_x, 0, 0))
                )
                # 根据中心，决定向+X还是-X扩展
                for v in extruded_verts:
                    if v.co.x > edge_center.x:
                        if v.co.y > edge_center.y :
                            v.co.y += trans_x
                        else:
                            v.co.y -= trans_x
                    else:
                        if v.co.y > edge_center.y :
                            v.co.y -= trans_x
                        else:
                            v.co.y += trans_x
        
        # 2.2、挤压出高度
        # 选中所有面
        for face in bm.faces: face.select = True
        # 沿Z方向挤出
        extrude_result = bmesh.ops.extrude_face_region(
            bm, geom=bm.faces)
        extruded_verts = [v for v in extrude_result['geom'] 
                        if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(
            bm,
            vec=Vector((0, 0, -extrude_Z)),  # Y轴方向移动
            verts=extruded_verts
        )

        # 更新bmesh
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bmesh.update_edit_mesh(interface.data ) 
        bm.free() 
        bpy.ops.object.mode_set( mode = 'OBJECT' )
    
    # 3、抱厦和主建筑分层合并
    # 抱厦进行分层合并
    if fromBuildingJoined:
        # 强制解除合并
        __undoJoin(fromBuildingJoined)
    # 重新分层合并
    fromBuildingJoined = joinBuilding(fromBuilding,useLayer=True)
    # 主建筑分层合并
    # 已合并的话，检查是否分层
    if toBuildingJoined:
        # 合并根节点
        building,mData,oData = utils.getRoot(toBuildingJoined)
        # 如果没有分层，则重新分层
        if len(building.children) == 1:
            __undoJoin(building)
            toBuildingJoined = joinBuilding(toBuilding,useLayer=True)
        else:
            # 如果已经分层，则保留
            toBuildingJoined = building
    # 未合并的话，进行分层合并
    else:
        toBuildingJoined = joinBuilding(toBuilding,useLayer=True)

    # 4、合并为一个对象
    boolObj = utils.joinObjects(intersections,
                      newName='丁字抱厦' + con.BOOL_SUFFIX ,)
    # 设置origin在几何中心
    utils.focusObj(boolObj)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
    utils.updateScene()
    # 重新映射坐标系
    wm = boolObj.matrix_world.copy()
    boolObj.parent = fromBuildingJoined
    boolObj.matrix_world = wm
    # 隐藏
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)
    
    # 5、绑定boolean
    # 添加bool modifier
    for layer in toBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        # 跳过装修、梁架、柱网
        if con.COLL_NAME_WALL in layer.name : continue
        if con.COLL_NAME_BEAM in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name: continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    # 添加bool modifier
    for layer in fromBuildingJoined.children:
        # 跳过bool对象、柱网
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name: continue
        if con.COLL_NAME_WALL in layer.name : continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='INTERSECT',
        )

    # 二、裁剪柱网 -------------------------------
    # 1、丁字抱厦相交的开间裁剪
    # 沿着主建筑的檐面额枋进行裁剪，以同时保证不破坏主建筑的额枋，同时不产生柱础的重叠
    # 同时，保留了主建筑保修，裁剪了抱厦可能存在的雀替等
    # 建筑高度
    buildingH = bData.platform_height + bData.piller_height
    if bData.use_dg:
        buildingH += bData.dg_height * bData.dg_scale[0]
    # 屋顶举高，简单的按进深1:1计算
    buildingH += bData.y_total
    # 保险数
    buildingH += 20*dk

    if dir == 'Y':
        # 宽：包裹抱厦宽度，避免裁剪外部的柱础
        boolWidth= bData.y_total + bData.piller_diameter
        # 长：包裹主建筑檐面额枋
        boolDeepth = mData.y_total + con.EFANG_LARGE_Y*dk + 0.01
    else:
        # 长：包裹抱厦进深+柱径，即明间柱的外皮
        boolDeepth = bData.y_total + bData.piller_diameter
        # 宽：包裹主建筑檐面额枋
        boolWidth = mData.x_total + con.EFANG_LARGE_Y*dk + 0.01
    boolHeight = buildingH
    boolZ = boolHeight/2
    boolObj = utils.addCube(
        name="丁字抱厦-柱网" + con.BOOL_SUFFIX ,
        location=(0,0,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=toBuildingJoined,
    )

    # 2、无抱厦开间的柱网保护
    extrudeExt = bData.piller_diameter
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.new()
    bm = bmesh.from_edit_mesh(boolObj.data)
    bm.faces.ensure_lookup_table()
    # 2.1、挤出两侧面：0号和2号
    if dir == 'Y':
        extrude_faces = [0,2]
    else:
        extrude_faces = [1,3]
    for f in bm.faces:
        if f.index in extrude_faces:
            f.select = True
        else:
            f.select = False
    extrude_faces0 = [f for f in bm.faces if f.select]
    extrude_result = bmesh.ops.extrude_face_region(
        bm,geom=extrude_faces0,
    )
    extruded_faces1 = [g for g in extrude_result['geom'] 
                      if isinstance(g, bmesh.types.BMFace)]
    extruded_verts1 = [g for g in extrude_result['geom'] 
                      if isinstance(g, bmesh.types.BMVert)]
    # 删除原始被挤出的面（extrude_faces 是挤出前记录的原面列表）
    for f in extrude_faces0:
        try:
            # 有时原面已被替换或合并，remove 前先检查仍在 bm.faces
            if f in bm.faces:
                bm.faces.remove(f)
        except Exception:
            # 忽略删除失败，继续处理
            pass
    # 更新索引表以保证后续访问安全
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()

    # 2.2、放大挤出面（一柱径）
    # 以几何中心放大
    center = Vector()
    for v in extruded_verts1:
        center += v.co
    center /= len(extruded_verts1)
    for v in extruded_verts1:
        if v.co.x > center.x:
            v.co.x += extrudeExt
        else:
            v.co.x -= extrudeExt
        if v.co.y > center.y:
            v.co.y += extrudeExt
        else:
            v.co.y -= extrudeExt

    # 2.3、再次挤出
    # 向外挤出，以涵盖无抱厦开间的柱网不被裁剪
    if dir == 'Y':
        extrudeWidth = (mData.x_total - bData.y_total)/2
    else:
        extrudeWidth = (mData.y_total - bData.y_total)/2
    extrude_result = bmesh.ops.extrude_face_region(
        bm,
        geom=extruded_faces1,  # 要挤出的几何元素
        use_normal_flip=False  # 不翻转法线
    )
    extruded_faces2 = [g for g in extrude_result['geom'] 
                      if isinstance(g, bmesh.types.BMFace)]
    extruded_verts2 = [g for g in extrude_result['geom'] 
                      if isinstance(g, bmesh.types.BMVert)]
    # 删除原始被挤出的面（extrude_faces 是挤出前记录的原面列表）
    for f in extruded_faces1:
        try:
            # 有时原面已被替换或合并，remove 前先检查仍在 bm.faces
            if f in bm.faces:
                bm.faces.remove(f)
        except Exception:
            # 忽略删除失败，继续处理
            pass
    # 更新索引表以保证后续访问安全
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    for v in extruded_verts2:
        if dir == 'Y':
            if v.co.x > center.x:
                v.co.x += extrudeWidth
            else:
                v.co.x -= extrudeWidth
        else:
            if v.co.y > center.y:
                v.co.y += extrudeWidth
            else:
                v.co.y -= extrudeWidth
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bmesh.update_edit_mesh(boolObj.data ) 
    bm.free() 
    bpy.ops.object.mode_set( mode = 'OBJECT' )

    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    for layer in toBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in layer.name : continue
        if con.COLL_NAME_PILLER in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='INTERSECT',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    for layer in fromBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX in layer.name : continue
        if (con.COLL_NAME_PILLER in layer.name
            # 抱厦的装修也按这个范围裁剪，包括雀替等
            or con.COLL_NAME_WALL in layer.name) :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)

    # 回收临时屋面
    utils.delObject(fromRoof_copy)
    utils.delObject(toRoof_copy)
    utils.delOrphan()
    if fromBuildingJoined:
        utils.focusObj(fromBuildingJoined)

    return {'FINISHED'}

# 建筑组合：L相交
# 暂时只考虑2坡顶
def __unionCrossL(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object,
                     dir='Y'):
    # 指定合并目录，以免碰撞体落在原建筑目录中
    coll:bpy.types.Collection = utils.setCollection(
                con.COLL_NAME_ROOT_JOINED,isRoot=True,colorTag=3)
    bData:acaData = fromBuilding.ACA_data
    mData:acaData = toBuilding.ACA_data
    dk = bData.DK
    
    if bData.roof_style not in (con.ROOF_YINGSHAN,
                                con.ROOF_YINGSHAN_JUANPENG,
                                con.ROOF_XUANSHAN,
                                con.ROOF_XUANSHAN_JUANPENG,):
        utils.outputMsg('只支持2坡顶')
        return
    if mData.roof_style not in (con.ROOF_YINGSHAN,
                                con.ROOF_YINGSHAN_JUANPENG,
                                con.ROOF_XUANSHAN,
                                con.ROOF_XUANSHAN_JUANPENG,):
        utils.outputMsg('只支持2坡顶')
        return
    
    # 裁剪体高度
    buildingH = (bData.platform_height+bData.piller_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += 20*dk # 保险高度
    buildingEave = 30*dk 
    
    # 获取相交瓦面 ---------------------------------
    # A建筑瓦面
    fromRoof = utils.getAcaChild(
        fromBuilding,con.ACA_TYPE_TILE_GRID)
    if fromRoof:
        fromRoof_copy = utils.copySimplyObject(
            fromRoof,singleUser=True)
        utils.showObj(fromRoof_copy)
        # 镜像
        utils.addModifierMirror(
            object=fromRoof_copy,
            mirrorObj=fromBuilding,
            use_axis=(True,True,False),
            use_bisect=(True,True,False),
            use_merge=True
        )
        utils.applyAllModifer(fromRoof_copy)
    # B建筑瓦面
    toRoof = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if toRoof:
        toRoof_copy = utils.copySimplyObject(
            toRoof,singleUser=True)
        utils.showObj(toRoof_copy)
        # 镜像
        utils.addModifierMirror(
            object=toRoof_copy,
            mirrorObj=toBuilding,
            use_axis=(True,True,False),
            use_bisect=(True,True,False),
            use_merge=True
        )
        utils.applyAllModifer(toRoof_copy)

    # 基于BVH的碰撞检测 ---------------------------
    if fromRoof_copy and toRoof_copy: 
        intersections,curve = utils.mesh_mesh_intersection(
            fromRoof_copy, 
            toRoof_copy,
            create_curve=True,
            create_mesh=False)
        if curve is None:
            # print(f"未找到屋顶相交范围：from={fromBuilding.name},to={toBuilding.name}")
            # 回收对象
            utils.delObject(fromRoof_copy)
            utils.delObject(toRoof_copy)
            utils.delOrphan()
            return {'CANCELLED'}
    else:
        # print(f"未找到屋顶相交范围：from={fromBuilding.name},to={toBuilding.name}")
        return {'CANCELLED'}
    
    # 碰撞线二次调整 --------------------
    spline = curve.data.splines[0]
    pStart = spline.points[0].co
    pEnd = spline.points[-1].co
    # 以中点与toBuilding的位置关系，决定做哪个象限
    pMid = (pStart + pEnd)/2
    toCenter = toBuilding.location
    # 添加5个包裹点
    spline.points.add(5)
    pEndExt = spline.points[-5].co
    pCornerEnd = spline.points[-4].co
    pCorner = spline.points[-3].co
    pCornerStart = spline.points[-2].co
    pStartExt = spline.points[-1].co
    
    # 裁剪西南角
    isClockWise = True
    if pMid.x < toCenter.x and pMid.y < toCenter.y:
        pCorner.x = toBuilding.location.x + bData.y_total/2 + buildingEave
        pCorner.y = toBuilding.location.y + bData.x_total/2 + buildingEave
        # 逆时针包裹
        if pStart.x < pEnd.x:
            isClockWise = False
            pEndExt.x = pEnd.x + buildingEave
            pEndExt.y = pEnd.y - buildingEave
            pStartExt.x = pStart.x - buildingEave
            pStartExt.y = pStart.y + buildingEave  
        # 顺时针包裹
        else:
            pEndExt.x = pEnd.x - buildingEave
            pEndExt.y = pEnd.y + buildingEave
            pStartExt.x = pStart.x + buildingEave
            pStartExt.y = pStart.y - buildingEave  
    
    # 裁剪西北角
    if pMid.x < toCenter.x and pMid.y > toCenter.y:
        pCorner.x = toBuilding.location.x + bData.y_total/2 + buildingEave
        pCorner.y = toBuilding.location.y - bData.x_total/2 - buildingEave
        # 逆时针包裹
        if pStart.x < pEnd.x:
            isClockWise = False
            pEndExt.x = pEnd.x + buildingEave
            pEndExt.y = pEnd.y + buildingEave
            pStartExt.x = pStart.x - buildingEave
            pStartExt.y = pStart.y - buildingEave  
        # 顺时针包裹
        else:
            pEndExt.x = pEnd.x - buildingEave
            pEndExt.y = pEnd.y - buildingEave
            pStartExt.x = pStart.x + buildingEave
            pStartExt.y = pStart.y + buildingEave 

    # 裁剪东南角
    if pMid.x > toCenter.x and pMid.y < toCenter.y:
        pCorner.x = toBuilding.location.x - bData.y_total/2 - buildingEave
        pCorner.y = toBuilding.location.y + bData.x_total/2 + buildingEave
        # 逆时针包裹
        if pStart.x > pEnd.x:
            isClockWise = False
            pEndExt.x = pEnd.x - buildingEave
            pEndExt.y = pEnd.y - buildingEave
            pStartExt.x = pStart.x + buildingEave
            pStartExt.y = pStart.y + buildingEave 
        # 顺时针包裹
        else:
            pEndExt.x = pEnd.x + buildingEave
            pEndExt.y = pEnd.y + buildingEave
            pStartExt.x = pStart.x - buildingEave
            pStartExt.y = pStart.y - buildingEave 
    
    # 裁剪东北角
    if pMid.x > toCenter.x and pMid.y > toCenter.y:
        pCorner.x = toBuilding.location.x - bData.y_total/2 - buildingEave
        pCorner.y = toBuilding.location.y - bData.x_total/2 - buildingEave
        # 逆时针包裹
        if pStart.x > pEnd.x:
            isClockWise = False
            pEndExt.x = pEnd.x - buildingEave
            pEndExt.y = pEnd.y + buildingEave
            pStartExt.x = pStart.x + buildingEave
            pStartExt.y = pStart.y - buildingEave 
        # 顺时针包裹
        else:
            pEndExt.x = pEnd.x + buildingEave
            pEndExt.y = pEnd.y - buildingEave
            pStartExt.x = pStart.x - buildingEave
            pStartExt.y = pStart.y + buildingEave 

    if isClockWise:
        pCornerEnd.x = pEndExt.x
        pCornerEnd.y = pCorner.y

        pCornerStart.x = pCorner.x
        pCornerStart.y = pStartExt.y
    else:
        pCornerEnd.x = pCorner.x
        pCornerEnd.y = pEndExt.y

        pCornerStart.x = pStartExt.x
        pCornerStart.y = pCorner.y

    # 压缩成一个水平面
    for p in spline.points:
        p.co.z = 0

    # 生成几何面 --------------------------
    # 读取世界坐标的点（之前我们已用世界坐标填入）
    verts_world = [Vector(p.co[:3]) for p in spline.points]
    # 创建 bmesh，面位于世界坐标系
    bm = bmesh.new()
    bm_verts = []
    for v_co in verts_world:
        bm_verts.append(bm.verts.new((v_co.x, v_co.y, v_co.z)))
    bm.verts.ensure_lookup_table()
    # 尝试创建面（若非平面则 Blender 会接受为 NGon，但可能被三角化）
    try:
        face = bm.faces.new(tuple(bm_verts))
    except ValueError:
        # 如果顶点顺序或重复导致错误，先去重再尝试
        unique_pts = []
        for v in verts_world:
            if len(unique_pts) == 0 or (v - unique_pts[-1]).length > 0.01:
                unique_pts.append(v)
        if len(unique_pts) >= 3:
            bm.clear()
            bm_verts = [bm.verts.new((v.x, v.y, v.z)) for v in unique_pts]
            bm.faces.new(tuple(bm_verts))
        else:
            bm.free()
            bm = None

    # 生成几何体 -------------------------------
    # 挤出垂直高度
    # 选中所有面
    for face in bm.faces: face.select = True
    # 沿Z方向挤出
    extrude_result = bmesh.ops.extrude_face_region(
        bm, geom=bm.faces)
    extruded_verts = [v for v in extrude_result['geom'] 
                      if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(
        bm,
        vec=Vector((0, 0, buildingH)),  # Y轴方向移动
        verts=extruded_verts
    )

    if bm is not None:
        bm.normal_update()
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        # 写入 mesh 并创建对象
        intersectionData = bpy.data.meshes.new(
            '屋顶相交'+con.BOOL_SUFFIX )
        bm.to_mesh(intersectionData)
        bm.free()
        intersectionObj = bpy.data.objects.new(
            '屋顶相交'+con.BOOL_SUFFIX , intersectionData)
        bpy.context.collection.objects.link(intersectionObj)

    # 251202 添加一次细分，以免柱子和坐凳之间产生异常的破碎面
    utils.subdivideObject(intersectionObj,level=1)
    
    # 绑定在新廊间之下
    mw = intersectionObj.matrix_world.copy()
    intersectionObj.parent = toBuildingJoined
    intersectionObj.matrix_world = mw

    utils.hideObjFace(intersectionObj)
    utils.hideObj(intersectionObj)

    # 4、回收辅助对象
    utils.delObject(curve)
    utils.delObject(fromRoof_copy)
    utils.delObject(toRoof_copy)
    utils.delOrphan()

    # 应用裁剪 -------------------------------------------
    for obj in toBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            object=obj,
            boolObj=intersectionObj,
            operation='INTERSECT'
        )
    for obj in fromBuildingJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            object=obj,
            boolObj=intersectionObj,
            operation='DIFFERENCE'
        )

    return

# 判断屋顶相交点
def __getRoofCrossPoint(fromBuilding:bpy.types.Object,
                        toBuilding:bpy.types.Object,):
    # 主建筑正身坡线
    tileCurve = utils.getAcaChild(
        fromBuilding,con.ACA_TYPE_TILE_CURVE_FB)
    if tileCurve:
        tileCurve_copy = utils.copySimplyObject(
            tileCurve,singleUser=True)
        utils.showObj(tileCurve_copy)
    else:
        utils.popMessageBox("无法获取正身坡线")
        return {'CANCELLED'}
    # 副建筑瓦面
    tileGrid = utils.getAcaChild(
        toBuilding,con.ACA_TYPE_TILE_GRID)
    if tileGrid:
        tileGrid_copy = utils.copySimplyObject(
            tileGrid,singleUser=True)
        utils.showObj(tileGrid_copy)
        # 镜像
        utils.addModifierMirror(
            object=tileGrid_copy,
            mirrorObj=toBuilding,
            use_axis=(True,True,False),
            use_bisect=(True,True,False),
            use_merge=True
        )
        utils.applyAllModifer(tileGrid_copy)
    else:
        utils.popMessageBox("无法获取屋面")
        return {'CANCELLED'}

    # 3、计算交点
    intersections = utils.intersect_curve_mesh(
        curve_obj=tileCurve_copy,
        mesh_obj=tileGrid_copy
    )
    if intersections == []:
        tileCurve_copy.location.y = - tileCurve_copy.location.y
        tileCurve_copy.scale.y = -1
        intersections = utils.intersect_curve_mesh(
            curve_obj=tileCurve_copy,
            mesh_obj=tileGrid_copy
        )
        if intersections == []:
            # 回收辅助对象
            utils.delObject(tileCurve_copy)
            utils.delObject(tileGrid_copy)
            utils.delOrphan()
            utils.popMessageBox("建筑没有相交，未做任何裁剪")
            return {'CANCELLED'}
    # 转换到局部坐标
    crossPoint = fromBuilding.matrix_world.inverted() @ intersections[0]['location']

    # 4、回收辅助对象
    utils.delObject(tileCurve_copy)
    utils.delObject(tileGrid_copy)
    utils.delOrphan()
    return crossPoint

# 回廊延伸
def loggia_extend(contextObj:bpy.types.Object,
                  dir = 'E', # 方向：东E南N西W北S
                  ):
    # 1、准备 -----------------------
    LoggiaJoined = None

    # 验证是否选中建筑
    building,bData,oData = utils.getRoot(contextObj)
    if building is None:
        utils.popMessageBox("请选中建筑")
        return {'CANCELLED'}
    
    # 找到未合并的本体
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        Loggia = __getJoinedOriginal(building)
        LoggiaJoined = building
    else:
        Loggia = building
    bData:acaData = Loggia.ACA_data

    # 如果未合并，开始合并
    if LoggiaJoined is None:
        LoggiaJoined = joinBuilding(Loggia)

        if LoggiaJoined is None:
            utils.popMessageBox("未能合并建筑")
            return {'CANCELLED'}
    
    # 2、判断转角，并生成转角 ---------------------------
    if dir in ('NW','NE','SW','SE'):
        isCorner = True
    else:
        isCorner = False
    if bData.combo_type == con.COMBO_LOGGIA_CORNER:
        isBranch = True
    else:
        isBranch = False
    # 做L形转角
    if isCorner: 
        LoggiaCornerJoined = __add_loggia_corner(
            baseLoggia = LoggiaJoined,
            dir = dir,
        )
    # 做丁字或十字交叉
    if isBranch:
        LoggiaCornerJoined = __update_loggia_corner(
            baseLoggia = LoggiaJoined,
            dir = dir,
        )
    
    # 3、延伸方向的廊间生成 -----------------------
    LoggiaNewJoined = __add_loggia_extend(
        baseLoggia = LoggiaJoined,
        dir = dir,
    )

    # 4、转角屋顶裁剪 ---------------------------
    # 注意：要在新廊间转角关联前处理，以新廊间重复自我裁剪
    if isCorner or isBranch:
        __add_loggia_intersection(
            fromLoggia = LoggiaJoined,
            toLoggia = LoggiaNewJoined,
            cornerLoggia = LoggiaCornerJoined,
        )

    # 5、标识转角与廊间的关联，以便在做T形或X形交叉时找回参考廊间
    if isCorner or isBranch:
        # 转角ID
        LoggiaCorner = __getJoinedOriginal(LoggiaCornerJoined)
        cornerJData:acaData = LoggiaCornerJoined.ACA_data
        cornerData:acaData = LoggiaCorner.ACA_data
        # 新廊间ID
        childID = cornerData.combo_children.add()
        childID.id = LoggiaNewJoined.ACA_data.aca_id
        childID = cornerJData.combo_children.add()
        childID.id = LoggiaNewJoined.ACA_data.aca_id
        if dir in ('NW','NE','SW','SE'):
            # 老廊间关联转角
            childID = cornerData.combo_children.add()
            childID.id = LoggiaJoined.ACA_data.aca_id
            childID = cornerJData.combo_children.add()
            childID.id = LoggiaJoined.ACA_data.aca_id

    # 6、标识原廊间的相邻廊间，以便panel上禁用不合理的延伸方向
    # 未合并对象的标注
    if dir in ('E','W','N','S'):
        bData.loggia_sign += '/' + dir
    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False
    if isWE:
        if dir in ('NE','SE'):
            bData.loggia_sign += '/E' 
        if dir in ('NW','SW'):
            bData.loggia_sign += '/W' 
    else:
        if dir in ('NE','NW'):
            bData.loggia_sign += '/N' 
        if dir in ('SE','SW'):
            bData.loggia_sign += '/S' 
    # 已合并对象的标注
    jData:acaData = LoggiaJoined.ACA_data
    jData.loggia_sign = bData.loggia_sign
    for obj in LoggiaJoined.children:
        if con.BOOL_SUFFIX  in obj.name : continue
        oData:acaData = obj.ACA_data
        oData.loggia_sign = bData.loggia_sign

    # 7、转角闭合判断 ----------------------------- 
    isConnected = False
    # 尝试闭合廊间与廊间的碰撞
    # 可能是在一字延伸时触发
    # 也可能是经过转角时触发
    isConnected = __connect_loggia_loggia(
        LoggiaNewJoined,dir)

    # 尝试闭合转角处的碰撞
    # 可能时从转角延伸到廊间，
    # 也可能时一字延伸碰撞到廊间
    if not isConnected:
        # 如果廊间已经闭合过，则不再触发转角闭合，避免修改了原来的转角
        __connect_loggia_corner(LoggiaNewJoined,dir)

    # 尝试闭合开放的转角
    __connect_open_corner(LoggiaNewJoined,dir)

    # 8、聚焦在新loggia
    for obj in LoggiaNewJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.focusObj(obj)

    return {'FINISHED'}

# 生成回廊转角
def __add_loggia_corner(baseLoggia:bpy.types.Object,
                  dir):
    # 1、准备 ----------------------------------
    # 开启进度条
    global isFinished,progress
    isFinished = False
    progress = 0

    # 参考廊间
    LoggiaJoined = baseLoggia
    Loggia = __getJoinedOriginal(LoggiaJoined)
    bData:acaData = Loggia.ACA_data
    dk = bData.DK   

    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False

    # 2、原廊间的裁剪 ------------------------
    __cut_base_loggia(baseLoggia,dir)
    
    # 3、创建回廊转角对象 ---------------------
    LoggiaCorner = buildFloor.__addBuildingRoot('回廊转角')
    # 从回廊同步设置
    from . import buildCombo
    buildCombo.__syncData(
        fromBuilding=Loggia,
        toBuilding=LoggiaCorner,
    )
    # 重新设置柱网，并打标识
    cornerData:acaData = LoggiaCorner.ACA_data
    cornerData['combo_type'] = con.COMBO_LOGGIA_CORNER
    cornerData['x_rooms'] = 1
    cornerData['x_1'] = cornerData.y_1
    cornerData['y_rooms'] = 1
    # 标注相邻廊间
    if isWE: # 水平方向，颠倒东西向
        if dir == 'NE':sign = '/N/W'
        if dir == 'NW':sign = '/N/E'
        if dir == 'SE':sign = '/S/W'
        if dir == 'SW':sign = '/S/E'
    else: # 垂直方向，颠倒南北向
        if dir == 'NE':sign = '/S/E'
        if dir == 'NW':sign = '/S/W'
        if dir == 'SE':sign = '/N/E'
        if dir == 'SW':sign = '/N/W'
    cornerData['loggia_sign'] = sign

    # 4、位移 ----------------------------
    offset_corner = bData.x_total/2 + bData.y_total/2
    # 横版，在廊间左右做转角
    if isWE:
        if dir in ('NE','SE'):
            offset_v = Vector((offset_corner,0,0))
        else:
            offset_v = Vector((-offset_corner,0,0))
    # 竖版，在廊间上下做转角
    else:
        if dir in ('NW','NE'):
            offset_v = Vector((0,offset_corner,0))
        else:
            offset_v = Vector((0,-offset_corner,0))
    LoggiaCorner.location = Loggia.location + offset_v 

    # 5、生成转角 ----------------------------
    buildFloor.buildFloor(LoggiaCorner)
    # 合并转角
    LoggiaCornerJoined = joinBuilding(LoggiaCorner)

    # 6、屋顶控制 ----------------------------
    # 6.1、裁剪位置
    eaveExt = 30*dk
    offset = eaveExt/2
    buildingH = (bData.platform_height+bData.piller_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += 20*dk # 保险高度
    boolCenter = Vector((offset,offset,buildingH/2))
    # 做东南角SE
    if ((isWE and dir == 'NE') # 横版向东北
        or (not isWE and dir == 'SW') # 竖版向西南
        ): 
        boolCenter *= Vector((1,-1,1))
        use_axis=(True,False,False)
        use_bisect=(True,False,False)
        use_flip=(True,False,False)
    # 做东北角NE
    if ((isWE and dir == 'SE') # 横版向东南
        or (not isWE and dir == 'NW') # 竖版向西南
        ): 
        boolCenter *= Vector((1,1,1))
        use_axis=(False,True,False)
        use_bisect=(False,True,False)
        use_flip=(False,False,False)
    # 做西北角NW
    if ((isWE and dir == 'SW') # 横版向东南
        or (not isWE and dir == 'NE') # 竖版向西南
        ): 
        boolCenter *= Vector((-1,1,1))
        use_axis=(True,False,False)
        use_bisect=(True,False,False)
        use_flip=(False,False,False)
    # 做西南角SW
    if ((isWE and dir == 'NW') # 横版向东南
        or (not isWE and dir == 'SE') # 竖版向西南
        ): 
        boolCenter *= Vector((-1,-1,1))
        use_axis=(False,True,False)
        use_bisect=(False,True,False)
        use_flip=(False,True,False)

    # 6.2、45度镜像
    diagnalObj = utils.addEmpty(
        name = '45度镜像' + con.BOOL_SUFFIX,
        parent = LoggiaCornerJoined,
        rotation=(0,0,math.radians(45)),
        location=(0,0,0)
    )
    utils.hideObj(diagnalObj)
    for obj in LoggiaCornerJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierMirror(
            object= obj,
            mirrorObj=diagnalObj,
            use_axis=use_axis,
            use_bisect=use_bisect,
            use_flip=use_flip,
            use_merge=True,
            name='45-Axis'
        )

    # 6.3、转角裁剪 --------------------------------------
    dim = (cornerData.x_total + eaveExt,
            cornerData.y_total + eaveExt,
            buildingH
    )
    boolCube = utils.addCube(
        name="转角裁剪" + con.BOOL_SUFFIX,
        location=boolCenter,
        dimension=dim,
        parent=LoggiaCornerJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    for obj in LoggiaCornerJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='Corner-Cut',
            object=obj,
            boolObj=boolCube,
            operation='INTERSECT',
        )
        # 裁剪后柱体normal异常，做平滑
        utils.shaderSmooth(obj)
    
    # 关闭进度条
    isFinished = True

    return LoggiaCornerJoined

# 更新转角
# 用于在转角上做丁字或十字交叉
def __update_loggia_corner(baseLoggia:bpy.types.Object,
                  dir=''):
    LoggiaCornerJoined = baseLoggia
    bData:acaData = LoggiaCornerJoined.ACA_data
    dk = bData.DK
    buildingH = (bData.platform_height+bData.piller_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += 20*dk # 保险高度
    buildingEave = 20*dk # 悬山出际
    
    # 转角链接的廊间数量
    linkCount = len(bData.combo_children)
    
    # 做丁字交叉
    if linkCount == 2:
        # 找到转角屋
        cornerObj = None
        for obj in LoggiaCornerJoined.children:
            if con.BOOL_SUFFIX not in obj.name : 
                cornerObj = obj
                break
        if cornerObj is None:
            raise Exception("无法找到转角对象")
    
        # 已有的2个廊间，加上将要做的第3的廊间，推断丁字方向
        cornerLinked = bData.loggia_sign + '/' + dir
        # 丁字方向，丁头顶不出头的方向
        tdir = ''
        if 'N' not in cornerLinked:
            tdir = 'N'
            tdim = Vector((0,1,0))
            tloc = Vector((0,1,0))
        elif 'S' not in cornerLinked:
            tdir = 'S'
            tdim = Vector((0,1,0))
            tloc = Vector((0,-1,0))
        elif 'W' not in cornerLinked:
            tdir = 'W'
            tdim = Vector((1,0,0))
            tloc = Vector((-1,0,0))
        elif 'E' not in cornerLinked:
            tdir = 'E'
            tdim = Vector((1,0,0))
            tloc = Vector((1,0,0))

        # 原廊间的调整 -------------------------------
        # 禁用45度镜像，以便后续如果做十字交叉时恢复
        mod = cornerObj.modifiers.get('45-Axis')
        mod.show_viewport = False
        mod.show_render = False
        # 与丁字方向对应
        if tdir in ('W','E'):
            cornerObj.rotation_euler.z = math.radians(90)

        # 原廊间的裁剪 ------------------------------------
        # 默认出檐尺寸
        eaveExt = 30*dk
        # 不出檐尺寸
        # 根据丁字头的出檐调整
        dimAdj = Vector((eaveExt,
                         eaveExt,
                         0)) * tdim
        dim = Vector((bData.x_total,
                      bData.x_total,
                      buildingH)) + dimAdj
        # 根据丁字头的出檐调整
        locAdj = Vector((eaveExt/2,
                         eaveExt/2,
                         0)) * tloc
        loc = Vector((0,
                      0,
                      buildingH/2)) + locAdj
        mod = cornerObj.modifiers.get('Corner-Cut')
        cornerBoolCube:bpy.types.Object = mod.object
        cornerBoolCube.dimensions = dim
        cornerBoolCube.location = loc

        # 复制转角屋并裁剪 ----------------------------------
        cornerCopy = utils.copySimplyObject(cornerObj)
        # 标注名称，便于在十字交叉时删除
        cornerCopy.name = '丁字转角'
        # 旋转并交叉
        cornerCopy.rotation_euler.z += math.radians(90)
        # 在丁字方向进行裁剪        
        size = (bData.y_total + buildingEave) * 1.414
        center = size * 1.414/2
        dim = (size,size,buildingH)
        locAdj = Vector((-center,-center,0)) * tloc
        loc = Vector((0,0,buildingH/2)) + locAdj
        # 添加裁剪
        boolCube = utils.addCube(
            name='丁字裁剪' + con.BOOL_SUFFIX,
            location=loc,
            dimension=dim,
            parent=LoggiaCornerJoined,
            rotation=(0,0,math.radians(45))
        )
        utils.hideObjFace(boolCube)
        utils.hideObj(boolCube)
        utils.addModifierBoolean(
            name='T-Cut',
            object=cornerCopy,
            boolObj=boolCube,
            operation='INTERSECT',
        )
        utils.addModifierBoolean(
            name='T-Cut',
            object=cornerObj,
            boolObj=boolCube,
            operation='DIFFERENCE',
        )

    # 做十字交叉
    if linkCount ==3:
        # 找到转角屋，并删除丁字复制的转角屋
        cornerObj = None
        for obj in LoggiaCornerJoined.children:
            if con.BOOL_SUFFIX  in obj.name : 
                if '丁字裁剪' in obj.name:
                    # 删除丁字裁剪
                    utils.delObject(obj)
                    continue
                else:
                    # 保留其他bool对象
                    continue
            if '丁字转角' in obj.name:
                # 删除丁字转角
                utils.delObject(obj)
            else:
                cornerObj = obj
        if cornerObj is None:
            raise Exception("无法找到转角对象")
                
        # 删除丁字裁剪
        mod = cornerObj.modifiers.get('T-Cut')
        cornerObj.modifiers.remove(mod)

        # 恢复旋转（不同的旋转，45度镜像的效果不同）
        cornerObj.rotation_euler.z = 0

        # 调整转角裁剪
        dim = Vector((bData.x_total,bData.x_total,buildingH))
        loc = Vector((0,0,buildingH/2))
        mod = cornerObj.modifiers.get('Corner-Cut')
        cornerBoolCube:bpy.types.Object = mod.object
        cornerBoolCube.dimensions = dim
        cornerBoolCube.location = loc

        # 重新启用45度对称
        mod:bpy.types.MirrorModifier = \
            cornerObj.modifiers.get('45-Axis')
        mod.show_viewport = True
        mod.show_render = True
        mod.use_axis = (True,True,False)
        mod.use_bisect_axis = (True,True,False)
        mod.use_bisect_flip_axis = (True,False,False)

    return LoggiaCornerJoined

# 向指定方向延伸一个廊间
def __add_loggia_extend(baseLoggia:bpy.types.Object,
                        dir,
                        ):
    # 1、准备 -----------------------------
    oData:acaData = baseLoggia.ACA_data
    LoggiaJoined = baseLoggia
    Loggia = __getJoinedOriginal(LoggiaJoined)
    bData:acaData = Loggia.ACA_data

    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False
    # 是否为转角
    if dir in ('NW','NE','SW','SE'):
        isCorner = True
    else:
        isCorner = False
    # 是否做T字或X字分支？
    isBranch = False
    if oData.combo_type == con.COMBO_LOGGIA_CORNER:
        isBranch = True
    # 如果在转角上做分支(T形或X形)，则反查原始廊间
    if isBranch:
        LoggiaCorner = Loggia
        cornerData:acaData = LoggiaCorner.ACA_data
        Loggia = utils.getObjByID(cornerData.combo_children[0].id)
        bData:acaData = Loggia.ACA_data

    # 2、原廊间的裁剪 ----------------------------------
    # 仅一字延伸需要裁剪原廊间
    # L转角在生成转角时已经裁剪过一次，不要重复裁剪
    # 另外，如果是从转角做T字或X字延伸，也不需要对转角进行裁剪
    if (not isCorner and not isBranch):
        __cut_base_loggia(baseLoggia,dir)

    # 3、向延伸方向复制 --------------------------------
    LoggiaColl = Loggia.users_collection[0]
    LoggiaNewColl = utils.copyCollection(
        LoggiaColl.name,LoggiaColl.name)
    LoggiaNew = LoggiaNewColl.objects[0]
    mData:acaData = LoggiaNew.ACA_data
    mData['aca_id'] = utils.generateID()
    # 标识相邻的回廊
    if dir == 'E':
        mData.loggia_sign = '/W'
    if dir == 'W':
        mData.loggia_sign = '/E'
    if dir == 'N':
        mData.loggia_sign = '/S'
    if dir == 'S':
        mData.loggia_sign = '/N'
    if isWE:
        if dir in ('NE','NW'):
            mData.loggia_sign = '/S'
        if dir in ('SE','SW'):
            mData.loggia_sign = '/N'
    else:
        if dir in ('NE','SE'):
            mData.loggia_sign = '/W'
        if dir in ('SW','NW'):
            mData.loggia_sign = '/E'
    
    # 4、如果转角则进行旋转
    if dir in ('NE','NW','SW','SE'):
        # 原廊间横版，转角后为竖版
        if isWE:
            LoggiaNew.rotation_euler.z = math.radians(90)
        # 原廊间竖版，转角后为横板
        else:
            LoggiaNew.rotation_euler.z = 0
    # 如果为分支，强制参考廊间于延伸方向一致
    if isBranch:
        if dir in ('W','E'):
            LoggiaNew.rotation_euler.z = 0
        else:
            LoggiaNew.rotation_euler.z = math.radians(90)

    # 5、位移 ----------------------------------------
    # 如果为分支，先将参考廊间对齐转角
    if isBranch:
        LoggiaNew.location = baseLoggia.location 
        offset = bData.x_total/2 - bData.y_total/2
        if dir == 'E': # 东
            LoggiaNew.location.x -= offset
        elif dir == 'W': # 西
            LoggiaNew.location.x += offset
        elif dir == 'N': # 北
            LoggiaNew.location.y -= offset
        elif dir == 'S': # 南
            LoggiaNew.location.y += offset
    # 一字延伸
    if dir == 'E': # 东
        LoggiaNew.location.x += bData.x_total
    elif dir == 'W': # 西
        LoggiaNew.location.x -= bData.x_total
    elif dir == 'N': # 北
        LoggiaNew.location.y += bData.x_total
    elif dir == 'S': # 南
        LoggiaNew.location.y -= bData.x_total
    # L转角
    offset = bData.x_total/2 + bData.y_total/2
    offset_v = Vector((offset,offset,0))
    if dir == 'NE':
        LoggiaNew.location += offset_v * Vector((1,1,1))
    if dir == 'NW':
        LoggiaNew.location += offset_v * Vector((-1,1,1))
    if dir == 'SE':
        LoggiaNew.location += offset_v * Vector((1,-1,1))
    if dir == 'SW':
        LoggiaNew.location += offset_v * Vector((-1,-1,1))

    # 6、合并 ------------------------------------
    LoggiaNewJoined = joinBuilding(LoggiaNew)

    # 7、裁剪 ------------------------------------
    dk = bData.DK
    buildingH = (bData.platform_height+bData.piller_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += 20*dk # 保险高度
    buildingEave = 20*dk # 悬山出际

    # 裁剪
    buildingDeepth = bData.y_total + 60*dk # 出檐
    # 定位
    offset = buildingEave/2
    # 根据新延伸的回廊的横竖，判断裁剪偏移
    if dir in ('N','S','W','E'):
        # 一字延伸不改变方向
        isWENew = isWE
    else:
        # 转角改变了方向
        isWENew = not isWE
    # 如果为分支，已经旋转了参考廊间，之间按延伸方向判断即可
    if isBranch:
        if dir in ('W','E'):
            isWENew = True
        else:
            isWENew = False
    if isWENew:
        # 水平建筑，旋转为0，E为+x
        if 'E' in dir:
            boolX = offset
        else:
            boolX = -offset
    else:
        # 垂直建筑，旋转为90，N为+x
        if 'N' in dir:
            boolX = offset
        else:
            boolX = -offset
    boolCube = utils.addCube(
        name="出檐A裁剪" + con.BOOL_SUFFIX,
        location=Vector((boolX,0,buildingH/2)),
        dimension=(bData.x_total+buildingEave,
                   buildingDeepth,
                   buildingH),
        parent=LoggiaNewJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    for obj in LoggiaNewJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='EaveA-Cut',
            object= obj,
            boolObj=boolCube,
            operation='INTERSECT'
        )
        # 裁剪后柱体normal异常，做平滑
        utils.shaderSmooth(obj)
    return LoggiaNewJoined

# 转角处相邻廊间的屋顶裁剪
def __add_loggia_intersection(fromLoggia:bpy.types.Object,
                              toLoggia:bpy.types.Object,
                              cornerLoggia:bpy.types.Object,):
    LoggiaJoined = fromLoggia
    Loggia = __getJoinedOriginal(LoggiaJoined)
    LoggiaNewJoined = toLoggia
    LoggiaNew = __getJoinedOriginal(LoggiaNewJoined)
    LoggiaCornerJoined = cornerLoggia
    LoggiaCorner = __getJoinedOriginal(LoggiaCornerJoined)

    bData:acaData = Loggia.ACA_data
    # L转角的两个廊间裁剪
    if bData.combo_type == con.COMBO_LOGGIA:
        __unionCrossL(
            fromBuilding= Loggia,
            toBuilding= LoggiaNew,
            fromBuildingJoined= LoggiaJoined,
            toBuildingJoined= LoggiaNewJoined,
        )
    # T转角裁剪
    if bData.combo_type == con.COMBO_LOGGIA_CORNER:
        cornerData:acaData = LoggiaCorner.ACA_data
        linkLoggiaList = cornerData.combo_children
        # 与转角每个相连廊间做裁剪
        for linkLoggia in linkLoggiaList:
            Loggia = utils.getObjByID(linkLoggia.id)
            LoggiaJoined = utils.getObjByID(
                linkLoggia.id,
                aca_type=con.ACA_TYPE_BUILDING_JOINED)
            __unionCrossL(
                fromBuilding= Loggia,
                toBuilding= LoggiaNew,
                fromBuildingJoined= LoggiaJoined,
                toBuildingJoined= LoggiaNewJoined,
            )

    return 

# 原廊间的裁剪
def __cut_base_loggia(baseLoggia:bpy.types.Object,
                      dir):
    LoggiaJoined = baseLoggia
    Loggia = __getJoinedOriginal(LoggiaJoined)
    bData:acaData = Loggia.ACA_data
    dk = bData.DK
    buildingH = (bData.platform_height+bData.piller_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += 20*dk # 保险高度
    buildingEave = 20*dk # 悬山出际

    # 原始廊间是横版，还是竖版？
    zRot = Loggia.rotation_euler.z
    if (abs(zRot - math.radians(0)) < 0.001
        or abs(zRot - math.radians(180)) < 0.001):
        isWE = True
    else:
        isWE = False

    # 原廊间可能已经做了一侧的转角裁剪，这里继续做另一侧的转角裁剪
    buildingDeepth = bData.y_total + 60*dk # 出檐
    # 定位
    offset = buildingEave/2
    if isWE:
        if 'E' in dir:
            boolX = -offset
        else:
            boolX = offset
    else:
        if 'S' in dir:
            boolX = offset
        else:
            boolX = -offset
    boolCube = utils.addCube(
        name="出檐B裁剪" + con.BOOL_SUFFIX,
        location=Vector((boolX,0,buildingH/2)),
        dimension=(bData.x_total+buildingEave,
                buildingDeepth,
                buildingH),
        parent=LoggiaJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    for obj in LoggiaJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            name='EaveB-Cut',
            object= obj,
            boolObj=boolCube,
            operation='INTERSECT'
        )
        # 裁剪后柱体normal异常，做平滑
        utils.shaderSmooth(obj)
    return

# 转角闭合判断，做转角时连接廊间和廊间
def __connect_loggia_loggia(LoggiaNewJoined:bpy.types.Object,dir):
    bData:acaData = LoggiaNewJoined.ACA_data

    # 一字廊间撞转角
    if dir == 'N': dir2 = 'S'
    if dir == 'S': dir2 = 'N'
    if dir == 'W': dir2 = 'E'
    if dir == 'E': dir2 = 'W'
    # L廊间撞转角
    if LoggiaNewJoined.rotation_euler.z == 0:
        if dir in ('NW','SW'): 
            dir = 'W'
            dir2 = 'E'
        if dir in ('NE','SE'): 
            dir = 'E'
            dir2 = 'W'
    else:
        if dir in ('NW','NE'): 
            dir = 'N'
            dir2 = 'S'
        if dir in ('SW','SE'): 
            dir = 'S'
            dir2 = 'N'

    # 找到合并目录
    JoinedColl:bpy.types.Collection = \
        bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
    connectObj = None
    # 遍历根目录下的每个建筑
    for joinedObj in JoinedColl.objects:
        # 跳过新建的廊间
        if joinedObj == LoggiaNewJoined: continue

        # 仅遍历合并的廊间
        if joinedObj.ACA_data.combo_type != con.COMBO_LOGGIA:
            continue

        # 只取3位小数，否则无法比较
        joinedLoc = utils.round_vector(joinedObj.location)
        newLoggiaLoc = utils.round_vector(LoggiaNewJoined.location)
        distance = utils.getVectorDistance(joinedLoc,newLoggiaLoc)
        roomdis = bData.x_total
        # 判断新廊间与现有廊间是否接近（面阔宽度）
        if distance - roomdis < 0.001:
            # 判断该廊间是否为已连接的相邻廊间
            if dir == 'W':
                # 想左延伸时，相连廊间在右侧
                if joinedLoc.x > newLoggiaLoc.x and joinedLoc.y == newLoggiaLoc.y:
                    continue
            if dir == 'E':
                # 想右延伸时，相连廊间在左侧
                if joinedLoc.x < newLoggiaLoc.x and joinedLoc.y == newLoggiaLoc.y:
                    continue
            if dir == 'N':
                # 想上延伸时，相连廊间在下侧
                if joinedLoc.y < newLoggiaLoc.y and joinedLoc.x == newLoggiaLoc.x:
                    continue
            if dir == 'S':
                # 想下延伸时，相连廊间在上侧
                if joinedLoc.y > newLoggiaLoc.y and joinedLoc.x == newLoggiaLoc.x:
                    continue
            connectObj = joinedObj
            break
    if connectObj is None: return
    # print("找到待闭合廊间：" + connectObj.name)

    # 廊间接头处裁剪
    __cut_base_loggia(LoggiaNewJoined,dir)
    __cut_base_loggia(connectObj,dir2)
    
    # 新廊间继承重叠廊间的标识
    connected_sign = connectObj.ACA_data.loggia_sign
    new_sign =  LoggiaNewJoined.ACA_data.loggia_sign

    LoggiaNewJoined.ACA_data['loggia_sign'] += connected_sign
    newLoggia = __getJoinedOriginal(LoggiaNewJoined)
    newLoggia.ACA_data['loggia_sign'] += connected_sign

    connectObj.ACA_data['loggia_sign'] += new_sign
    connectOrg = __getJoinedOriginal(connectObj)
    connectOrg.ACA_data['loggia_sign'] += new_sign

    # print("廊间与廊间的闭合")
    return True

# 延伸时，尝试连接廊间和转角
def __connect_loggia_corner(LoggiaNewJoined:bpy.types.Object,
                            dir):
    bData:acaData = LoggiaNewJoined.ACA_data
    
    # 找到合并目录
    JoinedColl:bpy.types.Collection = \
        bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
    LoggiaCornerJoined = None
    # 遍历根目录下的每个建筑
    for joinedObj in JoinedColl.objects:
        # 跳过新建的廊间
        if joinedObj == LoggiaNewJoined: continue

        # 仅遍历合并的转角
        if joinedObj.ACA_data.combo_type != con.COMBO_LOGGIA_CORNER:
            continue

        # 只取3位小数，否则无法比较
        joinedLoc = utils.round_vector(joinedObj.location)
        newLoggiaLoc = utils.round_vector(LoggiaNewJoined.location)
        # 判断新廊间与转角是否接近（面阔/2+进深/2）
        distance = utils.getVectorDistance(joinedLoc,newLoggiaLoc)
        roomdis = bData.x_total/2 + bData.y_total/2
        if abs(distance - roomdis) < 0.001:
            LoggiaCornerJoined = joinedObj
            break
    if LoggiaCornerJoined is None: return

    # 如果廊间和转角已经连接，则无需后续处理
    cornerData:acaData = LoggiaCornerJoined.ACA_data
    for linkLoggia in cornerData.combo_children:
        if linkLoggia.id == bData.aca_id:
            return None

    # 转角丁字或十字屋顶更新
    # 一字廊间撞转角
    if dir == 'N': dir2 = 'S'
    if dir == 'S': dir2 = 'N'
    if dir == 'W': dir2 = 'E'
    if dir == 'E': dir2 = 'W'
    # L廊间撞转角
    if LoggiaCornerJoined.rotation_euler.z == 0:
        if dir in ('NW','SW'): dir2 = 'W'
        if dir in ('NE','SE'): dir2 = 'E'
    else:
        if dir in ('NW','NE'): dir2 = 'N'
        if dir in ('SW','SE'): dir2 = 'S'
    LoggiaCornerJoined = __update_loggia_corner(
        baseLoggia = LoggiaCornerJoined,
        dir = dir2
    )

    # 新廊间的更新
    __cut_base_loggia(LoggiaNewJoined,dir)

    # 新廊间屋顶碰撞
    __add_loggia_intersection(
            fromLoggia = LoggiaCornerJoined,
            toLoggia = LoggiaNewJoined,
            cornerLoggia = LoggiaCornerJoined,
        )
    
    # 追加转角的相邻标识
    LoggiaCorner = __getJoinedOriginal(LoggiaCornerJoined)
    LoggiaCorner.ACA_data['loggia_sign'] += '/' + dir2
    LoggiaNew = __getJoinedOriginal(LoggiaNewJoined)
    LoggiaNew.ACA_data['loggia_sign'] += '/' + dir

    # 标识转角与廊间的关联，以便在做T形或X形交叉时找回参考廊间
    cornerJData:acaData = LoggiaCornerJoined.ACA_data
    cornerData:acaData = LoggiaCorner.ACA_data
    # 新廊间ID
    childID = cornerData.combo_children.add()
    childID.id = LoggiaNewJoined.ACA_data.aca_id
    childID = cornerJData.combo_children.add()
    childID.id = LoggiaNewJoined.ACA_data.aca_id

    # print("廊间与转角的闭合")
    return LoggiaCornerJoined

# 尝试连接开放的转角
def __connect_open_corner(LoggiaNewJoined:bpy.types.Object,
                            dir):
    bData:acaData = LoggiaNewJoined.ACA_data
    
    # 找到合并目录
    JoinedColl:bpy.types.Collection = \
        bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
    LoggiaOpenCorner = None
    # 遍历根目录下的每个建筑
    for joinedObj in JoinedColl.objects:
        # 跳过新建的廊间
        if joinedObj == LoggiaNewJoined: continue
        # 仅遍历合并的廊间
        if joinedObj.ACA_data.combo_type != con.COMBO_LOGGIA:
            continue
        # 只取3位小数，否则无法比较
        joinedLoc = utils.round_vector(joinedObj.location)
        newLoggiaLoc = utils.round_vector(LoggiaNewJoined.location)

        # 判断新廊间与转角是否接近（面阔/2+进深/2）
        distance = utils.getVectorDistance(joinedLoc,newLoggiaLoc)
        roomdis = (bData.x_total/2 + bData.y_total/2)*1.414
        if abs(distance - roomdis) < 0.001:
            # 再进一步判断相邻廊间之间是否已经存在转角
            hasCorner = False
            for cornerObj in JoinedColl.objects:
                if cornerObj.ACA_data.combo_type != con.COMBO_LOGGIA_CORNER:
                    continue # 只检查转角，其他跳过
                if (cornerObj.location.x == joinedObj.location.x
                    and cornerObj.location.y == LoggiaNewJoined.location.y):
                    # 一侧有转角，跳过
                    hasCorner = True
                    break
                if (cornerObj.location.y == joinedObj.location.y
                    and cornerObj.location.x == LoggiaNewJoined.location.x):
                    # 一侧有转角，跳过
                    hasCorner = True
                    break
            
            # 如果未找到相连的转角，找到需闭合廊间
            if not hasCorner:
                LoggiaOpenCorner = joinedObj
                break # 命中退出循环

    if LoggiaOpenCorner is None: return
    # print("找到待闭合转角，廊间名称为：" + LoggiaOpenCorner.name)

    dirNext = None
    if joinedLoc.x > newLoggiaLoc.x and joinedLoc.y > newLoggiaLoc.y:
        dirNext = 'NE'
    if joinedLoc.x > newLoggiaLoc.x and joinedLoc.y < newLoggiaLoc.y:
        dirNext = 'SE'
    if joinedLoc.x < newLoggiaLoc.x and joinedLoc.y < newLoggiaLoc.y:
        dirNext = 'SW'
    if joinedLoc.x < newLoggiaLoc.x and joinedLoc.y > newLoggiaLoc.y:
        dirNext = 'NW'

    # 做L形转角
    LoggiaCornerJoined = __add_loggia_corner(
        baseLoggia = LoggiaNewJoined,
        dir = dirNext,
    )

    # 闭合廊间的裁剪 ------------------------
    # 横版
    if LoggiaOpenCorner.rotation_euler.z == 0:
        if dirNext in ('NE','SE'):
            dirCut = 'W'
        if dirNext in ('NW','SW'):
            dirCut = 'E'
    else:
        if dirNext in ('NE','NW'):
            dirCut = 'S'
        if dirNext in ('SW','SE'):
            dirCut = 'N'
    __cut_base_loggia(LoggiaOpenCorner,dirCut)

    # 转角屋顶裁剪 ---------------------------
    __add_loggia_intersection(
            fromLoggia = LoggiaNewJoined,
            toLoggia = LoggiaOpenCorner,
            cornerLoggia = LoggiaCornerJoined,
        )
    
    # 相邻廊间的标注
    if LoggiaOpenCorner.rotation_euler.z == 0:
        if dirNext == 'NE':
            signA = 'N'
            signB = 'W'
        if dirNext == 'NW':
            signA = 'N'
            signB = 'E'
        if dirNext == 'SW':
            signA = 'S'
            signB = 'E'
        if dirNext == 'SE':
            signA = 'S'
            signB = 'W'
    else:
        if dirNext == 'NE':
            signA = 'E'
            signB = 'S'
        if dirNext == 'NW':
            signA = 'W'
            signB = 'S'
        if dirNext == 'SW':
            signA = 'W'
            signB = 'N'
        if dirNext == 'SE':
            signA = 'E'
            signB = 'N'
    LoggiaNew = __getJoinedOriginal(LoggiaNewJoined)
    LoggiaNew.ACA_data['loggia_sign'] += '/' + signA
    LoggiaOpen = __getJoinedOriginal(LoggiaOpenCorner)
    LoggiaOpen.ACA_data['loggia_sign'] += '/' + signB

    return