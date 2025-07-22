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
def addSection(joinedObj:bpy.types.Object,
               sectionPlan='X+',):
    sectionModName = 'Section'
    
    # 确认建筑已经合并
    bData = joinedObj.ACA_data
    if bData.aca_type != con.ACA_TYPE_BUILDING_JOINED:
        print("不是一个合并后的ACA对象，无法做剖视图")
        return
    
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
        # 标注aca_type，以便控制panel
        boolObj.ACA_data['aca_type'] = con.ACA_TYPE_BOOL
        # 设置外观
        boolObj.display_type = 'WIRE'   # 只显示框线
        boolObj.hide_render = True  # 不渲染输出
        # boolObj.hide_select = True    # 禁止选中
        # 回写已经完成的剖视方案
        boolObj.ACA_data['sectionPlan']=sectionPlan 

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
    
        # 回写已经完成的剖视方案
        sectionObj.ACA_data['sectionPlan']=sectionPlan 
    
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