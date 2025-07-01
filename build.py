# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   营造的主入口
#   判断是建造一个新的单体建筑，还是院墙等附加建筑
import bpy
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import template
from . import buildFloor
from . import buildYardWall
from . import buildRoof

isFinished = True
buildStatus = ''
progress = 0

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
def __excludeOther(rootColl,isExclude,buildingObj=None):
    # 查找当前建筑所在的目录
    if buildingObj != None:
        currentColl = buildingObj.users_collection[0]
    else:
        currentColl = None

    # 排除其他建筑
    for coll in rootColl.children:
        # 如果是当前建筑所在的目录，跳过
        if coll == currentColl:
            continue
        # 根据名称查找对应的视图层目录
        layerColl = utils.recurLayerCollection(
            bpy.context.view_layer.layer_collection,
            coll.name)
        # 如果找到了，设置排除属性
        if layerColl != None:
            layerColl.exclude = isExclude
    utils.redrawViewport() # 刷新视图
    return

# 开始新的营造
def build():
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    
    # 创建或锁定根目录（ACA筑韵古建）
    rootColl = utils.setCollection(con.ROOT_COLL_NAME,
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
    rootColl = utils.setCollection(con.ROOT_COLL_NAME,
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
    rootcoll = bpy.context.scene.collection.children[con.ROOT_COLL_NAME]
    # 删除该目录
    rootcoll.children.unlink(buildingColl)
    bpy.data.collections.remove(buildingColl)
    # 清理垃圾  
    utils.delOrphan()
    return {'FINISHED'}

# 清除所有的装修、踏跺等，重新生成地盘
def resetFloor(buildingObj:bpy.types.Object):
    # 创建或锁定根目录（ACA筑韵古建）
    rootColl = utils.setCollection(con.ROOT_COLL_NAME,
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
    rootColl = utils.setCollection(con.ROOT_COLL_NAME,
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