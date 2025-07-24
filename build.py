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

# 全局参数 -----------------
# 是否在运行
isFinished = True
# 当前状态提示文字
buildStatus = ''
# 进度百分比
progress = 0
# 集合的排除属性备份
collExclude = {}

def __buildSingle(acaType,templateName,comboset=False):
    # 根据模板类型调用不同的入口
    if acaType == con.ACA_TYPE_BUILDING:
        buildFloor.buildFloor(None,templateName,comboset=comboset)
    elif acaType == con.ACA_TYPE_YARDWALL:
        buildYardWall.buildYardWall(None,templateName)
    else:
        utils.popMessageBox("无法创建该类型的建筑：" + templateName)
    return

# 排除目录下的其他建筑
def __excludeOther(rootColl:bpy.types.Collection,
                   isExclude,
                   buildingObj=None,
    ):
    # 查找当前建筑所在的目录
    if buildingObj != None:
        currentColl = buildingObj.users_collection[0]
    else:
        currentColl = None
    
    # 全局参数，缓存的集合可见性
    global collExclude
    # 排除时，更新缓存
    if isExclude:
        collExclude.clear()
        for coll in rootColl.children:
            layerColl = utils.recurLayerCollection(
                bpy.context.view_layer.layer_collection, 
                coll.name,)
            # 将键值对存入字典
            collExclude[coll.name] = layerColl.exclude

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
            print(f"write collexclude {coll.name}:{layerColl.exclude}")
        # 恢复集合时，从缓存判断
        else:
            # 缓存有滞后性，本次新增的集合没有键值
            if coll.name in collExclude:
                layerExclude = collExclude[coll.name]
                print(f"read collexclude {coll.name}:{layerExclude}")
                # 如果原始状态就是隐藏，则跳出本次循环
                if layerExclude:
                    print(f"collexclude skip {coll.name}")
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
    
    # 创建或锁定根目录（ACA筑韵古建）
    rootColl = utils.setCollection(con.COLL_NAME_ROOT,
                        isRoot=True,colorTag=2)
    
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
    __excludeOther(rootColl,True)

    if acaType != con.ACA_TYPE_COMBO:
        # 单体建筑
        __buildSingle(
            acaType=acaType,
            templateName=templateName
        )
    else:
        # 组合建筑
        tempChildren = template.getTemplateChild(templateName)
        for child in tempChildren:
            __buildSingle(
                acaType=child['acaType'],
                templateName=child['templateName'],
                comboset=True
            )
    
    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(rootColl,False)

    # 关闭视角自动锁定
    scnData['is_auto_viewall'] = False

    return {'FINISHED'}

def updateBuilding(buildingObj:bpy.types.Object,
                   reloadAssets = False):
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    # 创建或锁定根目录（ACA筑韵古建）
    rootColl = utils.setCollection(con.COLL_NAME_ROOT,
                        isRoot=True,colorTag=2)
    
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther(rootColl,True,buildingObj)

    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0

    # 根据模板类型调用不同的入口
    if bData.aca_type == con.ACA_TYPE_BUILDING:
        buildFloor.buildFloor(buildingObj,
                    reloadAssets=reloadAssets)
    elif bData.aca_type == con.ACA_TYPE_YARDWALL:
        buildYardWall.buildYardWall(buildingObj,
                    reloadAssets=reloadAssets)
    else:
        utils.popMessageBox("无法创建该类型的建筑：" + bData.aca_type)

    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(rootColl,False,buildingObj)

    return {'FINISHED'}

# 删除建筑
def delBuilding(buildingObj:bpy.types.Object):
    # 找到对应的目录
    buildingColl = buildingObj.users_collection[0]
    # 从“ACA筑韵古建”目录查找
    rootcoll = bpy.context.scene.collection.children[con.COLL_NAME_ROOT]
    # 删除该目录
    rootcoll.children.unlink(buildingColl)
    bpy.data.collections.remove(buildingColl)
    # 清理垃圾  
    utils.delOrphan()
    return {'FINISHED'}

