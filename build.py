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
    if (bData.x_total != mData.x_total
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

        # 设置面阔较小的为fromBuilding(抱厦)
        if bData.x_total > mData.x_total:
            temp = fromBuilding
            fromBuilding = toBuilding
            toBuilding = temp
            temp = fromBuildingJoined
            fromBuildingJoined = toBuildingJoined
            toBuildingJoined = temp

        bData:acaData = fromBuilding.ACA_data
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
        name="勾连搭",
        location=boolLoc,
        dimension=boolDim,
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 4、添加bool modifier
    for layer in fromBuildingJoined.children:
        # 跳过bool对象本身
        if layer == boolObj: continue
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='INTERSECT',
        )
    for layer in toBuildingJoined.children:
        utils.addModifierBoolean(
            object=layer,
            boolObj=boolObj,
            operation='DIFFERENCE',
        )

    return {'FINISHED'}

# 建筑组合：平行抱厦-悬山
# fromBuilding为面阔较小的抱厦
def __unionParallelXuanshan(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object):
    boolSign = 'unionbool'
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
        name="平行抱厦-悬山-主建筑" + boolSign,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    for layer in toBuildingJoined.children:
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
        name="平行抱厦-悬山-抱厦" + boolSign,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 添加bool modifier
    for layer in fromBuildingJoined.children:
        # 跳过bool对象
        if boolSign in layer.name : continue
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
        name="平行抱厦-悬山-柱网" + boolSign,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    for layer in toBuildingJoined.children:
        if con.COLL_NAME_PILLER in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    for layer in fromBuildingJoined.children:
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
                + bData.platform_height*3 # 保留踏跺空间
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
        name="平行抱厦-悬山-台基" + boolSign,
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
        if con.COLL_NAME_BASE in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
    for layer in fromBuildingJoined.children:
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
    import bmesh
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
        if con.COLL_NAME_BOARD in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=tileGrid_copy,
                operation='DIFFERENCE',
            )

    return {'FINISHED'}

# 建筑组合：平行抱厦-歇山
# fromBuilding为面阔较小的抱厦
def __unionParallelXieshan(fromBuilding:bpy.types.Object,
                     toBuilding:bpy.types.Object,
                     fromBuildingJoined:bpy.types.Object,
                     toBuildingJoined:bpy.types.Object):
    utils.outputMsg('平行抱厦-歇山')
    boolSign = 'unionbool'
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
        name="平行抱厦-歇山屋顶" + boolSign,
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
        if boolSign in layer.name : continue
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
        name="平行抱厦-悬山-柱网" + boolSign,
        location=(boolX,boolY,boolZ),
        dimension=(boolWidth,boolDeepth,boolHeight),
        parent=fromBuildingJoined,
    )
    utils.hideObjFace(boolObj)
    utils.hideObj(boolObj)

    # 绑定boolean
    for layer in toBuildingJoined.children:
        if con.COLL_NAME_PILLER in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
            # 裁剪后柱体normal异常，做平滑
            utils.shaderSmooth(layer)
    for layer in fromBuildingJoined.children:
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
        name="平行抱厦-悬山-台基" + boolSign,
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
        if con.COLL_NAME_BASE in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=boolObj,
                operation='DIFFERENCE',
            )
    for layer in fromBuildingJoined.children:
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
    import bmesh
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
        if con.COLL_NAME_BOARD in layer.name :
            utils.addModifierBoolean(
                object=layer,
                boolObj=tileGrid_copy,
                operation='DIFFERENCE',
            )

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