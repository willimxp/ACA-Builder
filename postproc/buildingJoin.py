# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   建筑合并

import bpy
from .. import utils
from ..locale.i18n import _
from ..const import ACA_Consts as con

# 组合建筑为一个实体
# 或者解除组合恢复
def joinBuilding(buildingObj:bpy.types.Object,
                 useLayer=True, # 是否分层合并
                 joinCombo=True, # 是否合并整个combo
                 excludeKeyword='', # 排除合并的对象
                ):
    
    # print开始时间，用于调试
    # print(time.strftime("%H:%M:%S", time.localtime()),"开始合并建筑")

    # 判断组合或解除组合
    buildingObj,bData,objData = utils.getRoot(buildingObj)
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        undoJoin(buildingObj)
        return
    
    # 260409 如果是回廊，排除踏跺
    if bData.combo_type == con.COMBO_LOGGIA:
        excludeKeyword = _('踏跺.')

    # 251114 manifold boolean在合并后再做重复材质清理，会导致材质混乱
    # 所以，统一在合并前清理材质
    utils.updateScene()
    utils.cleanDupMat()
    
    # 1、参数和变量 --------------------------
    collcopySuffix = '.collcopy'

    # 墙体只有一级层次，不区分是否分层
    if bData.aca_type == con.ACA_TYPE_YARDWALL:
        useLayer = False
    
    # 2、准备合并的组织结构 ------------------------------------
    # 2.0、combo组合替换根对象
    isCombo = False
    # 251205 调用参数joinCombo来决定是否要合并整个combo
    # 如，在垂花门内部进行抱厦裁剪时，不应该组合combo
    if joinCombo:
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
    # 计算目标名称
    joinedRootName = buildingObj.name + con.JOIN_SUFFIX
    # 先查找是否已存在同名对象，存在则复用
    joinedRoot = bpy.data.objects.get(joinedRootName)
    if joinedRoot:
        # 复用已有对象，如果隐藏则显示（包括子对象）
        utils.showHierarchy(joinedRoot)
    else:
        # 不存在则新建
        joinedRoot = utils.copySimplyObject(buildingObjCopy)
        joinedRoot.name = joinedRootName
    # 标示为ACA对象
    joinedRoot.ACA_data['aca_obj'] = True
    joinedRoot.ACA_data['aca_type'] = \
        con.ACA_TYPE_BUILDING_JOINED

    # 3、开始合并对象 -------------------------------------
    # 3.1、选择所有下级层次对象
    partObjList = []    # 在addChild中递归填充
    # 收集合并排除的对象，用于非分层合并时单独处理
    excludeObjList = []
    def addChild(buildingObjCopy, excludeKeyword=None):
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
            # print(f"{parentColl.name}-{parentColl.hide_viewport}-{childObj.name}")
            if parentColl.hide_viewport:
                useObj = False
            # 260409 排除名称包含指定关键字的对象（如踏跺）
            if excludeKeyword and excludeKeyword in childObj.name:
                excludeObjList.append(childObj)
                useObj = False
            # 记录对象名称
            if useObj:
                partObjList.append(childObj)
            # 次级递归
            if childObj.children:
                addChild(childObj, excludeKeyword)
    
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
        # 260409 合并时可排除制定的关键字对象
        excludeObjList.clear()
        addChild(layer, excludeKeyword=excludeKeyword)
        if len(partObjList) == 0 :
            print(_("%s没有需要合并的对象，继续...") % (layer.name))
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

        # 250929 提取combo对象的属性
        if isCombo:
            comboType = partObjList[0].parent.parent.ACA_data.combo_type
        
        # 合并对象
        # 先在 joinedRoot 下查找是否存在同名对象（忽略.001/.002等后缀）
        oldJoinedModel = None
        for child in joinedRoot.children:
            # 比较时忽略 Blender 自动生成的数字后缀（如 .001, .002 等）
            childBaseName = utils.getBaseName(child.name)
            joinedBaseName = utils.getBaseName(joinedName)
            if childBaseName == joinedBaseName:
                oldJoinedModel = child
                break
        
        joinedModel = utils.joinObjects(
            objList=partObjList,
            newName=joinedName,)
        
        # 如果存在同名旧对象，拷贝其modifier后删除旧对象
        if oldJoinedModel:
            if oldJoinedModel.modifiers:
                utils.copyModifiers(oldJoinedModel, joinedModel)
            utils.delObject(oldJoinedModel)
        
        # 250929 继承父建筑的combo_type，以便剖视图区分是否为底层建筑还是楼阁
        if isCombo:
            joinedModel.ACA_data['combo_type'] = comboType
            # print(joinedName + " joinedComboType=" + comboType)

        # 251205 采用更简洁的坐标转换
        mw = joinedModel.matrix_world
        joinedModel.parent = joinedRoot
        joinedModel.matrix_world = mw

        utils.applyTransform2(joinedModel,
                                use_location=True,
                                use_rotation=True,
                                use_scale=True)

        # 2、添加到合并目录
        collJoined.objects.link(joinedModel)

        # 260409 如果有排除的对象，复制对象并挂接到joinedRoot下，避免被意外裁剪
        if len(excludeObjList) > 0:
            for excludeObj in excludeObjList:
                # 查找是否存在同名对象（忽略.001/.002等后缀）
                isExist = False
                excludeBaseName = utils.getBaseName(excludeObj.name)
                for child in joinedRoot.children:
                    childBaseName = utils.getBaseName(child.name)
                    if excludeBaseName == childBaseName:
                        isExist = True
                        break
                
                if not isExist:
                    # 复制排除的对象
                    excludeCopy = utils.copySimplyObject(excludeObj)
                    # 保持世界坐标转换
                    mw = excludeCopy.matrix_world
                    excludeCopy.parent = joinedRoot
                    excludeCopy.matrix_world = mw
                    # 应用变换
                    utils.applyTransform2(excludeCopy,
                                        use_location=True,
                                        use_rotation=True,
                                        use_scale=True)
                    # 从原集合取消链接
                    for coll in excludeCopy.users_collection:
                        coll.objects.unlink(excludeCopy)
                    # 添加到合并目录
                    collJoined.objects.link(excludeCopy)
        
        # 反查joinedRoot下的排除对象，是否已经被删除，保证原建筑删除踏跺后，同步在合并对象中删除
        if excludeKeyword != '':
            for child in joinedRoot.children:
                childBaseName = utils.getBaseName(child.name)
                if excludeKeyword in childBaseName:
                    if len(excludeObjList) == 0:
                        utils.delObject(child)
                    else:
                        isExist = False
                        for excludeObj in excludeObjList:
                            excludeBaseName = utils.getBaseName(excludeObj.name)
                            if excludeBaseName == childBaseName:
                                isExist = True
                                break
                        if not isExist:
                            utils.delObject(child)

    # 3、删除复制的建筑，包括复制的集合
    # 251205 根据joinCombo参数决定是否删除整个集合
    from .. import build
    build.delBuilding(buildingObjCopy,withCombo=joinCombo)

    # 4、隐藏原建筑
    utils.hideCollection(collName)

    # 5、聚焦根节点
    # utils.focusObj(joinedRoot)
    # 260413 改为聚焦所有对象
    utils.selectAll(joinedRoot)

    # print结束时间，用于调试
    # print(time.strftime("%H:%M:%S", time.localtime()),"结束合并建筑")

    return joinedRoot