# 清除所有的装修、踏跺等，重新生成地盘
def resetFloor(buildingObj:bpy.types.Object):
    # 创建或锁定根目录（ACA筑韵古建）
    rootColl = utils.setCollection(con.COLL_NAME_ROOT,
                        isRoot=True,colorTag=2)
    
    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther(rootColl,True,buildingObj)

    buildFloor.resetFloor(buildingObj)

    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(rootColl,False,buildingObj)
    return  {'FINISHED'}

# 重新生成屋顶
def resetRoof(buildingObj:bpy.types.Object):
    # 创建或锁定根目录（ACA筑韵古建）
    rootColl = utils.setCollection(con.COLL_NAME_ROOT,
                        isRoot=True,colorTag=2)
    
    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0
    # 暂时排除目录下的其他建筑，以加快执行速度
    __excludeOther(rootColl,True,buildingObj)

    buildRoof.buildRoof(buildingObj)

    isFinished = True
    # 取消排除目录下的其他建筑
    __excludeOther(rootColl,False,buildingObj)
    return  {'FINISHED'}

# 纵剖视图
def addSection(buildingObj:bpy.types.Object,
               sectionPlan='X+'):
    sectionModName = 'Section'

    # 1、确认是否已经合并 ------------------------
    bData = buildingObj.ACA_data
    # 如果未合并，则先自动合并
    if bData.aca_type != con.ACA_TYPE_BUILDING_JOINED:
        joinedObj = joinBuilding(buildingObj)
    else:
        joinedObj = buildingObj
    
    # 2、确认是否已经做了剖视 -----------------------
    jData = joinedObj.ACA_data
    # 获取当前剖视模式
    currentPlan = None
    if 'sectionPlan' in jData:     
        currentPlan = jData['sectionPlan']
    # 判断是否已做剖视
    if currentPlan == None:
        # 未作剖视的新合并对象，无需特殊处理
        pass
    else:
        # 如果剖视方案相同，解除剖视
        if sectionPlan == currentPlan:
            # 这里解除合并的同时，就会解除剖视
            __undoJoin(buildingObj)
            return
        # 剖视方案不同，重新合并
        else:
            buildingObj = __undoJoin(buildingObj)
            joinedObj = joinBuilding(buildingObj)

    
    # 3、开始做剖视 -----------------------
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
        # 确认该对象是否已经有boolean
        mod = sectionObj.modifiers.get(sectionModName)
        # 已有boolean的直接复用boolObj
        if mod != None:
            # 删除布尔对象
            utils.delObject(mod.object)
            # 删除修改器
            sectionObj.modifiers.remove(mod)
        
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
        # 设置外观
        boolObj.display_type = 'WIRE'   # 只显示框线
        boolObj.hide_render = True  # 不渲染输出
        # boolObj.hide_select = True    # 禁止选中

        # 设置剖视方案
        offset = __getSectionPlan(boolObj,sectionPlan)
        boolObj.location += offset

        # 添加boolean
        utils.addModifierBoolean(
            name=sectionModName,
            object=sectionObj,
            boolObj=boolObj,
            operation='INTERSECT',
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

    # Y剖面正方向
    if sectionType == 'Y+':
        offset = Vector((
            0,
            boolObj.dimensions.y/2 + Y_reserve - origin_loc.y,
            0
        ))
    elif sectionType == 'Y-':
        offset = Vector((
            0,
            -boolObj.dimensions.y/2 - Y_reserve - origin_loc.y,
            0
        ))
    elif sectionType == 'X+':
        offset = Vector((
            boolObj.dimensions.x/2 - origin_loc.x,
            0,
            0
        ))
    elif sectionType == 'X-':
        offset = Vector((
            -boolObj.dimensions.x/2 - origin_loc.x,
            0,
            0
        ))

    return offset

# 组合建筑为一个实体
# 或者解除组合恢复
def joinBuilding(buildingObj:bpy.types.Object,
                 useLayer=False, # 是否分层合并
                ):
    # 合并对象的名称后缀
    joinSuffix = '.joined'
    collcopySuffix = '.collcopy'
    
    # 判断组合或解除组合
    buildingObj,bData,objData = utils.getRoot(buildingObj)
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        __undoJoin(buildingObj)
        return
    
    # 墙体只有一级层次，不区分是否分层
    if bData.aca_type == con.ACA_TYPE_YARDWALL:
        useLayer = False
    
    # 开始合并处理 --------------------------------------
    # 1、复制建筑的整个集合，在复制集合上进行合并
    # 这样不会影响原有的生成模型
    collName = buildingObj.users_collection[0].name
    collCopy = utils.copyCollection(collName,collName + collcopySuffix)
    # 第一个对象就是建筑根节点，这样判断可能不够安全
    buildingObjCopy = collCopy.objects[0]
    # 新建/绑定合并集合
    collJoined = utils.setCollection(
            'ACA古建.合并',isRoot=True,colorTag=3)

    # 2、合并对象
    # 2.1、选择所有下级层次对象
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
    
    # 2.2、合并对象
    # 判断是否需要分层合并
    layerList = []
    if useLayer:
        layerList = buildingObjCopy.children
        # 复制生成分层合并的父节点
        joinedRoot = utils.copySimplyObject(buildingObjCopy)
        # 设置名称
        joinedRoot.name = buildingObj.name + joinSuffix
        # 标示为ACA对象
        joinedRoot.ACA_data['aca_obj'] = True
        joinedRoot.ACA_data['aca_type'] = \
            con.ACA_TYPE_BUILDING_JOINED
    else:
        layerList.append(buildingObjCopy)

    # 分层合并
    for layer in layerList:
        # 递归填充待合并对象
        partObjList.clear()
        addChild(layer)
        if len(partObjList) == 0 :
            print("失败，递归查询未找到待合并对象")
            return
        
        # 区分是否分层的不同命名规则
        if useLayer:
            # 合并名称以层标注
            joinedName = (buildingObj.name 
                          + '.' 
                          + layer.name)
        else:
            # 合并名称直接加'joined'后缀
            joinedName = buildingObj.name + joinSuffix
        # 合并对象
        joinedModel = utils.joinObjects(
            objList=partObjList,
            newName=joinedName,)
        
        # 区分是否分层的坐标映射
        if useLayer:
            # 绑定在以前复制生成的根节点
            layerParent = joinedRoot
            # 取各个分层的局部坐标
            matrix = joinedModel.parent.matrix_local  
        else:
            # 合并到了buildingObj根节点
            layerParent = None
            # 墙体只有一级层次，不区分是否分层
            if joinedModel.parent.ACA_data.aca_type == \
                con.ACA_TYPE_YARDWALL:
                matrix = joinedModel.parent.matrix_world
            else:
                # 直接取全局坐标
                matrix = joinedModel.matrix_world

        # 重新绑定父级对象
        joinedModel.parent = layerParent
        # 重新映射坐标
        joinedModel.location = matrix @ joinedModel.location
        if useLayer:
            utils.applyTransform2(joinedModel,use_location=True)

        # 标示为ACA对象
        joinedModel.ACA_data['aca_obj'] = True
        joinedModel.ACA_data['aca_type'] = \
            con.ACA_TYPE_BUILDING_JOINED

        # 2、添加到合并目录
        collJoined.objects.link(joinedModel)

    # 3、删除复制的建筑，包括复制的集合
    delBuilding(buildingObjCopy)

    # 4、隐藏原建筑
    utils.hideCollection(collName)

    # 5、聚焦
    if useLayer:
        focusObj = joinedRoot
    else:
        focusObj = joinedModel
    utils.focusObj(focusObj)

    return joinedModel

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