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

isFinished = True
buildStatus = ''
progress = 0

# 开始新的营造
def build():
    # 创建或锁定根目录（ACA筑韵古建）
    utils.setCollection(con.ROOT_COLL_NAME,
                        isRoot=True,colorTag=2)

    # 待营造的模板，来自用户界面上的选择
    templateName = bpy.context.scene.ACA_data.template

    # 获取模板类型，建筑或院墙
    acaType = template.getBuildingType(templateName)

    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0

    # 根据模板类型调用不同的入口
    if acaType == con.ACA_TYPE_BUILDING:
        from . import buildFloor
        buildFloor.buildFloor(None)
    elif acaType == con.ACA_TYPE_YARDWALL:
        from . import buildYardWall
        buildYardWall.buildYardWall(None)
    else:
        utils.popMessageBox("无法创建该类型的建筑：" + templateName)
    
    isFinished = True
    return {'FINISHED'}

def updateBuilding(buildingObj:bpy.types.Object):
    # 载入数据
    bData:acaData = buildingObj.ACA_data

    # 调用进度条
    global isFinished,progress
    isFinished = False
    progress = 0

    # 根据模板类型调用不同的入口
    if bData.aca_type == con.ACA_TYPE_BUILDING:
        from . import buildFloor
        buildFloor.buildFloor(buildingObj)
    elif bData.aca_type == con.ACA_TYPE_YARDWALL:
        from . import buildYardWall
        buildYardWall.buildYardWall(buildingObj)
    else:
        utils.popMessageBox("无法创建该类型的建筑：" + bData.aca_type)

    isFinished = True
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
    return

# 导出建筑
def exportBuilding(buildingObj:bpy.types.Object):
    return