# 解除建筑合并
def undoJoin(buildingObj:bpy.types.Object):
    # 恢复目录显示
    collName = buildingObj.name.removesuffix(con.JOIN_SUFFIX)
    utils.hideCollection(collName,isExclude=False)

    # 260408 隐藏原来的合并对象及其子对象
    utils.hideHierarchy(buildingObj)

    # 260413 删除剖视布尔对象和修改器
    __removeSectionObjects(buildingObj)

    # 选择目录中的所有构件
    src_coll = bpy.data.collections.get(collName)
    oldbuildingObj = src_coll.objects[0]
    utils.selectAll(oldbuildingObj)
    bpy.context.view_layer.objects.active = oldbuildingObj

    return oldbuildingObj

# 删除剖视布尔对象和修改器
def __removeSectionObjects(obj:bpy.types.Object):
    # 删除名为 'Section' 的布尔修改器
    mod = obj.modifiers.get('Section')
    if mod != None:
        obj.modifiers.remove(mod)
    
    # 检查并删除 'b.' 开头的子对象
    children_to_remove = []
    for child in obj.children:
        if child.name.startswith('b.'):
            children_to_remove.append(child)
        else:
            # 递归处理非布尔子对象
            __removeSectionObjects(child)
    
    # 删除布尔子对象
    for boolObj in children_to_remove:
        utils.delObject(boolObj)