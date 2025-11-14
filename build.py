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
            'ACA古建.合并',isRoot=True,colorTag=3)
    
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
                'ACA古建.合并',isRoot=True,colorTag=3)
    
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
            utils.popMessageBox(f"未找到屋顶相交范围")
            return {'CANCELLED'}
    else:
        print(f"未找到屋顶相交范围")
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
    utils.outputMsg("回廊延伸")
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

    # 验证是否可延伸
    LoggiaColl = Loggia.users_collection[0]
    bData:acaData = Loggia.ACA_data
    dk = bData.DK
    if dir in bData.loggia_sign:
        utils.popMessageBox("无法向该方向延伸")
        return {'CANCELLED'}
    else:
        bData.loggia_sign += '/' + dir

    # 如果未合并，开始合并
    if LoggiaJoined is None:
        LoggiaJoined = joinBuilding(Loggia)

        if LoggiaJoined is None:
            utils.popMessageBox("未能合并建筑")
            return {'CANCELLED'}
        
    # 建筑高度
    buildingH = (bData.platform_height+bData.piller_height)
    if bData.use_dg:
        buildingH += bData.dg_height
    buildingH += bData.y_total / 2
    buildingH += 20*dk # 保险高度
    buildingEave = 20*dk # 悬山出际
        
    # 2、判断转角，并生成转角 ---------------------------
    # 是否需要添加转角
    useCorner = False
    # 东西转南北
    if (Loggia.rotation_euler.z == 0 
        and dir in ('N','S')):
        useCorner = True
    # 南北转东西
    if (Loggia.rotation_euler.z != 0
        and dir in ('W','E')):
        useCorner = True

    if useCorner:
        # 调整原廊间的裁剪
        modBool = None
        for obj in LoggiaJoined.children:
            if con.BOOL_SUFFIX  in obj.name : continue
            for mod in obj.modifiers:
                if mod.type == 'BOOLEAN':
                    modBool = mod
                    break
        if modBool:
            boolcube = modBool.object
        offset = buildingEave + bData.piller_diameter
        boolcube.dimensions.x -= offset
        boolcube.location.x -= offset/2
        
        # 创建回廊转角对象
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
        # 位移
        offset_corner = bData.x_total/2 + bData.y_total/2
        if 'W' in bData.loggia_sign:
            offset_corner_v = Vector((offset_corner,0,0))
        else:
            offset_corner_v = Vector((-offset_corner,0,0))
        LoggiaCorner.location = Loggia.location + offset_corner_v
        # 重新生成转角
        buildFloor.buildFloor(LoggiaCorner)

        # 合并
        LoggiaCornerJoined = joinBuilding(LoggiaCorner)

        # 45度镜像
        mirrorOffsetX = bData.x_total/2-bData.y_total/2
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
                use_axis=(True,False,False),
                use_bisect=(True,False,False),
                use_flip=(True,False,False),
                use_merge=True
            )

        # 翼角裁剪
        eaveExt = 30*dk
        dim = (cornerData.x_total + eaveExt,
               cornerData.y_total + eaveExt,
               buildingH
        )
        loc = (eaveExt/2-bData.piller_diameter/2,
               -eaveExt/2+bData.piller_diameter/2,
               buildingH/2)
        boolCube = utils.addCube(
            name="翼角裁剪" + con.BOOL_SUFFIX,
            location=loc,
            dimension=dim,
            parent=LoggiaCornerJoined,
        )
        utils.hideObjFace(boolCube)
        utils.hideObj(boolCube)
        for obj in LoggiaCornerJoined.children:
            # 跳过bool对象
            if con.BOOL_SUFFIX  in obj.name : continue
            utils.addModifierBoolean(
                object=obj,
                boolObj=boolCube,
                operation='INTERSECT',
            )
    
    # 3、延伸方向的廊间生成 -----------------------
    # 向延伸方向复制
    LoggiaNewColl = utils.copyCollection(
        LoggiaColl.name,LoggiaColl.name)
    LoggiaNew = LoggiaNewColl.objects[0]
    mData:acaData = LoggiaNew.ACA_data
    # 移动复制体
    # 控制位移
    if useCorner:
        offset = bData.x_total/2 + bData.y_total/2
        if dir in ('N','S'):
            if dir == 'N': # 向北延伸
                LoggiaNew.location.y += offset    
            elif dir == 'S':# 向南延伸
                LoggiaNew.location.y -= offset
            if 'W' in bData.loggia_sign:# 向东转
                LoggiaNew.location.x += offset
            else: # 向西转
                LoggiaNew.location.x -= offset
        else:
            if dir == 'E':# 向东延伸
                LoggiaNew.location.x += offset
            elif dir == 'W':# 向西延伸
                LoggiaNew.location.x -= offset
            if 'S' in bData.loggia_sign:# 向北转
                LoggiaNew.location.y += offset
            else: # 向南转
                LoggiaNew.location.y -= offset
    else:
        if dir == 'E': # 东
            LoggiaNew.location.x += bData.x_total
        elif dir == 'W': # 西
            LoggiaNew.location.x -= bData.x_total
        elif dir == 'N': # 北
            LoggiaNew.location.y += bData.x_total
        elif dir == 'S': # 南
            LoggiaNew.location.y -= bData.x_total
    
    # 控制旋转
    if dir in ('N','S'): #南北转向90度
        LoggiaNew.rotation_euler.z = math.radians(90)
    else:
        LoggiaNew.rotation_euler.z = 0

    # 标识相邻的回廊
    if dir == 'E': # 东
        mData.loggia_sign = '/W'
    elif dir == 'W': # 西
        mData.loggia_sign = '/E'
    elif dir == 'N': # 北
        mData.loggia_sign = '/S'  
    elif dir == 'S': # 北
        mData.loggia_sign = '/N'  

    # 合并
    LoggiaNewJoined = joinBuilding(LoggiaNew)

    # 裁剪
    buildingDeepth = bData.y_total + 60*dk # 出檐
    # 定位
    offset = bData.piller_diameter/2 + buildingEave/2
    # 东向，北向，裁剪左侧
    if dir in ('E','N'):
        boolX = offset
    # 西向，南向，裁剪右侧
    elif dir in ('W','S'):
        boolX = - offset

    boolCube = utils.addCube(
        name="回廊裁剪" + con.BOOL_SUFFIX,
        location=Vector((boolX,0,buildingH/2)),
        dimension=(bData.x_total+buildingEave,
                   buildingDeepth,
                   buildingH),
        parent=LoggiaNewJoined,
    )
    utils.hideObjFace(boolCube)
    utils.hideObj(boolCube)
    if not useCorner:
        for obj in LoggiaJoined.children:
            # 跳过bool对象
            if con.BOOL_SUFFIX  in obj.name : continue
            utils.addModifierBoolean(
                object= obj,
                boolObj=boolCube,
                operation='DIFFERENCE'
            )
    for obj in LoggiaNewJoined.children:
        # 跳过bool对象
        if con.BOOL_SUFFIX  in obj.name : continue
        utils.addModifierBoolean(
            object= obj,
            boolObj=boolCube,
            operation='INTERSECT'
        )

    # 转角屋顶裁剪
    if useCorner:
        cubeWidth = bData.y_total + 60*dk + bData.x_total*2 # 出檐
        boolCube = utils.addCube(
            name="屋顶斜切" + con.BOOL_SUFFIX,
            dimension=(cubeWidth,cubeWidth,buildingH),
            location=(0,0,buildingH/2),
            parent=LoggiaCorner,
        )
        utils.dissolveEdge(boolCube,[6])
        utils.hideObjFace(boolCube)
        # utils.hideObj(boolCube)

        for obj in LoggiaJoined.children:
            # 跳过bool对象
            if con.BOOL_SUFFIX  in obj.name : continue
            utils.addModifierBoolean(
                object= obj,
                boolObj=boolCube,
                operation='INTERSECT'
            )
        for obj in LoggiaNewJoined.children:
            # 跳过bool对象
            if con.BOOL_SUFFIX  in obj.name : continue
            utils.addModifierBoolean(
                object= obj,
                boolObj=boolCube,
                operation='DIFFERENCE'
            )



    # 聚焦在新loggia
    utils.focusObj(LoggiaNewJoined.children[0])

    return {'FINISHED'}

# 生成回廊转角
def __loggia_corner(baseLoggia:bpy.types.Object,
                  dir):
    return