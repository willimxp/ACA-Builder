# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   营造的主入口
#   判断是建造一个新的单体建筑，还是院墙等附加建筑
import time
from .locale.i18n import _
import bpy
import bmesh
from mathutils import Vector
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from .template import template
from . import buildFloor
from .buildOther import buildYardWall
from . import buildRoof
from . import buildCombo
from .postproc import buildingJoin

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
        utils.popMessageBox(_("无法创建该类型的建筑：") 
                            + _(templateName,'template'))
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

    # 251221 排除同一个combo下的其他建筑
    if keepObj != None:
        comboObj = utils.getComboRoot(keepObj)
        if comboObj is not None:
            comboColl = comboObj.users_collection[0]
            currentColl = keepObj.users_collection[0]
            for coll in comboColl.children:
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
def build(templateName=None):
    # 250311 发现在中文版中UV贴图异常
    # 最终发现是该选项会导致生成的'UVMap'变成'UV贴图'
    # 禁用语言-翻译-新建数据
    bpy.context.preferences.view.use_translate_new_dataname = False
    from . import data
    scnData : data.ACA_data_scene = bpy.context.scene.ACA_data

    if templateName is None:
        # 待营造的模板，来自用户界面上的选择
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

@buildCombo.update_combo_bound
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
            utils.popMessageBox(_("无法创建该类型的建筑,%s") % (bData.aca_type))
        
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
    # 1、删除合并体 ------------------------------------
    # 判断是否为合并建筑
    bData:acaData = buildingObj.ACA_data
    # 如果为合并体，删除该合并体
    if bData.aca_type == con.ACA_TYPE_BUILDING_JOINED:
        # 找到未合并建筑
        buildingJoined = buildingObj
        buildingObj = buildingJoin.getJoinedOriginal(buildingJoined)
        if buildingObj is None:
            raise Exception(_("删除失败，未找到建筑未合并的本体"))
        # 删除合并建筑
        utils.deleteHierarchy(buildingJoined,del_parent=True)
    # 如果为本体，找到并删除合并体
    else:
        # 判断集合中是否存在合并目录
        if con.COLL_NAME_ROOT_JOINED in bpy.context.scene.collection.children:
            # 找到合并目录
            JoinedColl:bpy.types.Collection = \
                bpy.context.scene.collection.children[con.COLL_NAME_ROOT_JOINED]
            # 找到同名的合并对象
            for obj in JoinedColl.objects:
                if obj.name == buildingObj.name + con.JOIN_SUFFIX:
                    # 删除树状结构
                    utils.deleteHierarchy(obj,True)
    
    # 2、删除本体 ------------------------------------
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
            utils.popMessageBox(_("无法创建该类型的建筑：") + bData.aca_type)

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
            return _("盝顶设置异常，斗栱出跳或盝顶檐步架宽太小。请使用有出跳的斗栱，或增加盝顶檐步架宽。")
        
    # 平坐验证
    if (bData.roof_style == con.ROOF_BALCONY):
        if not bData.use_dg:
            if bData.dg_extend < 0.001:
                return _("无法生成平坐，请启用斗栱，且斗栱应该有足够的出跳。")
    return