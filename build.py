# 作者：willimxp
# 所属插件：ACA Builder
# 功能概述：
#   营造的主入口
#   判断是建造一个新的单体建筑，还是院墙等附加建筑
import bpy
from .const import ACA_Consts as con
from .data import ACA_data_obj as acaData
from . import utils
from . import acaTemplate

# 开始新的营造
def build():
    # 创建或锁定根目录（ACA古建营造）
    utils.setCollection(con.ROOT_COLL_NAME,
                        isRoot=True,colorTag=2)

    # 待营造的模板，来自用户界面上的选择
    templateName = bpy.context.scene.ACA_data.template

    # 创建或锁定根目录（建筑名称）
    utils.setCollection(templateName)

    acaType = acaTemplate.getBuildingType(templateName)

    # 根据模版类型调用不同的入口
    if acaType == con.ACA_TYPE_BUILDING:
        from . import buildFloor
        buildFloor.buildFloor(None)
    elif acaType == con.ACA_TYPE_YARDWALL:
        from . import buildYardWall
        buildYardWall.buildYardWall(None)
    else:
        utils.outputMsg("无法创建该类型的建筑：" + templateName)

    return {'FINISHED'}

# 删除建筑
def delBuilding(buildingObj:bpy.types.Object):
    # 找到对应的目录
    buildingColl = buildingObj.users_collection[0]
    # 从“ACA古建营造”目录查找
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